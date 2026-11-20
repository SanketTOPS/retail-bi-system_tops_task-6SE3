"""
app/routers/analysis.py
────────────────────────
Router for initiating multi-agent analyses, tracking real-time agent execution status,
reading agent logs, and retrieving final verified reports.

Endpoints:
  POST /api/v1/analysis/run         — Launch analysis in background (concurrency-locked per dataset)
  GET  /api/v1/analysis/{id}/status — Real-time progress, current agent, per-agent status
  GET  /api/v1/analysis/{id}/logs   — Detailed execution logs of each agent
  GET  /api/v1/analysis/{id}/report — Final verified intelligence report & recommendations
  GET  /api/v1/analysis/history     — Historical analysis runs
"""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.main import AppException
from app.models.analysis import AgentLog, Analysis
from app.models.dataset import Dataset
from app.models.recommendation import Recommendation
from app.models.report import Report
from app.models.user import User
from app.schemas.analysis import (
    AgentLogItem,
    AgentStatusItem,
    AnalysisHistoryItem,
    AnalysisLogsResponse,
    AnalysisReportResponse,
    AnalysisRunRequest,
    AnalysisRunResponse,
    AnalysisStatusResponse,
)
from app.services import analysis_runner, dataset_service
from app.utils.deps import get_current_active_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analysis", tags=["Analysis & Multi-Agent Execution"])


@router.post(
    "/run",
    response_model=AnalysisRunResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger Multi-Agent Analysis",
    description=(
        "Initiates the 6-agent CrewAI intelligence workflow in the background. "
        "Enforces a concurrency lock preventing multiple simultaneous runs on the same dataset. "
        "Returns the analysis_id immediately for asynchronous polling."
    ),
    responses={
        202: {"description": "Analysis launched in background"},
        404: {"description": "Dataset not found"},
        409: {"description": "Another analysis is already running on this dataset"},
    },
)
def run_analysis(
    payload: AnalysisRunRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> AnalysisRunResponse:
    """Trigger background analysis with concurrency protection."""
    # 1. Validate dataset existence and user access
    dataset = dataset_service.get_dataset_by_id(db=db, dataset_id=payload.dataset_id, user=current_user)

    if dataset.status != "ready":
        raise AppException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Dataset is not ready for analysis (current status: '{dataset.status}').",
            code="DATASET_NOT_READY",
        )

    # 2. Concurrency Guard: Check if an analysis is already running on this dataset
    active_run = analysis_runner.check_active_analysis_for_dataset(db=db, dataset_id=payload.dataset_id)
    if active_run:
        raise AppException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"An analysis is already actively running for dataset '{dataset.original_filename}' "
                f"(Analysis ID: {active_run.id}, Status: {active_run.status}). "
                "Please wait for it to complete or check /analysis/{id}/status."
            ),
            code="ANALYSIS_ALREADY_IN_PROGRESS",
        )

    # 3. Create Analysis and pre-initialize the 6 agent log placeholders
    analysis = analysis_runner.initialize_analysis_run(
        db=db,
        dataset_id=payload.dataset_id,
        user_id=current_user.id,
        user_question=payload.user_question,
    )

    # 4. Dispatch background task
    background_tasks.add_task(
        analysis_runner.run_analysis_background,
        analysis_id=analysis.id,
        user_question=payload.user_question,
        max_retries=2,
    )

    return AnalysisRunResponse(
        success=True,
        analysis_id=analysis.id,
        dataset_id=payload.dataset_id,
        status="running",
        message="Multi-agent intelligence analysis successfully queued and running in the background.",
    )


@router.get(
    "/{analysis_id}/status",
    response_model=AnalysisStatusResponse,
    summary="Get Analysis Execution Status",
    description="Returns high-level status, current active agent, calculated progress %, and per-agent status list.",
    responses={
        200: {"description": "Current analysis status"},
        404: {"description": "Analysis not found"},
    },
)
def get_analysis_status(
    analysis_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> AnalysisStatusResponse:
    """Poll live execution progress."""
    analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
    if not analysis:
        raise AppException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis '{analysis_id}' not found.",
            code="ANALYSIS_NOT_FOUND",
        )

    logs = (
        db.query(AgentLog)
        .filter(AgentLog.analysis_id == analysis_id)
        .order_by(AgentLog.sequence_order)
        .all()
    )

    completed_count = sum(1 for l in logs if l.status == "completed")
    total_agents = len(logs) if logs else 6
    progress_pct = int((completed_count / total_agents) * 100) if total_agents > 0 else 0

    current_agent = None
    for l in logs:
        if l.status == "running":
            current_agent = l.agent_name
            break

    agent_status_items = [
        AgentStatusItem(
            agent_name=l.agent_name,
            sequence_order=l.sequence_order,
            status=l.status,
            started_at=l.started_at,
            completed_at=l.completed_at,
            duration_seconds=l.duration_seconds,
        )
        for l in logs
    ]

    return AnalysisStatusResponse(
        analysis_id=analysis.id,
        dataset_id=analysis.dataset_id,
        status=analysis.status,
        current_agent=current_agent,
        progress_pct=progress_pct,
        error_message=analysis.error_message,
        started_at=analysis.started_at,
        completed_at=analysis.completed_at,
        agents=agent_status_items,
    )


@router.get(
    "/{analysis_id}/logs",
    response_model=AnalysisLogsResponse,
    summary="Get Agent Execution Logs",
    description="Returns detailed execution traces and outputs generated by each agent.",
    responses={
        200: {"description": "List of agent logs"},
        404: {"description": "Analysis not found"},
    },
)
def get_analysis_logs(
    analysis_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> AnalysisLogsResponse:
    """Retrieve full agent trace logs."""
    analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
    if not analysis:
        raise AppException(status_code=404, detail="Analysis not found", code="ANALYSIS_NOT_FOUND")

    logs = (
        db.query(AgentLog)
        .filter(AgentLog.analysis_id == analysis_id)
        .order_by(AgentLog.sequence_order)
        .all()
    )
    return AnalysisLogsResponse(
        analysis_id=analysis.id,
        logs=[AgentLogItem.model_validate(l) for l in logs],
    )


@router.get(
    "/{analysis_id}/report",
    response_model=AnalysisReportResponse,
    summary="Get Final Verified Report",
    description="Retrieves the completed Strategy Report, verification audit findings, and prioritized recommendations.",
    responses={
        200: {"description": "Verified BI Report"},
        404: {"description": "Report not found or analysis still in progress"},
    },
)
def get_analysis_report(
    analysis_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> AnalysisReportResponse:
    """Fetch completed business intelligence report."""
    analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
    if not analysis:
        raise AppException(status_code=404, detail="Analysis not found", code="ANALYSIS_NOT_FOUND")

    if analysis.status in ["queued", "running"]:
        raise AppException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Analysis is currently '{analysis.status}'. Please poll /status until completed.",
            code="ANALYSIS_IN_PROGRESS",
        )

    report = db.query(Report).filter(Report.analysis_id == analysis_id).first()
    if not report:
        raise AppException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No report generated for this analysis (run may have failed).",
            code="REPORT_NOT_FOUND",
        )

    # Parse verification notes JSON if stored as string
    parsed_notes = report.verification_notes
    if isinstance(parsed_notes, str):
        try:
            parsed_notes = json.loads(parsed_notes)
        except Exception:
            pass

    # Fetch recommendations
    recs = db.query(Recommendation).filter(Recommendation.analysis_id == analysis_id).all()
    rec_items = [
        {
            "id": str(r.id),
            "category": r.category,
            "title": r.title,
            "description": r.description,
            "expected_impact": r.expected_impact,
            "priority": r.priority,
            "approval_required": r.approval_required,
            "approval_status": r.approval_status,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in recs
    ]

    return AnalysisReportResponse(
        report_id=report.id,
        analysis_id=analysis.id,
        dataset_id=analysis.dataset_id,
        title=report.title,
        executive_summary=report.executive_summary,
        content_json=report.content_json,
        verification_status=report.verification_status,
        verification_notes=parsed_notes,
        pdf_path=report.pdf_path,
        created_at=report.created_at,
        recommendations=rec_items,
    )


@router.get(
    "/history",
    response_model=list[AnalysisHistoryItem],
    summary="Get Historical Analysis Runs",
    description="Returns a chronological list of previous analysis runs for the user (or all runs if admin).",
)
def get_analysis_history(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> list[AnalysisHistoryItem]:
    """List historical analysis executions."""
    stmt = select(Analysis, Dataset.original_filename).join(Dataset, Analysis.dataset_id == Dataset.id)

    if current_user.role != "admin":
        stmt = stmt.where(Analysis.user_id == current_user.id)

    stmt = stmt.order_by(Analysis.started_at.desc()).offset(skip).limit(limit)
    rows = db.execute(stmt).all()

    history: list[AnalysisHistoryItem] = []
    for analysis, orig_filename in rows:
        duration = None
        if analysis.started_at and analysis.completed_at:
            duration = round((analysis.completed_at - analysis.started_at).total_seconds(), 1)

        rep = db.query(Report.id, Report.verification_status).filter(Report.analysis_id == analysis.id).first()
        history.append(
            AnalysisHistoryItem(
                id=analysis.id,
                dataset_id=analysis.dataset_id,
                original_filename=orig_filename or "Dataset",
                status=analysis.status,
                started_at=analysis.started_at,
                completed_at=analysis.completed_at,
                duration_seconds=duration,
                has_report=rep is not None,
                verification_status=rep.verification_status if rep else None,
            )
        )

    return history
