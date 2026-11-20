"""
app/agents/verifier.py
───────────────────────
Python-level deterministic verification and anti-hallucination scanner.

Provides:
  1. verify_claims_numerically: Recomputes claimed values against PostgreSQL ground truth with 1% tolerance.
  2. scan_unsupported_statements: Regex-based scanner identifying rogue/hallucinated numbers in report text.
  3. calculate_confidence_score: Multi-factor scoring (0-100) and confidence tiering.
"""

from __future__ import annotations

import logging
import re
import uuid
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.services import analytics_service

logger = logging.getLogger(__name__)

# Standard benchmark tolerance (1% relative margin or 0.05 absolute for small values)
DEFAULT_TOLERANCE_PCT = 1.0


def _normalize_metric_key(name: str) -> str:
    """Standardize metric name into snake_case lookup key."""
    return name.strip().lower().replace(" ", "_").replace("-", "_")


def get_ground_truth_lookup(db: Session, dataset_id: uuid.UUID) -> dict[str, float]:
    """
    Fetches all ground truth metrics from analytics_service for direct numerical auditing.
    """
    kpis = analytics_service.get_kpi_summary(db, dataset_id)
    fin = kpis.get("financial_kpis", {})
    sales = kpis.get("sales_kpis", {})
    cust = kpis.get("customer_kpis", {})
    ops = kpis.get("operational_kpis", {})

    trends = analytics_service.get_monthly_trends(db, dataset_id).get("months", [])
    finance_breakdown = analytics_service.get_financial_breakdown(db, dataset_id)

    lookup: dict[str, float] = {
        "total_revenue": float(fin.get("total_revenue", 0.0)),
        "revenue": float(fin.get("total_revenue", 0.0)),
        "net_revenue": float(fin.get("total_revenue", 0.0)),
        "gross_sales": float(fin.get("total_gross_sales", 0.0)),
        "total_gross_sales": float(fin.get("total_gross_sales", 0.0)),
        "total_discount": float(fin.get("total_discount", 0.0)),
        "discount": float(fin.get("total_discount", 0.0)),
        "total_cogs": float(fin.get("total_cogs", 0.0)),
        "cogs": float(fin.get("total_cogs", 0.0)),
        "gross_profit": float(fin.get("gross_profit", 0.0)),
        "total_operating_expenses": float(fin.get("total_operating_expenses", 0.0)),
        "operating_expenses": float(fin.get("total_operating_expenses", 0.0)),
        "expenses": float(fin.get("total_operating_expenses", 0.0)),
        "net_profit": float(fin.get("net_profit", 0.0)),
        "gross_margin_pct": float(fin.get("gross_margin_pct", 0.0)),
        "gross_margin": float(fin.get("gross_margin_pct", 0.0)),
        "net_profit_margin_pct": float(fin.get("net_profit_margin_pct", 0.0)),
        "net_margin_pct": float(fin.get("net_profit_margin_pct", 0.0)),
        "profit_margin_pct": float(fin.get("net_profit_margin_pct", 0.0)),
        "margin_pct": float(fin.get("net_profit_margin_pct", 0.0)),
        "order_count": float(sales.get("completed_orders", 0)),
        "completed_orders": float(sales.get("completed_orders", 0)),
        "orders": float(sales.get("completed_orders", 0)),
        "total_transactions": float(sales.get("total_transactions", 0)),
        "average_order_value": float(sales.get("average_order_value", 0.0)),
        "aov": float(sales.get("average_order_value", 0.0)),
        "return_rate_pct": float(sales.get("return_rate_pct", 0.0)),
        "return_rate": float(sales.get("return_rate_pct", 0.0)),
        "cancellation_rate_pct": float(sales.get("cancellation_rate_pct", 0.0)),
        "unique_customers": float(cust.get("unique_customers", 0)),
        "repeat_customers": float(cust.get("repeat_customers", 0)),
        "repeat_customer_rate_pct": float(cust.get("repeat_customer_rate_pct", 0.0)),
        "stockout_count": float(ops.get("stockout_count", 0)),
        "inventory_turnover_ratio": float(ops.get("inventory_turnover_ratio", 0.0)),
        "inventory_turnover": float(ops.get("inventory_turnover_ratio", 0.0)),
        "cost_to_revenue_ratio": float(finance_breakdown.get("cost_to_revenue_ratio", 0.0)),
    }

    # Add monthly revenue and profits to lookup
    for m in trends:
        ym = m.get("year_month", "").replace("-", "_")
        if ym:
            lookup[f"revenue_{ym}"] = float(m.get("revenue", 0.0))
            lookup[f"net_profit_{ym}"] = float(m.get("net_profit", 0.0))
            lookup[f"expenses_{ym}"] = float(m.get("expenses", 0.0))

    return lookup


def verify_claims_numerically(
    claims: list[dict[str, Any]],
    dataset_id: uuid.UUID,
    db: Session,
    tolerance_pct: float = DEFAULT_TOLERANCE_PCT,
) -> dict[str, Any]:
    """
    Independently audits each claim against database ground truth.

    Args:
        claims: List of dicts with keys: statement, metric_name, claimed_value.
        dataset_id: Target dataset ID.
        db: Active SQLAlchemy session.
        tolerance_pct: Acceptable percentage deviation (default 1.0%).

    Returns:
        Structured audit report including matched and mismatched claims.
    """
    ground_truth = get_ground_truth_lookup(db, dataset_id)
    checks: list[dict[str, Any]] = []
    matched_count = 0
    mismatched_count = 0

    for claim in claims:
        statement = claim.get("statement", "")
        metric_name = str(claim.get("metric_name", "")).strip()
        claimed_val = float(claim.get("claimed_value", 0.0))
        norm_key = _normalize_metric_key(metric_name)

        actual_val = ground_truth.get(norm_key)

        if actual_val is None:
            # Fallback search if exact key is slightly different
            for k, v in ground_truth.items():
                if norm_key in k or k in norm_key:
                    actual_val = v
                    break

        if actual_val is None:
            # Metric not found in standard ground truth
            mismatched_count += 1
            checks.append({
                "statement": statement,
                "metric_name": metric_name,
                "claimed_value": claimed_val,
                "actual_value": None,
                "diff_pct": None,
                "match": False,
                "status": "UNRECOGNIZED_METRIC",
                "reason": f"Metric '{metric_name}' could not be resolved in database ground truth.",
            })
            continue

        diff_abs = abs(claimed_val - actual_val)
        if actual_val != 0:
            diff_pct = round((diff_abs / abs(actual_val)) * 100, 2)
        else:
            diff_pct = 0.0 if diff_abs == 0 else 100.0

        is_match = (diff_pct <= tolerance_pct) or (diff_abs <= 0.05)

        if is_match:
            matched_count += 1
            status = "MATCH"
        else:
            mismatched_count += 1
            status = "MISMATCH"

        checks.append({
            "statement": statement,
            "metric_name": metric_name,
            "claimed_value": round(claimed_val, 2),
            "actual_value": round(actual_val, 2),
            "diff_abs": round(diff_abs, 2),
            "diff_pct": diff_pct,
            "match": is_match,
            "status": status,
        })

    total = len(claims)
    accuracy_pct = round((matched_count / total) * 100, 2) if total > 0 else 100.0

    return {
        "total_claims": total,
        "matched_count": matched_count,
        "mismatched_count": mismatched_count,
        "accuracy_pct": accuracy_pct,
        "tolerance_pct": tolerance_pct,
        "checks": checks,
    }


def scan_unsupported_statements(
    report_dict: dict[str, Any],
    known_numbers: set[float],
) -> dict[str, Any]:
    """
    Scans report text for ungrounded numbers that do not match any known tool/ground-truth figure.
    """
    # Extract all prose sections
    text_blocks: list[str] = []
    for key in ["executive_summary", "revenue_expense_analysis", "customer_analysis"]:
        if isinstance(report_dict.get(key), str):
            text_blocks.append(report_dict[key])

    for list_key in ["performance_insights", "operational_problems", "risks", "growth_opportunities"]:
        items = report_dict.get(list_key, [])
        if isinstance(items, list):
            for item in items:
                if isinstance(item, str):
                    text_blocks.append(item)

    full_text = "\n".join(text_blocks)

    # Regex finding numbers with optional commas, decimals, or percentage symbols
    # Excludes years (2026) and small common enumerations (1, 2, 3, 4, 5, 6, 7, 10, 14, 30, 31)
    ignored_numbers = {2026.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 10.0, 14.0, 30.0, 31.0, 100.0, 0.0}
    number_pattern = re.compile(r"(?:₹|\$|INR)?\s*(\d{1,3}(?:,\d{3})*(?:\.\d+)?|\d+(?:\.\d+)?)\s*(%|INR|Cr|Lakh)?")

    unsupported_items: list[dict[str, Any]] = []
    seen_numbers: set[float] = set()

    sentences = re.split(r"(?<=[.!?])\s+", full_text)

    for sentence in sentences:
        matches = number_pattern.findall(sentence)
        for num_str, suffix in matches:
            clean_str = num_str.replace(",", "").strip()
            try:
                val = float(clean_str)
            except ValueError:
                continue

            if val in ignored_numbers or val in seen_numbers:
                continue

            seen_numbers.add(val)

            # Check if this number is close to any known ground truth or claimed number
            matched_any = False
            for kn in known_numbers:
                if kn == 0:
                    continue
                diff_pct = abs(val - kn) / abs(kn) * 100
                if diff_pct <= 2.0 or abs(val - kn) <= 0.1:
                    matched_any = True
                    break

            if not matched_any:
                unsupported_items.append({
                    "unsupported_value": val,
                    "sentence_snippet": sentence.strip()[:160],
                    "flag": "Number not traceable to analytical tool outputs or verified claims",
                })

    return {
        "unsupported_count": len(unsupported_items),
        "unsupported_findings": unsupported_items,
    }


def calculate_confidence_score(
    numerical_check: dict[str, Any],
    unsupported_check: dict[str, Any],
    verification_agent_result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Computes an objective, multi-factor confidence score (0-100) and assigns an audit status.
    """
    mismatches = numerical_check.get("mismatched_count", 0)
    unsupported = unsupported_check.get("unsupported_count", 0)
    agent_decision = verification_agent_result.get("decision", "APPROVED") if verification_agent_result else "APPROVED"

    # Score calculation starting at 100
    score = 100.0
    deductions: list[str] = []

    if mismatches > 0:
        penalty = min(mismatches * 25.0, 60.0)
        score -= penalty
        deductions.append(f"-{penalty:.1f} pts: {mismatches} numerical claim mismatch(es)")

    if unsupported > 0:
        penalty = min(unsupported * 5.0, 25.0)
        score -= penalty
        deductions.append(f"-{penalty:.1f} pts: {unsupported} unsupported number(s) detected in text")

    if agent_decision == "REJECTED":
        score -= 20.0
        deductions.append("-20.0 pts: Verification Agent issued REJECTED audit decision")

    score = max(0.0, min(100.0, round(score, 1)))

    if score >= 90.0 and mismatches == 0 and agent_decision == "APPROVED":
        status = "VERIFIED"
        rating = "HIGH"
    elif score >= 70.0 and mismatches == 0:
        status = "VERIFIED_WITH_WARNINGS"
        rating = "MEDIUM"
    else:
        status = "REJECTED"
        rating = "LOW"

    return {
        "confidence_score": score,
        "rating": rating,
        "status": status,
        "deductions": deductions,
        "passed": status in ["VERIFIED", "VERIFIED_WITH_WARNINGS"],
    }
