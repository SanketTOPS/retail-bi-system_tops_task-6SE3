"""
app/routers/analytics.py
─────────────────────────
Router exposing pure pandas analytical endpoints for the frontend dashboard and CrewAI tools.

Endpoints:
  GET /api/v1/analytics/{dataset_id}/kpis
  GET /api/v1/analytics/{dataset_id}/trends
  GET /api/v1/analytics/{dataset_id}/anomalies
  GET /api/v1/analytics/{dataset_id}/segments
  GET /api/v1/analytics/{dataset_id}/marketing
  GET /api/v1/analytics/{dataset_id}/finance
  GET /api/v1/analytics/{dataset_id}/operations
  GET /api/v1/analytics/{dataset_id}/dashboard-summary
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User
from app.services import analytics_service, dataset_service
from app.utils.deps import get_current_active_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analytics", tags=["Analytics"])


def _verify_dataset_access(db: Session, dataset_id: uuid.UUID, user: User):
    """Ensure dataset exists and the user is authorized to read it."""
    return dataset_service.get_dataset_by_id(db=db, dataset_id=dataset_id, user=user)


@router.get(
    "/{dataset_id}/kpis",
    summary="Get Executive KPI Summary",
    description="Returns high-level business KPIs including revenue, COGS, expenses, net profit, margin %, order counts, AOV, return rate, and stockout count.",
)
def get_kpis(
    dataset_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Calculate executive business metrics."""
    _verify_dataset_access(db, dataset_id, current_user)
    return analytics_service.get_kpi_summary(db, dataset_id)


@router.get(
    "/{dataset_id}/trends",
    summary="Get Monthly Trends & MoM Growth",
    description="Returns month-wise progression of sales, expenses, COGS, profits, and Month-over-Month (MoM) growth percentages.",
)
def get_trends(
    dataset_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Retrieve monthly trend metrics."""
    _verify_dataset_access(db, dataset_id, current_user)
    return analytics_service.get_monthly_trends(db, dataset_id)


@router.get(
    "/{dataset_id}/anomalies",
    summary="Detect Business & Statistical Anomalies",
    description="Identifies months, categories, or metrics deviating > 1.5 standard deviations or with > 20% rapid MoM shifts.",
)
def get_anomalies(
    dataset_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Compute statistical anomalies."""
    _verify_dataset_access(db, dataset_id, current_user)
    return analytics_service.detect_anomalies(db, dataset_id)


@router.get(
    "/{dataset_id}/segments",
    summary="Customer RFM Segmentation",
    description="Performs Recency, Frequency, Monetary (RFM) clustering to classify customers into behavioral tiers and identify churn risks.",
)
def get_segments(
    dataset_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Compute customer segments."""
    _verify_dataset_access(db, dataset_id, current_user)
    return analytics_service.get_customer_segments(db, dataset_id)


@router.get(
    "/{dataset_id}/marketing",
    summary="Marketing & Sales Channel Performance",
    description="Analyzes revenue contribution, discounting rates, and order counts across sales channels and payment methods.",
)
def get_marketing(
    dataset_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Analyze sales channel productivity."""
    _verify_dataset_access(db, dataset_id, current_user)
    return analytics_service.get_marketing_performance(db, dataset_id)


@router.get(
    "/{dataset_id}/finance",
    summary="Financial & Expense Breakdown",
    description="Provides expense breakdown by category, vendor distribution, category gross margins, and cost-to-revenue ratio.",
)
def get_finance(
    dataset_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Analyze cost breakdown and profitability."""
    _verify_dataset_access(db, dataset_id, current_user)
    return analytics_service.get_financial_breakdown(db, dataset_id)


@router.get(
    "/{dataset_id}/operations",
    summary="Operational & Inventory Health",
    description="Calculates warehouse throughput, movement type distribution, stockout risk alerts, and store-level operating efficiency.",
)
def get_operations(
    dataset_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Analyze operational bottlenecks and inventory health."""
    _verify_dataset_access(db, dataset_id, current_user)
    return analytics_service.get_operational_metrics(db, dataset_id)


@router.get(
    "/{dataset_id}/dashboard-summary",
    summary="Consolidated Dashboard Overview",
    description="Aggregates KPIs, monthly trends, top anomalies, and channel breakdown into a single call for high-performance dashboard loading.",
)
def get_dashboard_summary(
    dataset_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Single-roundtrip endpoint powering the React dashboard overview."""
    _verify_dataset_access(db, dataset_id, current_user)
    kpis = analytics_service.get_kpi_summary(db, dataset_id)
    trends = analytics_service.get_monthly_trends(db, dataset_id)
    anomalies = analytics_service.detect_anomalies(db, dataset_id)
    marketing = analytics_service.get_marketing_performance(db, dataset_id)
    finance = analytics_service.get_financial_breakdown(db, dataset_id)

    return {
        "kpis": kpis,
        "monthly_trends": trends.get("months", []),
        "recent_anomalies": anomalies.get("anomalies", [])[:5],
        "channel_performance": marketing.get("channels", []),
        "expense_breakdown": finance.get("expenses_by_category", []),
    }
