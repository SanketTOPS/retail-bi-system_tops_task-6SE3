"""
app/agents/tasks.py
────────────────────
Task definitions and Pydantic output schemas for the 6 CrewAI retail agents.

Enforces:
  - Context passing (T2, T3, T4 take T1; T5 takes T1..T4; T6 takes T1..T5)
  - Pydantic structured output for Strategy (StrategyReport)
  - Pydantic structured output for Verification (VerificationResult)
"""

from __future__ import annotations

from typing import Any, Literal
from pydantic import BaseModel, Field
from crewai import Agent, Task


# ─────────────────────────────────────────────────────────────────────────────
# Pydantic Schemas for Structured Agent Outputs
# ─────────────────────────────────────────────────────────────────────────────
class RecommendationItem(BaseModel):
    title: str = Field(..., description="Actionable headline recommendation")
    description: str = Field(..., description="Detailed operational steps to execute")
    expected_impact: str = Field(..., description="Quantified business benefit (e.g. 'Boost gross margin by 3.2%')")
    priority: int = Field(..., ge=1, le=4, description="1=Critical, 2=High, 3=Medium, 4=Low")
    requires_approval: bool = Field(
        ...,
        description="True for consequential decisions (budget increases >10%, bulk purchase orders, price adjustments)",
    )


class ActionPlanStep(BaseModel):
    step: str = Field(..., description="Specific operational task to perform")
    owner: str = Field(..., description="Responsible role (e.g. Marketing Lead, Inventory Manager, Store Director)")
    timeline: str = Field(..., description="Target completion window (e.g. 'Days 1-14', 'Month 1')")


class FactualClaim(BaseModel):
    statement: str = Field(..., description="The factual statement made in the report")
    metric_name: str = Field(..., description="The canonical metric name (e.g. 'total_revenue', 'gross_margin_pct', 'stockout_count')")
    claimed_value: float = Field(..., description="The exact numerical value stated in the report")


class StrategyReport(BaseModel):
    """Structured report produced by the Strategy Agent."""
    executive_summary: str = Field(..., description="Comprehensive C-level narrative summary of retail health")
    performance_insights: list[str] = Field(..., description="Top quantitative performance insights")
    revenue_expense_analysis: str = Field(..., description="In-depth breakdown of top-line sales, COGS, and overheads")
    customer_analysis: str = Field(..., description="Summary of customer segments, retention rate, and churn risks")
    operational_problems: list[str] = Field(..., description="Key bottlenecks in inventory, stockouts, or store efficiency")
    risks: list[str] = Field(..., description="Financial, operational, or customer retention risks identified")
    growth_opportunities: list[str] = Field(..., description="Actionable revenue expansion and cost reduction vectors")
    recommendations: list[RecommendationItem] = Field(..., description="Prioritized recommendations with human-in-the-loop flags")
    action_plan: list[ActionPlanStep] = Field(..., description="Sequenced operational execution roadmap")
    claims: list[FactualClaim] = Field(
        ...,
        description="Every numerical claim stated in the report that requires verification against source data",
    )


class VerifiedClaimCheck(BaseModel):
    statement: str
    metric_name: str
    claimed_value: float
    ground_truth_value: float
    is_accurate: bool
    discrepancy: float | None = None


class VerificationResult(BaseModel):
    """Audit report produced by the Verification Agent."""
    verified_claims: list[VerifiedClaimCheck] = Field(default_factory=list, description="Claims checked and validated")
    mismatches: list[dict[str, Any]] = Field(default_factory=list, description="Claims where claimed != ground truth")
    unsupported_statements: list[str] = Field(default_factory=list, description="Statements lacking cited data sources")
    contradictions: list[str] = Field(default_factory=list, description="Inconsistencies across prior agent findings")
    low_confidence_items: list[str] = Field(default_factory=list, description="Findings with insufficient evidence")
    decision: Literal["APPROVED", "REJECTED"] = Field(
        ...,
        description="APPROVED if all critical numerical claims are verified accurately; REJECTED if significant errors exist",
    )
    feedback: str = Field(..., description="Detailed rationale for the verification decision")


# ─────────────────────────────────────────────────────────────────────────────
# Task Factory
# ─────────────────────────────────────────────────────────────────────────────
def create_retail_tasks(
    agents: dict[str, Agent],
    user_question: str | None = None,
    feedback: str | None = None,
) -> list[Task]:
    """
    Creates the 6 sequential tasks with explicit context dependencies.

    T1: Data Analyst Task
    T2: Marketing Task (context=[T1])
    T3: Finance Task (context=[T1])
    T4: Operations Task (context=[T1])
    T5: Strategy Task (context=[T1, T2, T3, T4]) -> outputs StrategyReport
    T6: Verification Task (context=[T1, T2, T3, T4, T5]) -> outputs VerificationResult
    """
    data_analyst = agents["data_analyst"]
    marketing = agents["marketing"]
    finance = agents["finance"]
    operations = agents["operations"]
    strategy = agents["strategy"]
    verification = agents["verification"]

    extra_instructions = ""
    if user_question:
        extra_instructions += f"\nSpecific User Inquiry to Address: {user_question}"
    if feedback:
        extra_instructions += f"\nPrevious Human Feedback to Incorporate: {feedback}"

    # ── Task 1: Data Analyst ─────────────────────────────────────────────────
    task1 = Task(
        description=(
            "Execute a comprehensive retail analytical baseline using your tools.\n"
            "1. Call `kpi_summary_tool` to obtain total revenue, gross sales, discounts, COGS, "
            "gross profit, operating expenses, net profit, margins %, order counts, AOV, "
            "return rate %, cancellation rate %, and unique/repeat customer statistics.\n"
            "2. Call `monthly_trends_tool` to analyze month-by-month performance across May–October 2026, "
            "highlighting sales velocity and Month-over-Month (MoM) growth rates.\n"
            "3. Call `anomaly_tool` to identify statistical anomalies (>1.5 std dev) and rapid swings (>20%).\n"
            "Summarize all findings factually. Cite the exact tool output for EVERY number."
            f"{extra_instructions}"
        ),
        expected_output=(
            "A structured analytical report detailing executive KPIs, monthly trend metrics, "
            "and identified statistical anomalies with exact tool-verified numbers."
        ),
        agent=data_analyst,
    )

    # ── Task 2: Marketing ────────────────────────────────────────────────────
    task2 = Task(
        description=(
            "Analyze retail customer behavior and sales channel effectiveness.\n"
            "Review the Data Analyst's baseline findings from context.\n"
            "1. Call `customer_segments_tool` to assess RFM segments (Champions, Loyalists, At Risk, Dormant), "
            "their revenue share %, average spend, and churn risks.\n"
            "2. Call `marketing_tool` to evaluate channel performance (In-store, Mobile App, Online, Phone), "
            "discounting rates, revenue contributions, and payment method trends.\n"
            "3. Identify customer retention strategies and growth channels. Use ONLY tool-provided numbers."
        ),
        expected_output=(
            "A marketing intelligence report detailing customer RFM segments, channel performance, "
            "discounting impact, and targeted customer retention strategies."
        ),
        agent=marketing,
        context=[task1],
    )

    # ── Task 3: Finance ──────────────────────────────────────────────────────
    task3 = Task(
        description=(
            "Evaluate financial profitability, cost structures, and margins.\n"
            "Review the Data Analyst's KPI and trend findings from context.\n"
            "1. Call `finance_tool` to analyze operating expenses by category (salaries, utilities, packaging, marketing), "
            "top vendor concentrations, cost-to-revenue ratio, and product category gross margin contributions.\n"
            "2. Cross-reference monthly COGS and expense trends to detect margin compression periods.\n"
            "3. Formulate actionable cost optimization strategies without compromising customer experience."
        ),
        expected_output=(
            "A financial assessment report breaking down operating expenses, category margins, "
            "cost-to-revenue ratios, and cost reduction recommendations."
        ),
        agent=finance,
        context=[task1],
    )

    # ── Task 4: Operations ───────────────────────────────────────────────────
    task4 = Task(
        description=(
            "Audit inventory health, logistics, and store operational efficiency.\n"
            "Review the Data Analyst's anomaly and order volume findings from context.\n"
            "1. Call `operations_tool` to examine warehouse movement volumes, distribution by movement type "
            "(Sales, Restocks, Returns, Transfers), and store-level revenue vs. expense ratios.\n"
            "2. Inspect the stockout risk alerts (products where stock <= reorder level) and quantify inventory at risk.\n"
            "3. Recommend operational improvements for inventory reordering, warehouse logistics, and store cost efficiency."
        ),
        expected_output=(
            "An operational intelligence report detailing warehouse throughput, stockout risk alerts, "
            "store efficiency comparisons, and supply chain improvements."
        ),
        agent=operations,
        context=[task1],
    )

    # ── Task 5: Strategy (Produces StrategyReport Pydantic) ───────────────────
    task5 = Task(
        description=(
            "Synthesize findings from the Data Analyst, Marketing, Finance, and Operations agents.\n"
            "Develop a unified, C-suite Decision Intelligence Strategy Report for executive management.\n"
            "1. Combine insights into a cohesive executive summary and performance narrative.\n"
            "2. Detail revenue/expense dynamics, customer behavior, and operational bottlenecks.\n"
            "3. Define prioritized, actionable recommendations. Flag ANY consequential action "
            "(e.g. marketing budget increase >10%, major stock liquidation, bulk purchase orders, price adjustments) "
            "with requires_approval = True for human-in-the-loop review.\n"
            "4. Construct a phased operational action plan with owners and timelines.\n"
            "5. CRITICAL: Compile a comprehensive list of all numerical claims made in the report "
            "(statement, canonical metric_name, and claimed_value) so the Verification Agent can audit them.\n"
            "Ensure strict adherence to the StrategyReport schema."
        ),
        expected_output=(
            "A comprehensive StrategyReport Pydantic object containing executive summary, insights, "
            "prioritized recommendations with human-in-the-loop flags, action plan, and verifiable claims."
        ),
        agent=strategy,
        context=[task1, task2, task3, task4],
        output_pydantic=StrategyReport,
    )

    # ── Task 6: Verification (Produces VerificationResult Pydantic) ───────────
    task6 = Task(
        description=(
            "Perform an independent, rigorous audit of the Strategy Agent's report.\n"
            "Review all previous agent outputs (Tasks 1 through 5).\n"
            "1. Extract every claim from the Strategy Report's claims list.\n"
            "2. For each claim, call `recompute_metric_tool(metric_name=...)` to retrieve the database ground truth.\n"
            "3. Compare the claimed value against the ground truth value. Flag any mismatch > 1%.\n"
            "4. Detect any unsupported statements or logical contradictions between agents.\n"
            "5. If all critical numerical claims are verified, set decision = 'APPROVED'. "
            "If significant discrepancies or hallucinations exist, set decision = 'REJECTED'.\n"
            "Provide detailed audit feedback in the VerificationResult schema."
        ),
        expected_output=(
            "A VerificationResult Pydantic object detailing checked claims, ground-truth comparisons, "
            "discrepancies, decision (APPROVED or REJECTED), and audit feedback."
        ),
        agent=verification,
        context=[task1, task2, task3, task4, task5],
        output_pydantic=VerificationResult,
    )

    return [task1, task2, task3, task4, task5, task6]
