"""
app/routers/reports.py
──────────────────────
PDF Report Generation & Retrieval Router — Module 11

Responsibilities:
  - Expose the PDF generation endpoint (GET /reports/{analysis_id}/pdf)
  - Expose a report list endpoint (GET /reports)
  - Expose a JSON report detail endpoint (GET /reports/{analysis_id})
  - Stream or serve the generated PDF as a downloadable file response

Design Decisions:
  - PDFs are generated ON DEMAND on first request and cached to disk thereafter.
    Subsequent requests re-use the cached file, avoiding redundant ReportLab work.
  - FileResponse is used (not StreamingResponse) because ReportLab writes to disk
    first (two-pass page numbering requires knowing total pages before writing headers).
  - The endpoint guards against generating a PDF for unverified reports: the HITL
    principle — only VERIFIED or VERIFIED_WITH_WARNINGS reports are publishable.
  - Admin can list all reports; regular users see only reports from their own datasets.

Viva Question: Why use FileResponse instead of StreamingResponse?
Answer: ReportLab's NumberedCanvas requires two build passes (first to count pages,
second to write page-N-of-M). It must write the entire PDF to disk before it is
complete. FileResponse reads from the completed file, which is both simpler and correct.
StreamingResponse would require holding the whole PDF in memory anyway (via BytesIO),
so there is no benefit and increased complexity.
"""

from __future__ import annotations

import logging
import os
import uuid

from fastapi import APIRouter, Depends, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.main import AppException
from app.models.analysis import Analysis
from app.models.dataset import Dataset
from app.models.report import Report
from app.schemas.report import ReportListItem, ReportDetailResponse
from app.services.report_service import generate_pdf_report
from app.utils.deps import get_current_active_user, require_roles
from app.models.user import User

logger = logging.getLogger("retail_bi.reports")

router = APIRouter(prefix="/reports", tags=["Reports"])


# ─────────────────────────────────────────────────────────────────────────────
# Helper: ownership check
# ─────────────────────────────────────────────────────────────────────────────

def _assert_report_access(report: Report, analysis: Analysis, current_user: User) -> None:
    """
    Raise 403 if a non-admin user tries to access a report from a dataset
    they do not own.

    Design: Row-level security implemented in Python rather than the DB because
    the ownership chain is Dataset → Analysis → Report and we have already loaded
    the ORM objects at this point. A DB-level RLS policy would be more robust in
    a multi-tenant production system, but Python guards are sufficient here.
    """
    if current_user.role == "admin":
        return  # admins see everything
    if str(analysis.dataset.user_id) != str(current_user.id):
        raise AppException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this report.",
            code="REPORT_ACCESS_DENIED",
        )


# ─────────────────────────────────────────────────────────────────────────────
# GET /reports  — List reports (current user; admin sees all)
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "",
    summary="List all BI reports",
    response_description="Paginated list of report summaries",
    status_code=status.HTTP_200_OK,
)
def list_reports(
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> dict:
    """
    Returns a list of reports visible to the authenticated user.

    - **Admin**: sees reports across all users / datasets.
    - **Non-admin**: sees only reports produced from their own datasets.

    Fields returned per report:
      report_id, analysis_id, dataset_id, title, verification_status,
      has_pdf (bool — PDF file exists on disk), created_at.

    Pagination:
      Use `skip` / `limit` query params (default: first 20).
    """
    stmt = (
        select(Report, Analysis, Dataset)
        .join(Analysis, Report.analysis_id == Analysis.id)
        .join(Dataset, Analysis.dataset_id == Dataset.id)
        .order_by(Report.created_at.desc())
        .offset(skip)
        .limit(limit)
    )

    if current_user.role != "admin":
        stmt = stmt.where(Dataset.user_id == current_user.id)

    rows = db.execute(stmt).all()

    items = []
    for report, analysis, dataset in rows:
        items.append({
            "report_id": str(report.id),
            "analysis_id": str(report.analysis_id),
            "dataset_id": str(dataset.id),
            "dataset_name": dataset.name,
            "title": report.title,
            "verification_status": report.verification_status,
            "has_pdf": bool(report.pdf_path and os.path.exists(report.pdf_path)),
            "created_at": report.created_at.isoformat() if report.created_at else None,
        })

    return {
        "success": True,
        "data": {
            "items": items,
            "count": len(items),
            "skip": skip,
            "limit": limit,
        },
    }


# ─────────────────────────────────────────────────────────────────────────────
# GET /reports/{analysis_id}  — Report JSON detail
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/{analysis_id}",
    summary="Get report JSON for an analysis",
    response_description="Full structured report content as JSON",
    status_code=status.HTTP_200_OK,
)
def get_report_json(
    analysis_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> dict:
    """
    Returns the full structured JSON content of the verified BI report.

    This is the same content that gets rendered into the PDF — it can be used
    by the frontend to display an interactive report dashboard instead of a
    static PDF.

    Raises:
      - 404 if the analysis or report does not exist.
      - 403 if the requesting user does not own the analysis dataset.

    Design Note: Separating this endpoint from /analysis/{id}/report (Module 8)
    provides a dedicated, semantically correct URL under /reports and returns
    richer dataset metadata alongside the report content.
    """
    analysis = db.get(Analysis, analysis_id)
    if not analysis:
        raise AppException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analysis not found.",
            code="ANALYSIS_NOT_FOUND",
        )

    report = db.scalar(select(Report).where(Report.analysis_id == analysis_id))
    if not report:
        raise AppException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No report found for this analysis. The analysis may still be running.",
            code="REPORT_NOT_FOUND",
        )

    # Eager-load dataset for ownership check
    dataset = db.get(Dataset, analysis.dataset_id)
    analysis.dataset = dataset  # attach for helper
    _assert_report_access(report, analysis, current_user)

    return {
        "success": True,
        "data": {
            "report_id": str(report.id),
            "analysis_id": str(report.analysis_id),
            "dataset_id": str(analysis.dataset_id),
            "title": report.title,
            "executive_summary": report.executive_summary,
            "verification_status": report.verification_status,
            "verification_notes": report.verification_notes,
            "content": report.content_json or {},
            "has_pdf": bool(report.pdf_path and os.path.exists(report.pdf_path)),
            "created_at": report.created_at.isoformat() if report.created_at else None,
        },
    }


# ─────────────────────────────────────────────────────────────────────────────
# GET /reports/{analysis_id}/pdf  — Generate (if needed) & serve PDF
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/{analysis_id}/pdf",
    summary="Download the PDF report for an analysis",
    response_description="PDF file download (application/pdf)",
    status_code=status.HTTP_200_OK,
    # FastAPI won't document the response body for FileResponse correctly without
    # the response_class hint, but we keep it explicit for Swagger correctness.
    responses={
        200: {
            "content": {"application/pdf": {}},
            "description": "Returns a downloadable PDF file.",
        },
        404: {"description": "Analysis or report not found."},
        403: {"description": "Access denied."},
        409: {"description": "Report is not yet verified — PDF generation refused."},
    },
)
def download_pdf_report(
    analysis_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> FileResponse:
    """
    Generates the PDF BI report (if not already cached on disk) and returns it
    as a downloadable file.

    **Generation lifecycle:**
    1. Load the Analysis and its Report record from the DB.
    2. Guard: only VERIFIED or VERIFIED_WITH_WARNINGS reports can be published.
    3. If `report.pdf_path` points to an existing file → skip generation (cache hit).
    4. Otherwise call `generate_pdf_report(db, analysis_id)` from report_service.
       - ReportLab renders all 11 sections.
       - Matplotlib charts are rendered to PNG bytes in memory and embedded.
       - Two-pass NumberedCanvas writes page-N-of-M footers.
    5. Return `FileResponse` with correct Content-Disposition filename.

    **Why cache?**
    PDF generation is CPU-bound (chart rendering + ReportLab layout).  Caching
    to disk after first generation ensures O(1) subsequent requests without
    database or matplotlib overhead.

    **Security:**
    Non-admin users can only download PDFs for reports from their own datasets.
    """
    # ── 1. Load analysis ──────────────────────────────────────────────────────
    analysis = db.get(Analysis, analysis_id)
    if not analysis:
        raise AppException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analysis not found.",
            code="ANALYSIS_NOT_FOUND",
        )

    # Eager-load dataset for ownership / filename
    dataset = db.get(Dataset, analysis.dataset_id)
    if not dataset:
        raise AppException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dataset record not found.",
            code="DATASET_NOT_FOUND",
        )
    analysis.dataset = dataset  # attach for _assert_report_access

    # ── 2. Load report ────────────────────────────────────────────────────────
    report = db.scalar(select(Report).where(Report.analysis_id == analysis_id))
    if not report:
        raise AppException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No report found for this analysis. Run the analysis first.",
            code="REPORT_NOT_FOUND",
        )

    # ── 3. Ownership guard ────────────────────────────────────────────────────
    _assert_report_access(report, analysis, current_user)

    # ── 4. Verification guard ─────────────────────────────────────────────────
    # Only emit PDFs for verified reports. Unverified content could contain
    # hallucinated numbers that management must not see in an official document.
    allowed_statuses = {"VERIFIED", "VERIFIED_WITH_WARNINGS"}
    if report.verification_status.upper() not in allowed_statuses:
        raise AppException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"PDF generation is only available for verified reports. "
                f"Current status: {report.verification_status!r}. "
                "Re-run the analysis or wait for verification to complete."
            ),
            code="REPORT_NOT_VERIFIED",
        )

    # ── 5. Cache hit: serve existing file ─────────────────────────────────────
    if report.pdf_path and os.path.exists(report.pdf_path):
        logger.info(
            "Cache hit: serving existing PDF for analysis %s from %s",
            analysis_id,
            report.pdf_path,
        )
        pdf_path = report.pdf_path
    else:
        # ── 6. Generate PDF ───────────────────────────────────────────────────
        logger.info("Generating PDF report for analysis %s …", analysis_id)
        try:
            pdf_path = generate_pdf_report(db, analysis_id)
        except Exception as exc:
            logger.exception("PDF generation failed for analysis %s", analysis_id)
            raise AppException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"PDF generation failed: {exc}",
                code="PDF_GENERATION_FAILED",
            ) from exc

    # ── 7. Build a safe, human-readable filename ──────────────────────────────
    safe_name = (dataset.name or "report").replace(" ", "_").replace("/", "-")[:50]
    filename = f"BI_Report_{safe_name}_{str(analysis_id)[:8]}.pdf"

    logger.info("Serving PDF %s to user %s", filename, current_user.email)

    return FileResponse(
        path=pdf_path,
        media_type="application/pdf",
        filename=filename,
        headers={
            # Instruct browsers to download rather than display inline
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )
