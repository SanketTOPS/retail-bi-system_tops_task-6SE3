"""
app/routers/datasets.py
────────────────────────
Router for Dataset upload, preview, listing, details, and deletion.

Endpoints:
  POST   /api/v1/datasets/upload        — Multipart Excel upload, cleaning, & DB ingestion
  GET    /api/v1/datasets               — List all datasets for current user (or all if admin)
  GET    /api/v1/datasets/{id}          — Fetch dataset details with cleaning summary
  GET    /api/v1/datasets/{id}/preview  — Preview top 5 cleaned rows per entity table
  DELETE /api/v1/datasets/{id}          — Delete dataset and cascade delete all child rows
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User
from app.schemas.dataset import (
    DatasetListItem,
    DatasetPreviewResponse,
    DatasetResponse,
    DatasetUploadResponse,
)
from app.services import dataset_service
from app.utils.deps import get_current_active_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/datasets", tags=["Datasets"])


@router.post(
    "/upload",
    response_model=DatasetUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and ingest dataset",
    description="Accepts a multipart/form-data Excel (.xlsx) file. Validates required sheets/columns, cleans data with pandas, filters period to May 1 - Oct 31 2026, and ingests into PostgreSQL.",
    responses={
        201: {"description": "Dataset uploaded and processed successfully"},
        422: {"description": "Validation error: missing sheets, missing columns, or invalid file format"},
        500: {"description": "Ingestion failed"},
    },
)
def upload_dataset(
    file: UploadFile = File(..., description="Excel file (.xlsx) containing all retail sheets"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> DatasetUploadResponse:
    """Upload and process retail dataset file."""
    dataset = dataset_service.process_dataset_upload(
        db=db,
        user=current_user,
        file=file,
    )
    return DatasetUploadResponse(
        success=True,
        message=f"Dataset '{dataset.original_filename}' uploaded and processed successfully.",
        dataset=DatasetResponse.model_validate(dataset),
    )


@router.get(
    "",
    response_model=list[DatasetListItem],
    summary="List datasets",
    description="Returns a paginated list of datasets uploaded by the user (or all datasets if user is admin).",
)
def list_datasets(
    skip: int = Query(0, ge=0, description="Offset for pagination"),
    limit: int = Query(50, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> list[DatasetListItem]:
    """List accessible datasets."""
    items = dataset_service.list_datasets(db=db, user=current_user, skip=skip, limit=limit)
    return [DatasetListItem(**item) for item in items]


@router.get(
    "/{dataset_id}",
    response_model=DatasetResponse,
    summary="Get dataset details",
    description="Retrieves metadata, ingestion status, row counts, and cleaning summary for a specific dataset.",
    responses={
        200: {"description": "Dataset details"},
        404: {"description": "Dataset not found"},
    },
)
def get_dataset(
    dataset_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> DatasetResponse:
    """Fetch dataset metadata and cleaning summary."""
    dataset = dataset_service.get_dataset_by_id(db=db, dataset_id=dataset_id, user=current_user)
    return DatasetResponse.model_validate(dataset)


@router.get(
    "/{dataset_id}/preview",
    response_model=DatasetPreviewResponse,
    summary="Preview dataset records",
    description="Returns sample records (first 5 rows by default) across each of the 6 retail entities for inspection.",
    responses={
        200: {"description": "Data previews per sheet"},
        404: {"description": "Dataset not found"},
    },
)
def preview_dataset(
    dataset_id: uuid.UUID,
    limit: int = Query(5, ge=1, le=20, description="Number of sample rows per entity"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> DatasetPreviewResponse:
    """Retrieve sample rows from each entity table."""
    dataset = dataset_service.get_dataset_by_id(db=db, dataset_id=dataset_id, user=current_user)
    previews = dataset_service.get_dataset_preview(db=db, dataset_id=dataset, limit=limit)
    return DatasetPreviewResponse(
        dataset_id=dataset.id,
        filename=dataset.original_filename,
        previews=previews,
    )


@router.delete(
    "/{dataset_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete dataset",
    description="Permanently deletes the dataset, its raw file, and cascade deletes all child records across all 6 retail tables.",
    responses={
        200: {"description": "Dataset deleted successfully"},
        404: {"description": "Dataset not found"},
    },
)
def delete_dataset(
    dataset_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Delete dataset and cascade child data."""
    dataset = dataset_service.get_dataset_by_id(db=db, dataset_id=dataset_id, user=current_user)
    dataset_service.delete_dataset(db=db, dataset=dataset)
    return {
        "success": True,
        "message": f"Dataset '{dataset.original_filename}' and all associated records deleted successfully.",
        "deleted_id": str(dataset_id),
    }
