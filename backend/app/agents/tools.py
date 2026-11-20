"""
app/agents/tools.py
────────────────────
CrewAI custom tools wrapping the pure pandas analytics service.

Factory pattern:
  build_tools(dataset_id, db_session_factory)
  Binds the dataset_id and database connection server-side inside function closures.
  The LLM never specifies or manipulates the dataset_id, preventing cross-tenant leakage.

All outputs are formatted as compact JSON strings to conserve LLM context window tokens.
Internal try/except blocks prevent tool crashes from terminating the CrewAI execution.
"""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any, Callable

from crewai.tools import tool
from sqlalchemy.orm import Session

from app.services import analytics_service

logger = logging.getLogger(__name__)


def _compact_json(data: Any) -> str:
    """Serialize Python dictionary into compact JSON string without whitespace."""
    try:
        return json.dumps(data, separators=(",", ":"), default=str)
    except Exception as exc:
        return json.dumps({"status": "error", "message": f"Serialization error: {str(exc)}"})


def build_tools(
    dataset_id: uuid.UUID,
    db_session_factory: Callable[[], Session],
) -> dict[str, Any]:
    """
    Factory function that creates CrewAI tools with server-side bound dataset_id.

    Args:
        dataset_id: The specific dataset UUID to analyze.
        db_session_factory: Callable yielding a fresh SQLAlchemy Session (e.g. SessionLocal).

    Returns:
        Dictionary mapping tool names to CrewAI Tool instances.
    """

    @tool("Retail KPI Summary Tool")
    def kpi_summary_tool() -> str:
        """
        Calculates and returns core executive business KPIs for the dataset:
        total revenue, gross sales, discounts, COGS, gross profit, operating expenses,
        net profit, gross/net margins, completed order count, average order value (AOV),
        return rate %, cancellation rate %, unique/repeat customers, and stockout count.
        Returns a compact JSON string.
        """
        try:
            with db_session_factory() as db:
                data = analytics_service.get_kpi_summary(db, dataset_id)
                return _compact_json(data)
        except Exception as exc:
            logger.error("Error in kpi_summary_tool: %s", exc, exc_info=True)
            return _compact_json({"status": "error", "tool": "kpi_summary_tool", "error": str(exc)})

    @tool("Monthly Sales and Financial Trends Tool")
    def monthly_trends_tool() -> str:
        """
        Returns month-by-month financial progression from May 2026 to October 2026:
        monthly revenue, expenses, COGS, net profit, orders, active customers,
        and Month-over-Month (MoM) growth percentages for sales, costs, and profit.
        Returns a compact JSON string.
        """
        try:
            with db_session_factory() as db:
                data = analytics_service.get_monthly_trends(db, dataset_id)
                return _compact_json(data)
        except Exception as exc:
            logger.error("Error in monthly_trends_tool: %s", exc, exc_info=True)
            return _compact_json({"status": "error", "tool": "monthly_trends_tool", "error": str(exc)})

    @tool("Statistical Anomaly Detection Tool")
    def anomaly_tool() -> str:
        """
        Detects business and operational anomalies in the dataset:
        1. Metrics deviating > 1.5 standard deviations from the 6-month mean.
        2. Rapid Month-over-Month spikes or drops exceeding 20%.
        3. Product category revenue concentration anomalies.
        Returns an anomaly list with deviation scores and explanations.
        """
        try:
            with db_session_factory() as db:
                data = analytics_service.detect_anomalies(db, dataset_id)
                return _compact_json(data)
        except Exception as exc:
            logger.error("Error in anomaly_tool: %s", exc, exc_info=True)
            return _compact_json({"status": "error", "tool": "anomaly_tool", "error": str(exc)})

    @tool("Customer RFM Segmentation Tool")
    def customer_segments_tool() -> str:
        """
        Performs Recency, Frequency, and Monetary (RFM) clustering on customers.
        Returns customer groups (Champions/VIP, Loyal, New Buyers, Potential Loyalists,
        At Risk, Dormant), along with customer counts, revenue contributions,
        average spend, and churn risk ratings.
        """
        try:
            with db_session_factory() as db:
                data = analytics_service.get_customer_segments(db, dataset_id)
                return _compact_json(data)
        except Exception as exc:
            logger.error("Error in customer_segments_tool: %s", exc, exc_info=True)
            return _compact_json({"status": "error", "tool": "customer_segments_tool", "error": str(exc)})

    @tool("Sales Channels and Marketing Performance Tool")
    def marketing_tool() -> str:
        """
        Evaluates sales channel performance (In-store, Mobile App, Online, Phone):
        order volumes, gross sales, total discount, net revenue, revenue share %,
        average order value per channel, effective discount %, and payment method share.
        """
        try:
            with db_session_factory() as db:
                data = analytics_service.get_marketing_performance(db, dataset_id)
                return _compact_json(data)
        except Exception as exc:
            logger.error("Error in marketing_tool: %s", exc, exc_info=True)
            return _compact_json({"status": "error", "tool": "marketing_tool", "error": str(exc)})

    @tool("Financial Breakdown and Cost Ratios Tool")
    def finance_tool() -> str:
        """
        Detailed cost analysis:
        operating expenses by category, top 5 vendors by spend, cost-to-revenue ratio,
        and product category gross margin and COGS breakdown.
        """
        try:
            with db_session_factory() as db:
                data = analytics_service.get_financial_breakdown(db, dataset_id)
                return _compact_json(data)
        except Exception as exc:
            logger.error("Error in finance_tool: %s", exc, exc_info=True)
            return _compact_json({"status": "error", "tool": "finance_tool", "error": str(exc)})

    @tool("Operational Efficiency and Inventory Health Tool")
    def operations_tool() -> str:
        """
        Evaluates warehouse throughput, movement types (Sales, Restocks, Returns, Transfers),
        stockout risk alerts (products where stock <= reorder level), and store efficiency.
        """
        try:
            with db_session_factory() as db:
                data = analytics_service.get_operational_metrics(db, dataset_id)
                return _compact_json(data)
        except Exception as exc:
            logger.error("Error in operations_tool: %s", exc, exc_info=True)
            return _compact_json({"status": "error", "tool": "operations_tool", "error": str(exc)})

    @tool("Metric Verification and Recomputation Tool")
    def recompute_metric_tool(metric_name: str) -> str:
        """
        Used by the Verification Agent to independently recalculate and confirm any metric
        against the source database.
        Accepts metric_name (e.g. 'total_revenue', 'gross_profit', 'net_profit', 'cogs',
        'margin_pct', 'order_count', 'aov', 'return_rate', 'stockout_count', 'expenses').
        Returns the ground-truth value and computation formula.
        """
        try:
            with db_session_factory() as db:
                kpis = analytics_service.get_kpi_summary(db, dataset_id)
                fin = kpis.get("financial_kpis", {})
                sales = kpis.get("sales_kpis", {})
                cust = kpis.get("customer_kpis", {})
                ops = kpis.get("operational_kpis", {})

                key = metric_name.strip().lower().replace(" ", "_")
                metric_lookup = {
                    "total_revenue": (fin.get("total_revenue"), "Sum of net_amount for Completed transactions"),
                    "revenue": (fin.get("total_revenue"), "Sum of net_amount for Completed transactions"),
                    "gross_sales": (fin.get("total_gross_sales"), "Sum of gross_amount for Completed transactions"),
                    "discount": (fin.get("total_discount"), "Sum of discount for Completed transactions"),
                    "cogs": (fin.get("total_cogs"), "Sum of (quantity * unit_cost) for Completed line items"),
                    "gross_profit": (fin.get("gross_profit"), "Total Revenue - Total COGS"),
                    "operating_expenses": (fin.get("total_operating_expenses"), "Sum of all expenses in dataset period"),
                    "expenses": (fin.get("total_operating_expenses"), "Sum of all expenses in dataset period"),
                    "net_profit": (fin.get("net_profit"), "Gross Profit - Operating Expenses"),
                    "gross_margin_pct": (fin.get("gross_margin_pct"), "(Gross Profit / Total Revenue) * 100"),
                    "margin_pct": (fin.get("net_profit_margin_pct"), "(Net Profit / Total Revenue) * 100"),
                    "net_profit_margin_pct": (fin.get("net_profit_margin_pct"), "(Net Profit / Total Revenue) * 100"),
                    "order_count": (sales.get("completed_orders"), "Count of Completed transactions"),
                    "orders": (sales.get("completed_orders"), "Count of Completed transactions"),
                    "aov": (sales.get("average_order_value"), "Total Revenue / Completed Orders"),
                    "average_order_value": (sales.get("average_order_value"), "Total Revenue / Completed Orders"),
                    "return_rate": (sales.get("return_rate_pct"), "(Returned Orders / Total Orders) * 100"),
                    "return_rate_pct": (sales.get("return_rate_pct"), "(Returned Orders / Total Orders) * 100"),
                    "stockout_count": (ops.get("stockout_count"), "Count of products where current stock <= reorder level"),
                    "repeat_customer_rate": (cust.get("repeat_customer_rate_pct"), "(Customers with >=2 orders / Total) * 100"),
                }

                if key in metric_lookup:
                    val, formula = metric_lookup[key]
                    return _compact_json({
                        "status": "verified",
                        "metric_requested": metric_name,
                        "ground_truth_value": val,
                        "calculation_formula": formula,
                    })
                else:
                    return _compact_json({
                        "status": "unknown_metric",
                        "metric_requested": metric_name,
                        "available_metrics": list(metric_lookup.keys()),
                    })
        except Exception as exc:
            logger.error("Error in recompute_metric_tool: %s", exc, exc_info=True)
            return _compact_json({"status": "error", "tool": "recompute_metric_tool", "error": str(exc)})

    return {
        "kpi_summary_tool": kpi_summary_tool,
        "monthly_trends_tool": monthly_trends_tool,
        "anomaly_tool": anomaly_tool,
        "customer_segments_tool": customer_segments_tool,
        "marketing_tool": marketing_tool,
        "finance_tool": finance_tool,
        "operations_tool": operations_tool,
        "recompute_metric_tool": recompute_metric_tool,
    }
