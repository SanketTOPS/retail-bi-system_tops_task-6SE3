"""
app/services/analytics_service.py
──────────────────────────────────
Pure pandas-based business analytics service (NO LLM, exact deterministic calculations).

Calculates KPIs, monthly trends, statistical anomalies, RFM customer segments,
marketing/channel performance, financial breakdowns, and operational metrics.
All return structures are sanitized into JSON-serializable Python native types.
"""

from __future__ import annotations

import logging
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

import numpy as np
import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.retail import (
    RetailCustomer,
    RetailExpense,
    RetailInventoryMovement,
    RetailProduct,
    RetailTransaction,
    RetailTransactionItem,
)

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Helper: Sanitization of NumPy/Pandas types to Python native types
# ─────────────────────────────────────────────────────────────────────────────
def sanitize_value(val: Any) -> Any:
    """Recursively converts NumPy/Pandas/Decimal types into standard JSON-compliant types."""
    if isinstance(val, (np.integer, np.int64, np.int32)):
        return int(val)
    if isinstance(val, (np.floating, np.float64, np.float32)):
        return 0.0 if np.isnan(val) or np.isinf(val) else round(float(val), 2)
    if isinstance(val, (Decimal,)):
        return round(float(val), 2)
    if isinstance(val, (pd.Timestamp, datetime, date)):
        return val.isoformat()
    if isinstance(val, dict):
        return {k: sanitize_value(v) for k, v in val.items()}
    if isinstance(val, list):
        return [sanitize_value(v) for v in val]
    if pd.isna(val):
        return None
    return val


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """Safe division avoiding ZeroDivisionError or NaN."""
    if denominator == 0 or np.isnan(denominator) or np.isnan(numerator):
        return default
    return round(float(numerator / denominator), 4)


# ─────────────────────────────────────────────────────────────────────────────
# Data Fetching Helpers
# ─────────────────────────────────────────────────────────────────────────────
def load_dataset_dataframes(db: Session, dataset_id: uuid.UUID) -> dict[str, pd.DataFrame]:
    """
    Loads all retail tables for a specific dataset_id into pandas DataFrames.
    """
    # 1. Customers
    cust_stmt = select(RetailCustomer).where(RetailCustomer.dataset_id == dataset_id)
    cust_rows = db.execute(cust_stmt).scalars().all()
    df_customers = pd.DataFrame([
        {
            "customer_id": c.customer_id,
            "customer_name": c.customer_name,
            "city": c.city,
            "signup_date": c.signup_date,
            "customer_segment": c.customer_segment,
            "email": c.email,
        }
        for c in cust_rows
    ]) if cust_rows else pd.DataFrame(columns=["customer_id", "customer_name", "city", "signup_date", "customer_segment", "email"])

    # 2. Products
    prod_stmt = select(RetailProduct).where(RetailProduct.dataset_id == dataset_id)
    prod_rows = db.execute(prod_stmt).scalars().all()
    df_products = pd.DataFrame([
        {
            "product_id": p.product_id,
            "product_name": p.product_name,
            "category": p.category,
            "unit_price": float(p.unit_price) if p.unit_price is not None else 0.0,
            "unit_cost": float(p.unit_cost) if p.unit_cost is not None else 0.0,
            "reorder_level": p.reorder_level or 0,
            "supplier_id": p.supplier_id,
        }
        for p in prod_rows
    ]) if prod_rows else pd.DataFrame(columns=["product_id", "product_name", "category", "unit_price", "unit_cost", "reorder_level", "supplier_id"])

    # 3. Transactions
    txn_stmt = select(RetailTransaction).where(RetailTransaction.dataset_id == dataset_id)
    txn_rows = db.execute(txn_stmt).scalars().all()
    df_transactions = pd.DataFrame([
        {
            "transaction_id": t.transaction_id,
            "customer_id": t.customer_id,
            "transaction_date": pd.to_datetime(t.transaction_date),
            "store_id": t.store_id,
            "channel": t.channel,
            "gross_amount": float(t.gross_amount) if t.gross_amount is not None else 0.0,
            "discount": float(t.discount) if t.discount is not None else 0.0,
            "net_amount": float(t.net_amount) if t.net_amount is not None else 0.0,
            "payment_method": t.payment_method,
            "order_status": t.order_status,
        }
        for t in txn_rows
    ]) if txn_rows else pd.DataFrame(columns=["transaction_id", "customer_id", "transaction_date", "store_id", "channel", "gross_amount", "discount", "net_amount", "payment_method", "order_status"])

    # 4. Transaction Items
    item_stmt = select(RetailTransactionItem).where(RetailTransactionItem.dataset_id == dataset_id)
    item_rows = db.execute(item_stmt).scalars().all()
    df_items = pd.DataFrame([
        {
            "line_item_id": i.line_item_id,
            "transaction_id": i.transaction_id,
            "product_id": i.product_id,
            "quantity": i.quantity or 0,
            "unit_price": float(i.unit_price) if i.unit_price is not None else 0.0,
            "line_total": float(i.line_total) if i.line_total is not None else 0.0,
        }
        for i in item_rows
    ]) if item_rows else pd.DataFrame(columns=["line_item_id", "transaction_id", "product_id", "quantity", "unit_price", "line_total"])

    # 5. Inventory Movements
    inv_stmt = select(RetailInventoryMovement).where(RetailInventoryMovement.dataset_id == dataset_id)
    inv_rows = db.execute(inv_stmt).scalars().all()
    df_inventory = pd.DataFrame([
        {
            "movement_id": m.movement_id,
            "product_id": m.product_id,
            "movement_date": pd.to_datetime(m.movement_date),
            "movement_type": m.movement_type,
            "quantity": m.quantity or 0,
            "warehouse_id": m.warehouse_id,
            "reference_no": m.reference_no,
        }
        for m in inv_rows
    ]) if inv_rows else pd.DataFrame(columns=["movement_id", "product_id", "movement_date", "movement_type", "quantity", "warehouse_id", "reference_no"])

    # 6. Expenses
    exp_stmt = select(RetailExpense).where(RetailExpense.dataset_id == dataset_id)
    exp_rows = db.execute(exp_stmt).scalars().all()
    df_expenses = pd.DataFrame([
        {
            "expense_id": e.expense_id,
            "expense_date": pd.to_datetime(e.expense_date),
            "store_id": e.store_id,
            "category": e.category,
            "amount": float(e.amount) if e.amount is not None else 0.0,
            "vendor": e.vendor,
        }
        for e in exp_rows
    ]) if exp_rows else pd.DataFrame(columns=["expense_id", "expense_date", "store_id", "category", "amount", "vendor"])

    return {
        "customers": df_customers,
        "products": df_products,
        "transactions": df_transactions,
        "items": df_items,
        "inventory": df_inventory,
        "expenses": df_expenses,
    }


# ─────────────────────────────────────────────────────────────────────────────
# 1. KPI Summary
# ─────────────────────────────────────────────────────────────────────────────
def get_kpi_summary(db: Session, dataset_id: uuid.UUID) -> dict[str, Any]:
    """
    Calculates executive KPI summary:
      - Total Revenue, Total Expenses, COGS, Gross Profit, Net Profit, Profit Margin %
      - Order Count, Average Order Value (AOV)
      - Unique Customers, Repeat Customer Rate %
      - Retail-Specific: Return Rate %, Cancellation Rate %, Inventory Turnover, Stockout Count
    """
    dfs = load_dataset_dataframes(db, dataset_id)
    txns = dfs["transactions"]
    items = dfs["items"]
    prods = dfs["products"]
    exps = dfs["expenses"]
    inv = dfs["inventory"]

    if txns.empty:
        return {"message": "No transaction data available for this dataset"}

    # Completed orders for sales calculations
    completed_txns = txns[txns["order_status"] == "Completed"]
    total_revenue = float(completed_txns["net_amount"].sum())
    total_gross = float(completed_txns["gross_amount"].sum())
    total_discount = float(completed_txns["discount"].sum())
    order_count = int(len(completed_txns))
    aov = safe_divide(total_revenue, order_count)

    # All transactions for rates
    all_orders_count = int(len(txns))
    returned_orders = int((txns["order_status"] == "Returned").sum())
    cancelled_orders = int((txns["order_status"] == "Cancelled").sum())
    return_rate_pct = round(safe_divide(returned_orders, all_orders_count) * 100, 2)
    cancellation_rate_pct = round(safe_divide(cancelled_orders, all_orders_count) * 100, 2)

    # Total Expenses (Operating Expenses)
    total_expenses = float(exps["amount"].sum()) if not exps.empty else 0.0

    # Calculate Cost of Goods Sold (COGS) by joining completed line items with product unit_cost
    if not items.empty and not prods.empty:
        completed_ids = set(completed_txns["transaction_id"])
        completed_items = items[items["transaction_id"].isin(completed_ids)]
        items_with_cost = completed_items.merge(prods[["product_id", "unit_cost"]], on="product_id", how="left")
        items_with_cost["cogs"] = items_with_cost["quantity"] * items_with_cost["unit_cost"].fillna(0.0)
        total_cogs = float(items_with_cost["cogs"].sum())
    else:
        total_cogs = 0.0

    gross_profit = total_revenue - total_cogs
    net_profit = gross_profit - total_expenses
    gross_margin_pct = round(safe_divide(gross_profit, total_revenue) * 100, 2)
    net_profit_margin_pct = round(safe_divide(net_profit, total_revenue) * 100, 2)

    # Customer Metrics
    unique_customers = int(completed_txns["customer_id"].nunique())
    cust_order_counts = completed_txns["customer_id"].value_counts()
    repeat_customers = int((cust_order_counts >= 2).sum())
    repeat_rate_pct = round(safe_divide(repeat_customers, unique_customers) * 100, 2)

    # Inventory Metrics (Turnover & Stockout count)
    stockout_count = 0
    inventory_turnover = 0.0
    if not inv.empty and not prods.empty:
        # Calculate net inventory per product: Restock + Return - Sale
        inv_copy = inv.copy()
        inv_copy["signed_qty"] = inv_copy.apply(
            lambda r: r["quantity"] if r["movement_type"] in ["Restock", "Return"]
            else -r["quantity"] if r["movement_type"] in ["Sale", "Transfer"]
            else r["quantity"],
            axis=1,
        )
        current_stock = inv_copy.groupby("product_id")["signed_qty"].sum().reset_index()
        stock_df = prods.merge(current_stock, on="product_id", how="left")
        stock_df["signed_qty"] = stock_df["signed_qty"].fillna(0)
        stockout_count = int((stock_df["signed_qty"] <= stock_df["reorder_level"]).sum())

        avg_inventory_value = float((stock_df["signed_qty"].clip(lower=0) * stock_df["unit_cost"]).sum())
        if avg_inventory_value > 0 and total_cogs > 0:
            inventory_turnover = round(safe_divide(total_cogs, avg_inventory_value), 2)

    res = {
        "dataset_period": "2026-05-01 to 2026-10-31",
        "financial_kpis": {
            "total_revenue": round(total_revenue, 2),
            "total_gross_sales": round(total_gross, 2),
            "total_discount": round(total_discount, 2),
            "total_cogs": round(total_cogs, 2),
            "gross_profit": round(gross_profit, 2),
            "total_operating_expenses": round(total_expenses, 2),
            "net_profit": round(net_profit, 2),
            "gross_margin_pct": gross_margin_pct,
            "net_profit_margin_pct": net_profit_margin_pct,
        },
        "sales_kpis": {
            "completed_orders": order_count,
            "total_transactions": all_orders_count,
            "average_order_value": round(aov, 2),
            "return_rate_pct": return_rate_pct,
            "cancellation_rate_pct": cancellation_rate_pct,
        },
        "customer_kpis": {
            "unique_customers": unique_customers,
            "repeat_customers": repeat_customers,
            "repeat_customer_rate_pct": repeat_rate_pct,
        },
        "operational_kpis": {
            "stockout_count": stockout_count,
            "inventory_turnover_ratio": inventory_turnover,
        },
    }
    return sanitize_value(res)


# ─────────────────────────────────────────────────────────────────────────────
# 2. Monthly Trends & MoM Growth
# ─────────────────────────────────────────────────────────────────────────────
def get_monthly_trends(db: Session, dataset_id: uuid.UUID) -> dict[str, Any]:
    """
    Computes month-wise sales, expenses, profits, order volume, and Month-over-Month (MoM) % changes.
    """
    dfs = load_dataset_dataframes(db, dataset_id)
    txns = dfs["transactions"]
    items = dfs["items"]
    prods = dfs["products"]
    exps = dfs["expenses"]

    if txns.empty:
        return {"months": []}

    completed_txns = txns[txns["order_status"] == "Completed"].copy()
    completed_txns["year_month"] = completed_txns["transaction_date"].dt.to_period("M").astype(str)

    # Monthly revenue & orders
    monthly_sales = completed_txns.groupby("year_month").agg(
        revenue=("net_amount", "sum"),
        gross_sales=("gross_amount", "sum"),
        discount=("discount", "sum"),
        order_count=("transaction_id", "count"),
        active_customers=("customer_id", "nunique"),
    ).reset_index()

    # Monthly expenses
    if not exps.empty:
        exps_copy = exps.copy()
        exps_copy["year_month"] = exps_copy["expense_date"].dt.to_period("M").astype(str)
        monthly_exp = exps_copy.groupby("year_month")["amount"].sum().reset_index().rename(columns={"amount": "expenses"})
    else:
        monthly_exp = pd.DataFrame(columns=["year_month", "expenses"])

    # Monthly COGS
    if not items.empty and not prods.empty:
        item_merged = items.merge(prods[["product_id", "unit_cost"]], on="product_id", how="left")
        item_merged["cogs"] = item_merged["quantity"] * item_merged["unit_cost"].fillna(0.0)
        txn_cogs = item_merged.groupby("transaction_id")["cogs"].sum().reset_index()
        completed_txns = completed_txns.merge(txn_cogs, on="transaction_id", how="left")
        completed_txns["cogs"] = completed_txns["cogs"].fillna(0.0)
        monthly_cogs = completed_txns.groupby("year_month")["cogs"].sum().reset_index()
    else:
        monthly_cogs = pd.DataFrame(columns=["year_month", "cogs"])

    # Merge all
    df_merged = monthly_sales.merge(monthly_exp, on="year_month", how="outer")
    df_merged = df_merged.merge(monthly_cogs, on="year_month", how="outer").fillna(0.0)
    df_merged = df_merged.sort_values("year_month")

    df_merged["gross_profit"] = df_merged["revenue"] - df_merged["cogs"]
    df_merged["net_profit"] = df_merged["gross_profit"] - df_merged["expenses"]
    df_merged["gross_margin_pct"] = np.where(df_merged["revenue"] > 0, (df_merged["gross_profit"] / df_merged["revenue"]) * 100, 0.0)
    df_merged["net_margin_pct"] = np.where(df_merged["revenue"] > 0, (df_merged["net_profit"] / df_merged["revenue"]) * 100, 0.0)
    df_merged["aov"] = np.where(df_merged["order_count"] > 0, df_merged["revenue"] / df_merged["order_count"], 0.0)

    # Calculate MoM growth %
    df_merged["revenue_mom_pct"] = df_merged["revenue"].pct_change() * 100
    df_merged["expenses_mom_pct"] = df_merged["expenses"].pct_change() * 100
    df_merged["net_profit_mom_pct"] = df_merged["net_profit"].pct_change() * 100
    df_merged["orders_mom_pct"] = df_merged["order_count"].pct_change() * 100

    records = df_merged.to_dict(orient="records")
    return {"months": sanitize_value(records)}


# ─────────────────────────────────────────────────────────────────────────────
# 3. Statistical Anomaly Detection
# ─────────────────────────────────────────────────────────────────────────────
def detect_anomalies(db: Session, dataset_id: uuid.UUID) -> dict[str, Any]:
    """
    Detects operational and financial anomalies:
      - Months where metrics deviate > 1.5 standard deviations from the mean
      - Month-over-Month (MoM) jumps or drops > 20%
      - Sudden spikes in expense categories or return rates
    """
    trends_data = get_monthly_trends(db, dataset_id)
    months = trends_data.get("months", [])
    if len(months) < 2:
        return {"anomalies": [], "summary": "Insufficient monthly data for statistical anomaly detection"}

    df = pd.DataFrame(months)
    anomalies: list[dict[str, Any]] = []

    metrics_to_check = [
        ("revenue", "Revenue", "INR"),
        ("expenses", "Expenses", "INR"),
        ("net_profit", "Net Profit", "INR"),
        ("order_count", "Order Volume", "orders"),
        ("aov", "Average Order Value", "INR"),
    ]

    for col, name, unit in metrics_to_check:
        mean_val = float(df[col].mean())
        std_val = float(df[col].std()) if len(df) > 1 else 0.0

        for idx, row in df.iterrows():
            curr_val = float(row[col])
            mom_col = f"{col}_mom_pct" if f"{col}_mom_pct" in df.columns else None
            mom_pct = float(row[mom_col]) if mom_col and pd.notna(row[mom_col]) else 0.0

            # 1. Standard deviation anomaly (> 1.5 sigma)
            if std_val > 0:
                z_score = (curr_val - mean_val) / std_val
                if abs(z_score) >= 1.5:
                    direction = "Spike" if z_score > 0 else "Drop"
                    anomalies.append({
                        "period": row["year_month"],
                        "metric": name,
                        "type": f"Statistical {direction} (>1.5 Std Dev)",
                        "severity": "High" if abs(z_score) >= 2.0 else "Medium",
                        "current_value": round(curr_val, 2),
                        "baseline_mean": round(mean_val, 2),
                        "deviation_score": round(float(z_score), 2),
                        "explanation": f"{name} of {curr_val:,.2f} {unit} in {row['year_month']} is {abs(z_score):.1f}σ away from 6-month mean ({mean_val:,.2f}).",
                    })

            # 2. Significant MoM change (> 20%)
            if idx > 0 and abs(mom_pct) >= 20.0:
                direction = "Surge" if mom_pct > 0 else "Contraction"
                anomalies.append({
                    "period": row["year_month"],
                    "metric": name,
                    "type": f"Rapid MoM {direction} (>20%)",
                    "severity": "High" if abs(mom_pct) >= 35.0 else "Medium",
                    "current_value": round(curr_val, 2),
                    "baseline_mean": round(mean_val, 2),
                    "deviation_score": round(float(mom_pct), 2),
                    "explanation": f"{name} experienced a {mom_pct:+.1f}% change compared to the preceding month.",
                })

    # 3. Product category sales anomalies
    dfs = load_dataset_dataframes(db, dataset_id)
    txns = dfs["transactions"]
    items = dfs["items"]
    prods = dfs["products"]
    if not txns.empty and not items.empty and not prods.empty:
        completed_ids = set(txns[txns["order_status"] == "Completed"]["transaction_id"])
        c_items = items[items["transaction_id"].isin(completed_ids)].merge(prods[["product_id", "category"]], on="product_id", how="left")
        cat_rev = c_items.groupby("category")["line_total"].sum()
        if len(cat_rev) > 2:
            cat_mean = float(cat_rev.mean())
            cat_std = float(cat_rev.std())
            for cat, rev in cat_rev.items():
                if cat_std > 0 and abs(rev - cat_mean) / cat_std >= 1.5:
                    anomalies.append({
                        "period": "Overall",
                        "metric": f"Category Share: {cat}",
                        "type": "Category Concentration Anomaly",
                        "severity": "Medium",
                        "current_value": round(float(rev), 2),
                        "baseline_mean": round(cat_mean, 2),
                        "deviation_score": round((rev - cat_mean) / cat_std, 2),
                        "explanation": f"Category '{cat}' revenue of {rev:,.2f} INR significantly deviates from category average ({cat_mean:,.2f}).",
                    })

    return {
        "anomaly_count": len(anomalies),
        "anomalies": sanitize_value(anomalies),
    }


# ─────────────────────────────────────────────────────────────────────────────
# 4. Customer Segmentation (RFM + Spend Analysis)
# ─────────────────────────────────────────────────────────────────────────────
def get_customer_segments(db: Session, dataset_id: uuid.UUID) -> dict[str, Any]:
    """
    Performs RFM (Recency, Frequency, Monetary) segmentation and customer lifetime tiering.
    Identifies high-value customers, churn risks, and loyal segments.
    """
    dfs = load_dataset_dataframes(db, dataset_id)
    txns = dfs["transactions"]
    custs = dfs["customers"]

    if txns.empty or custs.empty:
        return {"segments": [], "summary": "No customer transaction data available"}

    completed = txns[txns["order_status"] == "Completed"].copy()
    if completed.empty:
        return {"segments": [], "summary": "No completed transactions"}

    # Reference date is max transaction date in dataset
    snapshot_date = completed["transaction_date"].max()

    rfm = completed.groupby("customer_id").agg(
        recency_days=("transaction_date", lambda d: (snapshot_date - d.max()).days),
        frequency=("transaction_id", "count"),
        monetary=("net_amount", "sum"),
    ).reset_index()

    # Dynamic quantile scores (1 to 4)
    r_labels = [4, 3, 2, 1]  # Lower recency days = higher score
    f_labels = [1, 2, 3, 4]
    m_labels = [1, 2, 3, 4]

    rfm["r_score"] = pd.qcut(rfm["recency_days"].rank(method="first"), q=4, labels=r_labels).astype(int)
    rfm["f_score"] = pd.qcut(rfm["frequency"].rank(method="first"), q=4, labels=f_labels).astype(int)
    rfm["m_score"] = pd.qcut(rfm["monetary"].rank(method="first"), q=4, labels=m_labels).astype(int)

    def assign_segment(row: pd.Series) -> str:
        r, f, m = row["r_score"], row["f_score"], row["m_score"]
        if r >= 3 and f >= 3 and m >= 3:
            return "Champions / VIP"
        elif r >= 3 and f >= 2:
            return "Loyal Customers"
        elif r >= 3 and f == 1:
            return "Recent / New Buyers"
        elif r <= 2 and f >= 3:
            return "At Risk (High Value)"
        elif r == 1 and f <= 2:
            return "Dormant / Churned"
        else:
            return "Potential Loyalists"

    rfm["segment"] = rfm.apply(assign_segment, axis=1)

    # Segment summary
    total_rev = float(rfm["monetary"].sum())
    total_custs = len(rfm)

    seg_summary = rfm.groupby("segment").agg(
        customer_count=("customer_id", "count"),
        total_revenue=("monetary", "sum"),
        avg_revenue_per_customer=("monetary", "mean"),
        avg_frequency=("frequency", "mean"),
        avg_recency_days=("recency_days", "mean"),
    ).reset_index()

    seg_summary["customer_share_pct"] = (seg_summary["customer_count"] / total_custs) * 100
    seg_summary["revenue_share_pct"] = np.where(total_rev > 0, (seg_summary["total_revenue"] / total_rev) * 100, 0.0)

    # Add actionable churn risk flag
    risk_mapping = {
        "Champions / VIP": "Low",
        "Loyal Customers": "Low",
        "Recent / New Buyers": "Medium",
        "Potential Loyalists": "Medium",
        "At Risk (High Value)": "Critical",
        "Dormant / Churned": "High",
    }
    seg_summary["churn_risk"] = seg_summary["segment"].map(risk_mapping).fillna("Medium")

    return {
        "total_analyzed_customers": total_custs,
        "segments": sanitize_value(seg_summary.to_dict(orient="records")),
    }


# ─────────────────────────────────────────────────────────────────────────────
# 5. Marketing & Channel Performance
# ─────────────────────────────────────────────────────────────────────────────
def get_marketing_performance(db: Session, dataset_id: uuid.UUID) -> dict[str, Any]:
    """
    Evaluates sales channel productivity (In-store, Mobile App, Online, Phone)
    and payment method adoption rates.
    """
    dfs = load_dataset_dataframes(db, dataset_id)
    txns = dfs["transactions"]

    if txns.empty:
        return {"channels": [], "payment_methods": []}

    completed = txns[txns["order_status"] == "Completed"]
    total_net = float(completed["net_amount"].sum())
    total_orders = len(completed)

    # 1. Channel Performance
    channel_perf = completed.groupby("channel").agg(
        order_count=("transaction_id", "count"),
        gross_sales=("gross_amount", "sum"),
        total_discount=("discount", "sum"),
        net_revenue=("net_amount", "sum"),
        unique_buyers=("customer_id", "nunique"),
    ).reset_index()

    channel_perf["revenue_share_pct"] = np.where(total_net > 0, (channel_perf["net_revenue"] / total_net) * 100, 0.0)
    channel_perf["aov"] = np.where(channel_perf["order_count"] > 0, channel_perf["net_revenue"] / channel_perf["order_count"], 0.0)
    channel_perf["effective_discount_pct"] = np.where(
        channel_perf["gross_sales"] > 0, (channel_perf["total_discount"] / channel_perf["gross_sales"]) * 100, 0.0
    )

    # 2. Payment Method Performance
    payment_perf = completed.groupby("payment_method").agg(
        transaction_count=("transaction_id", "count"),
        total_amount=("net_amount", "sum"),
    ).reset_index()
    payment_perf["transaction_share_pct"] = np.where(total_orders > 0, (payment_perf["transaction_count"] / total_orders) * 100, 0.0)

    return {
        "channels": sanitize_value(channel_perf.to_dict(orient="records")),
        "payment_methods": sanitize_value(payment_perf.to_dict(orient="records")),
    }


# ─────────────────────────────────────────────────────────────────────────────
# 6. Financial Breakdown & Cost Ratios
# ─────────────────────────────────────────────────────────────────────────────
def get_financial_breakdown(db: Session, dataset_id: uuid.UUID) -> dict[str, Any]:
    """
    Detailed cost and profitability breakdown:
      - Expense distribution by category and vendor
      - Cost-to-Revenue ratios
      - Product category gross margin breakdown
    """
    dfs = load_dataset_dataframes(db, dataset_id)
    txns = dfs["transactions"]
    items = dfs["items"]
    prods = dfs["products"]
    exps = dfs["expenses"]

    # 1. Expense by Category
    exp_by_cat: list[dict[str, Any]] = []
    top_vendors: list[dict[str, Any]] = []
    total_exp = 0.0

    if not exps.empty:
        total_exp = float(exps["amount"].sum())
        cat_df = exps.groupby("category").agg(
            total_amount=("amount", "sum"),
            transaction_count=("expense_id", "count"),
        ).reset_index()
        cat_df["share_pct"] = np.where(total_exp > 0, (cat_df["total_amount"] / total_exp) * 100, 0.0)
        exp_by_cat = cat_df.sort_values("total_amount", ascending=False).to_dict(orient="records")

        ven_df = exps.groupby("vendor")["amount"].sum().reset_index()
        top_vendors = ven_df.sort_values("amount", ascending=False).head(5).to_dict(orient="records")

    # 2. Category Margin Breakdown
    cat_margins: list[dict[str, Any]] = []
    total_rev = 0.0
    total_cogs = 0.0

    if not txns.empty and not items.empty and not prods.empty:
        completed_txns = txns[txns["order_status"] == "Completed"]
        total_rev = float(completed_txns["net_amount"].sum())

        c_items = items[items["transaction_id"].isin(set(completed_txns["transaction_id"]))].copy()
        c_items = c_items.merge(prods[["product_id", "category", "unit_cost"]], on="product_id", how="left")
        c_items["cogs"] = c_items["quantity"] * c_items["unit_cost"].fillna(0.0)
        total_cogs = float(c_items["cogs"].sum())

        cat_sales = c_items.groupby("category").agg(
            revenue=("line_total", "sum"),
            cogs=("cogs", "sum"),
            units_sold=("quantity", "sum"),
        ).reset_index()
        cat_sales["gross_profit"] = cat_sales["revenue"] - cat_sales["cogs"]
        cat_sales["gross_margin_pct"] = np.where(cat_sales["revenue"] > 0, (cat_sales["gross_profit"] / cat_sales["revenue"]) * 100, 0.0)
        cat_margins = cat_sales.sort_values("revenue", ascending=False).to_dict(orient="records")

    total_costs = total_cogs + total_exp
    cost_to_revenue_ratio = safe_divide(total_costs, total_rev)

    return {
        "total_operating_expenses": round(total_exp, 2),
        "total_cogs": round(total_cogs, 2),
        "cost_to_revenue_ratio": cost_to_revenue_ratio,
        "expenses_by_category": sanitize_value(exp_by_cat),
        "top_vendors": sanitize_value(top_vendors),
        "category_profitability": sanitize_value(cat_margins),
    }


# ─────────────────────────────────────────────────────────────────────────────
# 7. Operational & Inventory Metrics
# ─────────────────────────────────────────────────────────────────────────────
def get_operational_metrics(db: Session, dataset_id: uuid.UUID) -> dict[str, Any]:
    """
    Evaluates inventory distribution, warehouse throughput, reorder/stockout warnings,
    and store operational performance.
    """
    dfs = load_dataset_dataframes(db, dataset_id)
    inv = dfs["inventory"]
    prods = dfs["products"]
    txns = dfs["transactions"]
    exps = dfs["expenses"]

    # 1. Warehouse movements throughput
    wh_throughput: list[dict[str, Any]] = []
    movement_type_breakdown: list[dict[str, Any]] = []
    stockout_alerts: list[dict[str, Any]] = []

    if not inv.empty:
        wh_df = inv.groupby("warehouse_id").agg(
            total_movements=("movement_id", "count"),
            units_handled=("quantity", "sum"),
        ).reset_index()
        wh_throughput = wh_df.to_dict(orient="records")

        mov_df = inv.groupby("movement_type").agg(
            count=("movement_id", "count"),
            total_units=("quantity", "sum"),
        ).reset_index()
        movement_type_breakdown = mov_df.to_dict(orient="records")

        # Current remaining inventory estimate
        if not prods.empty:
            inv_copy = inv.copy()
            inv_copy["signed_qty"] = inv_copy.apply(
                lambda r: r["quantity"] if r["movement_type"] in ["Restock", "Return"]
                else -r["quantity"] if r["movement_type"] in ["Sale", "Transfer"]
                else r["quantity"],
                axis=1,
            )
            net_inv = inv_copy.groupby("product_id")["signed_qty"].sum().reset_index()
            stock_df = prods.merge(net_inv, on="product_id", how="left")
            stock_df["current_stock"] = stock_df["signed_qty"].fillna(0).astype(int)

            # Stockout warning: current_stock <= reorder_level
            at_risk = stock_df[stock_df["current_stock"] <= stock_df["reorder_level"]]
            stockout_alerts = at_risk[[
                "product_id", "product_name", "category", "current_stock", "reorder_level", "supplier_id"
            ]].head(15).to_dict(orient="records")

    # 2. Store Efficiency (Revenue vs. Expenses per store_id)
    store_perf: list[dict[str, Any]] = []
    if not txns.empty:
        completed = txns[txns["order_status"] == "Completed"]
        store_sales = completed.groupby("store_id").agg(
            revenue=("net_amount", "sum"),
            order_count=("transaction_id", "count"),
        ).reset_index()

        store_exp = exps.groupby("store_id")["amount"].sum().reset_index().rename(columns={"amount": "expenses"}) if not exps.empty else pd.DataFrame(columns=["store_id", "expenses"])

        store_merged = store_sales.merge(store_exp, on="store_id", how="outer").fillna(0.0)
        store_merged["expense_ratio_pct"] = np.where(
            store_merged["revenue"] > 0, (store_merged["expenses"] / store_merged["revenue"]) * 100, 0.0
        )
        store_perf = store_merged.sort_values("revenue", ascending=False).to_dict(orient="records")

    return {
        "warehouse_throughput": sanitize_value(wh_throughput),
        "movement_type_distribution": sanitize_value(movement_type_breakdown),
        "stockout_alerts_count": len(stockout_alerts),
        "sample_stockout_alerts": sanitize_value(stockout_alerts),
        "store_performance": sanitize_value(store_perf),
    }
