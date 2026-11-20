"""
app/services/dataset_service.py
────────────────────────────────
Comprehensive service for dataset file upload, schema validation,
pandas-based data cleaning, referential integrity enforcement, and DB ingestion.
"""

from __future__ import annotations

import logging
import os
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, BinaryIO, Sequence

import numpy as np
import pandas as pd
from fastapi import UploadFile
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.main import AppException
from app.models.dataset import Dataset
from app.models.retail import (
    RetailCustomer,
    RetailExpense,
    RetailInventoryMovement,
    RetailProduct,
    RetailTransaction,
    RetailTransactionItem,
)
from app.models.user import User

logger = logging.getLogger(__name__)

# Mandatory target period
START_DATE = pd.to_datetime("2026-05-01")
END_DATE = pd.to_datetime("2026-10-31")

# Expected sheets and their required columns for the Retail dataset
REQUIRED_SCHEMA: dict[str, list[str]] = {
    "Customers": [
        "customer_id",
        "customer_name",
        "city",
        "signup_date",
        "customer_segment",
        "email",
    ],
    "Products": [
        "product_id",
        "product_name",
        "category",
        "unit_price",
        "unit_cost",
        "reorder_level",
        "supplier_id",
    ],
    "Transactions": [
        "transaction_id",
        "customer_id",
        "transaction_date",
        "store_id",
        "channel",
        "gross_amount",
        "discount",
        "net_amount",
        "payment_method",
        "order_status",
    ],
    "Transaction_Items": [
        "line_item_id",
        "transaction_id",
        "product_id",
        "quantity",
        "unit_price",
        "line_total",
    ],
    "Inventory_Movements": [
        "movement_id",
        "product_id",
        "movement_date",
        "movement_type",
        "quantity",
        "warehouse_id",
        "reference_no",
    ],
    "Expenses": [
        "expense_id",
        "expense_date",
        "store_id",
        "category",
        "amount",
        "vendor",
    ],
}


def validate_file_format_and_save(file: UploadFile) -> tuple[str, str, int]:
    """
    Validate extension, MIME type, and size, then save to settings.UPLOAD_DIR.
    Returns: (stored_filename, absolute_file_path, file_size_bytes)
    """
    filename = file.filename or ""
    ext = os.path.splitext(filename)[1].lower()
    if ext not in [".xlsx", ".xls"]:
        raise AppException(
            status_code=422,
            detail=f"Invalid file type '{ext}'. Only Excel files (.xlsx, .xls) containing the required retail sheets are supported.",
            code="INVALID_FILE_TYPE",
        )

    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    stored_name = f"{uuid.uuid4().hex}_{filename}"
    file_path = os.path.join(settings.UPLOAD_DIR, stored_name)

    size = 0
    with open(file_path, "wb") as f:
        while chunk := file.file.read(1024 * 1024):  # 1MB chunks
            size += len(chunk)
            if size > settings.max_upload_bytes:
                os.remove(file_path)
                raise AppException(
                    status_code=422,
                    detail=f"File exceeds maximum allowed size of {settings.MAX_UPLOAD_SIZE_MB}MB.",
                    code="FILE_TOO_LARGE",
                )
            f.write(chunk)

    return stored_name, file_path, size


def load_and_validate_sheets(file_path: str) -> dict[str, pd.DataFrame]:
    """
    Load Excel file using pandas + openpyxl, checking for mandatory sheets and columns.
    Raises 422 with comprehensive list of missing components if validation fails.
    """
    try:
        excel_file = pd.ExcelFile(file_path, engine="openpyxl")
    except Exception as exc:
        raise AppException(
            status_code=422,
            detail=f"Could not read Excel file: {str(exc)}",
            code="CORRUPT_EXCEL_FILE",
        )

    sheet_names = excel_file.sheet_names
    missing_sheets = [s for s in REQUIRED_SCHEMA if s not in sheet_names]
    if missing_sheets:
        raise AppException(
            status_code=422,
            detail=f"Missing required sheets: {missing_sheets}. Required sheets are: {list(REQUIRED_SCHEMA.keys())}",
            code="MISSING_SHEETS",
        )

    raw_dfs: dict[str, pd.DataFrame] = {}
    missing_columns: dict[str, list[str]] = {}

    for sheet, req_cols in REQUIRED_SCHEMA.items():
        df = pd.read_excel(excel_file, sheet_name=sheet)
        # Strip column names
        df.columns = [str(c).strip() for c in df.columns]
        missing = [c for c in req_cols if c not in df.columns]
        if missing:
            missing_columns[sheet] = missing
        raw_dfs[sheet] = df

    if missing_columns:
        raise AppException(
            status_code=422,
            detail={
                "message": "Required columns missing in one or more sheets",
                "missing_columns": missing_columns,
            },
            code="MISSING_COLUMNS",
        )

    return raw_dfs


def clean_retail_data(
    raw_dfs: dict[str, pd.DataFrame],
) -> tuple[dict[str, pd.DataFrame], dict[str, Any]]:
    """
    Apply full cleaning rules to raw dataframes:
      1. Drop exact duplicates
      2. Parse dates (dayfirst=True)
      3. Date period filter (2026-05-01 to 2026-10-31)
      4. Fix data types & handle nulls (category median / defaults)
      5. Remove negative & invalid numeric values
      6. Text normalization
      7. Referential integrity enforcement (drop orphan FK rows)
    Returns: (cleaned_dfs, cleaning_summary)
    """
    cleaned: dict[str, pd.DataFrame] = {}
    summary: dict[str, Any] = {
        "dataset_period": "2026-05-01 to 2026-10-31",
        "sheets": {},
        "total_rows_imported": 0,
    }

    def init_stats(sheet_name: str, initial_count: int) -> dict[str, Any]:
        return {
            "rows_initial": int(initial_count),
            "rows_final": 0,
            "duplicates_removed": 0,
            "nulls_handled": 0,
            "date_filtered_rows": 0,
            "invalid_values_dropped": 0,
            "orphan_rows_dropped": 0,
            "details": [],
        }

    # ─────────────────────────────────────────────────────────────────────────
    # 1. Clean Customers
    # ─────────────────────────────────────────────────────────────────────────
    df_c = raw_dfs["Customers"].copy()
    c_stats = init_stats("Customers", len(df_c))

    # Exact duplicates
    dups = int(df_c.duplicated().sum())
    if dups:
        c_stats["duplicates_removed"] = dups
        df_c = df_c.drop_duplicates()

    # Drop rows without customer_id
    null_ids = int(df_c["customer_id"].isna().sum())
    if null_ids:
        df_c = df_c.dropna(subset=["customer_id"])
        c_stats["invalid_values_dropped"] += null_ids
        c_stats["details"].append(f"Dropped {null_ids} rows with missing customer_id")

    df_c["customer_id"] = df_c["customer_id"].astype(str).str.strip()
    df_c = df_c.drop_duplicates(subset=["customer_id"], keep="first")

    # Dates
    df_c["signup_date"] = pd.to_datetime(df_c["signup_date"], dayfirst=True, errors="coerce")

    # Nulls & text normalization
    null_name = int(df_c["customer_name"].isna().sum())
    if null_name:
        df_c["customer_name"] = df_c["customer_name"].fillna("Unknown Customer")
        c_stats["nulls_handled"] += null_name

    df_c["customer_name"] = df_c["customer_name"].astype(str).str.strip().str.title()
    df_c["city"] = df_c["city"].fillna("Unknown").astype(str).str.strip().str.title()
    df_c["customer_segment"] = (
        df_c["customer_segment"].fillna("Regular").astype(str).str.strip().str.title()
    )
    df_c["email"] = df_c["email"].fillna("").astype(str).str.strip().str.lower()

    c_stats["rows_final"] = len(df_c)
    cleaned["Customers"] = df_c
    summary["sheets"]["Customers"] = c_stats

    # ─────────────────────────────────────────────────────────────────────────
    # 2. Clean Products
    # ─────────────────────────────────────────────────────────────────────────
    df_p = raw_dfs["Products"].copy()
    p_stats = init_stats("Products", len(df_p))

    dups = int(df_p.duplicated().sum())
    if dups:
        p_stats["duplicates_removed"] = dups
        df_p = df_p.drop_duplicates()

    # Drop missing product_id
    null_ids = int(df_p["product_id"].isna().sum())
    if null_ids:
        df_p = df_p.dropna(subset=["product_id"])
        p_stats["invalid_values_dropped"] += null_ids

    df_p["product_id"] = df_p["product_id"].astype(str).str.strip()
    df_p = df_p.drop_duplicates(subset=["product_id"], keep="first")

    # Text
    df_p["product_name"] = df_p["product_name"].fillna("Unnamed Product").astype(str).str.strip()
    df_p["category"] = df_p["category"].fillna("General").astype(str).str.strip().str.title()
    df_p["supplier_id"] = df_p["supplier_id"].fillna("Unknown").astype(str).str.strip()

    # Numerics: unit_price, unit_cost, reorder_level
    df_p["unit_price"] = pd.to_numeric(df_p["unit_price"], errors="coerce")
    df_p["unit_cost"] = pd.to_numeric(df_p["unit_cost"], errors="coerce")
    df_p["reorder_level"] = pd.to_numeric(df_p["reorder_level"], errors="coerce").fillna(10).astype(int)

    # Impute missing price/cost using category median
    for col in ["unit_price", "unit_cost"]:
        null_count = int(df_p[col].isna().sum())
        if null_count > 0:
            p_stats["nulls_handled"] += null_count
            median_val = df_p.groupby("category")[col].transform("median")
            df_p[col] = df_p[col].fillna(median_val).fillna(df_p[col].median()).fillna(100.0)
            p_stats["details"].append(f"Imputed {null_count} null {col} values using category median")

    # Non-negative check
    neg_prices = int((df_p["unit_price"] < 0).sum() + (df_p["unit_cost"] < 0).sum())
    if neg_prices:
        df_p = df_p[(df_p["unit_price"] >= 0) & (df_p["unit_cost"] >= 0)]
        p_stats["invalid_values_dropped"] += neg_prices
        p_stats["details"].append(f"Dropped {neg_prices} products with negative price or cost")

    p_stats["rows_final"] = len(df_p)
    cleaned["Products"] = df_p
    summary["sheets"]["Products"] = p_stats

    # ─────────────────────────────────────────────────────────────────────────
    # 3. Clean Transactions
    # ─────────────────────────────────────────────────────────────────────────
    df_t = raw_dfs["Transactions"].copy()
    t_stats = init_stats("Transactions", len(df_t))

    dups = int(df_t.duplicated().sum())
    if dups:
        t_stats["duplicates_removed"] = dups
        df_t = df_t.drop_duplicates()

    # Drop missing transaction_id
    null_ids = int(df_t["transaction_id"].isna().sum())
    if null_ids:
        df_t = df_t.dropna(subset=["transaction_id"])
        t_stats["invalid_values_dropped"] += null_ids

    df_t["transaction_id"] = df_t["transaction_id"].astype(str).str.strip()
    df_t = df_t.drop_duplicates(subset=["transaction_id"], keep="first")
    df_t["customer_id"] = df_t["customer_id"].astype(str).str.strip()

    # Date parsing & filtering to 2026-05-01 -> 2026-10-31
    df_t["transaction_date"] = pd.to_datetime(df_t["transaction_date"], dayfirst=True, errors="coerce")
    initial_t_len = len(df_t)
    valid_dates = (df_t["transaction_date"] >= START_DATE) & (df_t["transaction_date"] <= END_DATE)
    df_t = df_t[valid_dates]
    date_filtered = initial_t_len - len(df_t)
    if date_filtered:
        t_stats["date_filtered_rows"] = date_filtered
        t_stats["details"].append(f"Filtered {date_filtered} transactions outside May 1 - Oct 31, 2026")

    # Numerics: gross_amount, discount, net_amount
    df_t["gross_amount"] = pd.to_numeric(df_t["gross_amount"], errors="coerce").fillna(0.0)
    df_t["discount"] = pd.to_numeric(df_t["discount"], errors="coerce").fillna(0.0)
    df_t["net_amount"] = pd.to_numeric(df_t["net_amount"], errors="coerce")

    # Enforce non-negative amounts & calculate net_amount consistency
    df_t["gross_amount"] = df_t["gross_amount"].clip(lower=0.0)
    df_t["discount"] = df_t["discount"].clip(lower=0.0)
    # Ensure discount doesn't exceed gross
    df_t["discount"] = np.minimum(df_t["discount"], df_t["gross_amount"])
    # Recalculate net_amount = gross_amount - discount
    df_t["net_amount"] = df_t["gross_amount"] - df_t["discount"]

    # Categorical normalization
    df_t["channel"] = df_t["channel"].fillna("In-store").astype(str).str.strip().str.title()
    df_t["payment_method"] = df_t["payment_method"].fillna("Other").astype(str).str.strip()
    df_t["order_status"] = df_t["order_status"].fillna("Completed").astype(str).str.strip().str.title()
    df_t["store_id"] = df_t["store_id"].fillna("STR01").astype(str).str.strip()

    # Referential Integrity: customer_id must exist in Customers
    valid_cust_ids = set(cleaned["Customers"]["customer_id"])
    orphans = int((~df_t["customer_id"].isin(valid_cust_ids)).sum())
    if orphans:
        t_stats["orphan_rows_dropped"] = orphans
        df_t = df_t[df_t["customer_id"].isin(valid_cust_ids)]
        t_stats["details"].append(f"Dropped {orphans} transactions referencing non-existent customer_ids")

    t_stats["rows_final"] = len(df_t)
    cleaned["Transactions"] = df_t
    summary["sheets"]["Transactions"] = t_stats

    # ─────────────────────────────────────────────────────────────────────────
    # 4. Clean Transaction_Items
    # ─────────────────────────────────────────────────────────────────────────
    df_ti = raw_dfs["Transaction_Items"].copy()
    ti_stats = init_stats("Transaction_Items", len(df_ti))

    dups = int(df_ti.duplicated().sum())
    if dups:
        ti_stats["duplicates_removed"] = dups
        df_ti = df_ti.drop_duplicates()

    # Drop missing line_item_id
    df_ti = df_ti.dropna(subset=["line_item_id"])
    df_ti["line_item_id"] = df_ti["line_item_id"].astype(str).str.strip()
    df_ti = df_ti.drop_duplicates(subset=["line_item_id"], keep="first")

    df_ti["transaction_id"] = df_ti["transaction_id"].astype(str).str.strip()
    df_ti["product_id"] = df_ti["product_id"].astype(str).str.strip()

    # Quantities & Prices
    df_ti["quantity"] = pd.to_numeric(df_ti["quantity"], errors="coerce").fillna(1).astype(int)
    df_ti["unit_price"] = pd.to_numeric(df_ti["unit_price"], errors="coerce")
    df_ti["line_total"] = pd.to_numeric(df_ti["line_total"], errors="coerce")

    # Drop negative or zero quantity
    invalid_qty = int((df_ti["quantity"] <= 0).sum())
    if invalid_qty:
        df_ti = df_ti[df_ti["quantity"] > 0]
        ti_stats["invalid_values_dropped"] += invalid_qty

    # Impute missing unit_price from Products if null
    price_map = cleaned["Products"].set_index("product_id")["unit_price"].to_dict()
    df_ti["unit_price"] = df_ti["unit_price"].fillna(df_ti["product_id"].map(price_map)).fillna(0.0)
    df_ti["line_total"] = df_ti["quantity"] * df_ti["unit_price"]

    # Referential Integrity: transaction_id in Transactions, product_id in Products
    valid_txns = set(cleaned["Transactions"]["transaction_id"])
    valid_prods = set(cleaned["Products"]["product_id"])
    orphan_items = int((~df_ti["transaction_id"].isin(valid_txns) | ~df_ti["product_id"].isin(valid_prods)).sum())
    if orphan_items:
        ti_stats["orphan_rows_dropped"] = orphan_items
        df_ti = df_ti[df_ti["transaction_id"].isin(valid_txns) & df_ti["product_id"].isin(valid_prods)]
        ti_stats["details"].append(f"Dropped {orphan_items} items referencing deleted/invalid transactions or products")

    ti_stats["rows_final"] = len(df_ti)
    cleaned["Transaction_Items"] = df_ti
    summary["sheets"]["Transaction_Items"] = ti_stats

    # ─────────────────────────────────────────────────────────────────────────
    # 5. Clean Inventory_Movements
    # ─────────────────────────────────────────────────────────────────────────
    df_im = raw_dfs["Inventory_Movements"].copy()
    im_stats = init_stats("Inventory_Movements", len(df_im))

    dups = int(df_im.duplicated().sum())
    if dups:
        im_stats["duplicates_removed"] = dups
        df_im = df_im.drop_duplicates()

    df_im = df_im.dropna(subset=["movement_id"])
    df_im["movement_id"] = df_im["movement_id"].astype(str).str.strip()
    df_im = df_im.drop_duplicates(subset=["movement_id"], keep="first")
    df_im["product_id"] = df_im["product_id"].astype(str).str.strip()

    # Dates & Date filter
    df_im["movement_date"] = pd.to_datetime(df_im["movement_date"], dayfirst=True, errors="coerce")
    initial_im_len = len(df_im)
    df_im = df_im[(df_im["movement_date"] >= START_DATE) & (df_im["movement_date"] <= END_DATE)]
    date_filtered = initial_im_len - len(df_im)
    if date_filtered:
        im_stats["date_filtered_rows"] = date_filtered

    # Quantity
    df_im["quantity"] = pd.to_numeric(df_im["quantity"], errors="coerce").fillna(0).astype(int)
    # Categoricals
    df_im["movement_type"] = df_im["movement_type"].fillna("Adjustment").astype(str).str.strip().str.title()
    df_im["warehouse_id"] = df_im["warehouse_id"].fillna("WH01").astype(str).str.strip()
    df_im["reference_no"] = df_im["reference_no"].fillna("").astype(str).str.strip()

    # Referential Integrity: product_id must exist in Products
    orphan_movements = int((~df_im["product_id"].isin(valid_prods)).sum())
    if orphan_movements:
        im_stats["orphan_rows_dropped"] = orphan_movements
        df_im = df_im[df_im["product_id"].isin(valid_prods)]
        im_stats["details"].append(f"Dropped {orphan_movements} movements referencing non-existent product_ids")

    im_stats["rows_final"] = len(df_im)
    cleaned["Inventory_Movements"] = df_im
    summary["sheets"]["Inventory_Movements"] = im_stats

    # ─────────────────────────────────────────────────────────────────────────
    # 6. Clean Expenses
    # ─────────────────────────────────────────────────────────────────────────
    df_e = raw_dfs["Expenses"].copy()
    e_stats = init_stats("Expenses", len(df_e))

    dups = int(df_e.duplicated().sum())
    if dups:
        e_stats["duplicates_removed"] = dups
        df_e = df_e.drop_duplicates()

    df_e = df_e.dropna(subset=["expense_id"])
    df_e["expense_id"] = df_e["expense_id"].astype(str).str.strip()
    df_e = df_e.drop_duplicates(subset=["expense_id"], keep="first")

    # Dates
    df_e["expense_date"] = pd.to_datetime(df_e["expense_date"], dayfirst=True, errors="coerce")
    initial_e_len = len(df_e)
    df_e = df_e[(df_e["expense_date"] >= START_DATE) & (df_e["expense_date"] <= END_DATE)]
    date_filtered = initial_e_len - len(df_e)
    if date_filtered:
        e_stats["date_filtered_rows"] = date_filtered

    # Amounts
    df_e["amount"] = pd.to_numeric(df_e["amount"], errors="coerce").fillna(0.0).clip(lower=0.0)

    # Categoricals
    df_e["store_id"] = df_e["store_id"].fillna("STR01").astype(str).str.strip()
    df_e["category"] = df_e["category"].fillna("General").astype(str).str.strip().str.title()
    df_e["vendor"] = df_e["vendor"].fillna("Unknown Vendor").astype(str).str.strip()

    e_stats["rows_final"] = len(df_e)
    cleaned["Expenses"] = df_e
    summary["sheets"]["Expenses"] = e_stats

    # Total rows count
    total_imported = sum(s["rows_final"] for s in summary["sheets"].values())
    summary["total_rows_imported"] = total_imported

    return cleaned, summary


def insert_cleaned_data_to_db(
    db: Session,
    dataset: Dataset,
    cleaned_dfs: dict[str, pd.DataFrame],
    summary: dict[str, Any],
) -> None:
    """
    Insert all cleaned records into the respective retail tables inside a single atomic transaction.
    """
    dataset_id = dataset.id
    logger.info("Starting database ingestion for dataset %s", dataset_id)

    # 1. Customers
    cust_objs = [
        RetailCustomer(
            dataset_id=dataset_id,
            customer_id=row["customer_id"],
            customer_name=row["customer_name"],
            city=row["city"] if pd.notna(row["city"]) else None,
            signup_date=row["signup_date"].date() if pd.notna(row["signup_date"]) else None,
            customer_segment=row["customer_segment"],
            email=row["email"] if row["email"] else None,
        )
        for _, row in cleaned_dfs["Customers"].iterrows()
    ]
    db.bulk_save_objects(cust_objs)

    # 2. Products
    prod_objs = [
        RetailProduct(
            dataset_id=dataset_id,
            product_id=row["product_id"],
            product_name=row["product_name"],
            category=row["category"],
            unit_price=Decimal(str(round(row["unit_price"], 2))),
            unit_cost=Decimal(str(round(row["unit_cost"], 2))),
            reorder_level=int(row["reorder_level"]),
            supplier_id=row["supplier_id"],
        )
        for _, row in cleaned_dfs["Products"].iterrows()
    ]
    db.bulk_save_objects(prod_objs)

    # 3. Transactions
    # We create and flush transaction objects so we obtain their generated UUID PKs
    txn_map: dict[str, uuid.UUID] = {}
    txn_objs = []
    for _, row in cleaned_dfs["Transactions"].iterrows():
        t_id = uuid.uuid4()
        txn_map[row["transaction_id"]] = t_id
        txn_objs.append(
            RetailTransaction(
                id=t_id,
                dataset_id=dataset_id,
                transaction_id=row["transaction_id"],
                customer_id=row["customer_id"],
                transaction_date=row["transaction_date"].date() if pd.notna(row["transaction_date"]) else None,
                store_id=row["store_id"],
                channel=row["channel"],
                gross_amount=Decimal(str(round(row["gross_amount"], 2))),
                discount=Decimal(str(round(row["discount"], 2))),
                net_amount=Decimal(str(round(row["net_amount"], 2))),
                payment_method=row["payment_method"],
                order_status=row["order_status"],
            )
        )
    db.bulk_save_objects(txn_objs)

    # 4. Transaction Items
    ti_objs = [
        RetailTransactionItem(
            dataset_id=dataset_id,
            line_item_id=row["line_item_id"],
            transaction_id=row["transaction_id"],
            transaction_pk=txn_map.get(row["transaction_id"]),
            product_id=row["product_id"],
            quantity=int(row["quantity"]),
            unit_price=Decimal(str(round(row["unit_price"], 2))),
            line_total=Decimal(str(round(row["line_total"], 2))),
        )
        for _, row in cleaned_dfs["Transaction_Items"].iterrows()
    ]
    db.bulk_save_objects(ti_objs)

    # 5. Inventory Movements
    im_objs = [
        RetailInventoryMovement(
            dataset_id=dataset_id,
            movement_id=row["movement_id"],
            product_id=row["product_id"],
            movement_date=row["movement_date"].date() if pd.notna(row["movement_date"]) else None,
            movement_type=row["movement_type"],
            quantity=int(row["quantity"]),
            warehouse_id=row["warehouse_id"],
            reference_no=row["reference_no"] if row["reference_no"] else None,
        )
        for _, row in cleaned_dfs["Inventory_Movements"].iterrows()
    ]
    db.bulk_save_objects(im_objs)

    # 6. Expenses
    exp_objs = [
        RetailExpense(
            dataset_id=dataset_id,
            expense_id=row["expense_id"],
            expense_date=row["expense_date"].date() if pd.notna(row["expense_date"]) else None,
            store_id=row["store_id"],
            category=row["category"],
            amount=Decimal(str(round(row["amount"], 2))),
            vendor=row["vendor"],
        )
        for _, row in cleaned_dfs["Expenses"].iterrows()
    ]
    db.bulk_save_objects(exp_objs)

    # Update dataset record metadata
    row_counts = {sheet: len(df) for sheet, df in cleaned_dfs.items()}
    dataset.status = "ready"
    dataset.row_counts = row_counts
    dataset.cleaning_summary = summary
    dataset.processed_at = datetime.now(timezone.utc)
    dataset.error_message = None

    db.flush()
    logger.info("Successfully ingested %d total rows into database for dataset %s", summary["total_rows_imported"], dataset_id)


def process_dataset_upload(
    db: Session,
    user: User,
    file: UploadFile,
) -> Dataset:
    """
    High-level orchestrator: saves file, creates pending record, cleans data,
    ingests into database with full transaction safety.
    """
    stored_name, file_path, file_size = validate_file_format_and_save(file)

    # Create dataset record in 'pending' status
    dataset = Dataset(
        user_id=user.id,
        original_filename=file.filename or "unknown.xlsx",
        stored_filename=stored_name,
        file_path=file_path,
        file_size_bytes=file_size,
        status="processing",
    )
    db.add(dataset)
    db.commit()
    db.refresh(dataset)

    try:
        # Load and validate sheets & columns
        raw_dfs = load_and_validate_sheets(file_path)

        # Clean, filter, and normalize
        cleaned_dfs, summary = clean_retail_data(raw_dfs)

        # Ingest into database
        insert_cleaned_data_to_db(db, dataset, cleaned_dfs, summary)
        db.commit()
        db.refresh(dataset)
        return dataset

    except Exception as exc:
        db.rollback()
        logger.error("Dataset processing failed for %s: %s", dataset.id, str(exc), exc_info=True)
        dataset.status = "failed"
        dataset.error_message = str(exc)
        db.commit()
        raise


def get_dataset_by_id(db: Session, dataset_id: uuid.UUID, user: User) -> Dataset:
    """Retrieve dataset by ID, ensuring user ownership or admin access."""
    query = select(Dataset).where(Dataset.id == dataset_id)
    if user.role != "admin":
        query = query.where(Dataset.user_id == user.id)

    dataset = db.execute(query).scalar_one_or_none()
    if not dataset:
        raise AppException(
            status_code=404,
            detail=f"Dataset '{dataset_id}' not found or access denied.",
            code="DATASET_NOT_FOUND",
        )
    return dataset


def list_datasets(
    db: Session,
    user: User,
    skip: int = 0,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """List datasets accessible by user with total row counts."""
    query = select(Dataset)
    if user.role != "admin":
        query = query.where(Dataset.user_id == user.id)

    query = query.order_by(Dataset.uploaded_at.desc()).offset(skip).limit(limit)
    datasets = db.execute(query).scalars().all()

    items = []
    for d in datasets:
        total = sum(d.row_counts.values()) if d.row_counts else 0
        items.append({
            "id": d.id,
            "original_filename": d.original_filename,
            "file_size_bytes": d.file_size_bytes,
            "status": d.status,
            "total_rows": total,
            "row_counts": d.row_counts,
            "uploaded_at": d.uploaded_at,
            "processed_at": d.processed_at,
        })
    return items


def get_dataset_preview(
    db: Session,
    dataset: Dataset,
    limit: int = 5,
) -> dict[str, list[dict[str, Any]]]:
    """Retrieve top N sample rows from each table for this dataset."""
    d_id = dataset.id
    previews: dict[str, list[dict[str, Any]]] = {}

    def serialize_row(obj: Any, keys: list[str]) -> dict[str, Any]:
        return {
            k: (getattr(obj, k).isoformat() if isinstance(getattr(obj, k), (date, datetime))
                else float(getattr(obj, k)) if isinstance(getattr(obj, k), Decimal)
                else getattr(obj, k))
            for k in keys
        }

    # Customers
    custs = db.execute(
        select(RetailCustomer).where(RetailCustomer.dataset_id == d_id).limit(limit)
    ).scalars().all()
    previews["Customers"] = [
        serialize_row(c, ["customer_id", "customer_name", "city", "signup_date", "customer_segment", "email"])
        for c in custs
    ]

    # Products
    prods = db.execute(
        select(RetailProduct).where(RetailProduct.dataset_id == d_id).limit(limit)
    ).scalars().all()
    previews["Products"] = [
        serialize_row(p, ["product_id", "product_name", "category", "unit_price", "unit_cost", "reorder_level", "supplier_id"])
        for p in prods
    ]

    # Transactions
    txns = db.execute(
        select(RetailTransaction).where(RetailTransaction.dataset_id == d_id).limit(limit)
    ).scalars().all()
    previews["Transactions"] = [
        serialize_row(t, ["transaction_id", "customer_id", "transaction_date", "store_id", "channel", "gross_amount", "discount", "net_amount", "payment_method", "order_status"])
        for t in txns
    ]

    # Transaction Items
    items = db.execute(
        select(RetailTransactionItem).where(RetailTransactionItem.dataset_id == d_id).limit(limit)
    ).scalars().all()
    previews["Transaction_Items"] = [
        serialize_row(i, ["line_item_id", "transaction_id", "product_id", "quantity", "unit_price", "line_total"])
        for i in items
    ]

    # Inventory Movements
    invs = db.execute(
        select(RetailInventoryMovement).where(RetailInventoryMovement.dataset_id == d_id).limit(limit)
    ).scalars().all()
    previews["Inventory_Movements"] = [
        serialize_row(m, ["movement_id", "product_id", "movement_date", "movement_type", "quantity", "warehouse_id", "reference_no"])
        for m in invs
    ]

    # Expenses
    exps = db.execute(
        select(RetailExpense).where(RetailExpense.dataset_id == d_id).limit(limit)
    ).scalars().all()
    previews["Expenses"] = [
        serialize_row(e, ["expense_id", "expense_date", "store_id", "category", "amount", "vendor"])
        for e in exps
    ]

    return previews


def delete_dataset(db: Session, dataset: Dataset) -> None:
    """Delete dataset record and its associated physical file. DB child tables cascade delete."""
    file_path = dataset.file_path
    db.delete(dataset)
    db.commit()

    if file_path and os.path.exists(file_path):
        try:
            os.remove(file_path)
            logger.info("Deleted physical file %s", file_path)
        except Exception as exc:
            logger.warning("Could not delete file %s: %s", file_path, exc)
