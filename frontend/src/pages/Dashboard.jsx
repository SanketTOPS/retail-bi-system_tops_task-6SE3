/**
 * src/pages/Dashboard.jsx
 * ────────────────────────
 * Retail Business Intelligence Analytics Dashboard (Module 13.3).
 *
 * Consumes pure Pandas analytics endpoints (NO LLM hallucinations):
 *  - GET /analytics/{dataset_id}/kpis
 *  - GET /analytics/{dataset_id}/trends
 *  - GET /analytics/{dataset_id}/anomalies
 *  - GET /analytics/{dataset_id}/segments
 *  - GET /analytics/{dataset_id}/finance
 *  - GET /analytics/{dataset_id}/operations
 *  - GET /analytics/{dataset_id}/marketing
 *
 * Features:
 *  - Dataset Selector Dropdown (auto-selects first available dataset)
 *  - 12 Executive & Retail-specific KPI Cards with trend indicators
 *  - Monthly Revenue vs Expense vs COGS Composed Chart (Bar + Line)
 *  - Profit Progression & Margin Trends
 *  - Expense Breakdown Pie Chart & Category Gross Margin Bar Chart
 *  - Customer RFM Behavioral Segmentation (Donut + Revenue Share)
 *  - Retail Inventory Movements & Channel Performance Breakdown
 *  - Statistical & Business Anomaly Feed with severity badges
 *  - Full Skeleton Loading States (no layout jumps)
 *  - Empty state with direct upload link when no datasets exist
 */

import React, { useEffect, useState, useMemo } from 'react';
import { Link } from 'react-router-dom';
import toast from 'react-hot-toast';
import {
  ResponsiveContainer,
  ComposedChart,
  BarChart,
  Bar,
  LineChart,
  Line,
  AreaChart,
  Area,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from 'recharts';

import { listDatasetsApi } from '@/api/datasets';
import {
  getKpisApi,
  getTrendsApi,
  getAnomaliesApi,
  getSegmentsApi,
  getFinanceApi,
  getOperationsApi,
  getMarketingApi,
} from '@/api/analytics';

// ── Color Schemes ────────────────────────────────────────────────────────────
const CHART_COLORS = [
  '#2563eb', // Blue
  '#16a34a', // Green
  '#f59e0b', // Amber
  '#ef4444', // Red
  '#8b5cf6', // Violet
  '#06b6d4', // Cyan
  '#ec4899', // Pink
  '#64748b', // Slate
];

// ── Currency & Metric Formatters ─────────────────────────────────────────────
const formatCurrency = (val) => {
  if (val === null || val === undefined || isNaN(val)) return '$0';
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 0,
  }).format(val);
};

const formatPercent = (val) => {
  if (val === null || val === undefined || isNaN(val)) return '0.0%';
  return `${Number(val).toFixed(1)}%`;
};

const formatNumber = (val) => {
  if (val === null || val === undefined || isNaN(val)) return '0';
  return Number(val).toLocaleString();
};

export default function Dashboard() {
  // ── Datasets selection state ───────────────────────────────────────────────
  const [datasets, setDatasets] = useState([]);
  const [selectedDatasetId, setSelectedDatasetId] = useState('');
  const [datasetsLoading, setDatasetsLoading] = useState(true);

  // ── Analytics data states ──────────────────────────────────────────────────
  const [analyticsLoading, setAnalyticsLoading] = useState(false);
  const [kpis, setKpis] = useState(null);
  const [trends, setTrends] = useState(null);
  const [anomalies, setAnomalies] = useState(null);
  const [segments, setSegments] = useState(null);
  const [finance, setFinance] = useState(null);
  const [operations, setOperations] = useState(null);
  const [marketing, setMarketing] = useState(null);

  // ── 1. Load Datasets on Mount ──────────────────────────────────────────────
  useEffect(() => {
    async function fetchDatasets() {
      setDatasetsLoading(true);
      try {
        const data = await listDatasetsApi();
        setDatasets(data || []);
        if (data && data.length > 0) {
          setSelectedDatasetId(data[0].id);
        }
      } catch (err) {
        toast.error('Failed to load dataset inventory.');
      } finally {
        setDatasetsLoading(false);
      }
    }
    fetchDatasets();
  }, []);

  // ── 2. Load Analytics When Selected Dataset Changes ────────────────────────
  useEffect(() => {
    if (!selectedDatasetId) return;

    async function loadAnalytics() {
      setAnalyticsLoading(true);
      try {
        const [
          kpiRes,
          trendsRes,
          anomRes,
          segRes,
          finRes,
          opsRes,
          mktRes,
        ] = await Promise.all([
          getKpisApi(selectedDatasetId).catch(() => null),
          getTrendsApi(selectedDatasetId).catch(() => null),
          getAnomaliesApi(selectedDatasetId).catch(() => null),
          getSegmentsApi(selectedDatasetId).catch(() => null),
          getFinanceApi(selectedDatasetId).catch(() => null),
          getOperationsApi(selectedDatasetId).catch(() => null),
          getMarketingApi(selectedDatasetId).catch(() => null),
        ]);

        setKpis(kpiRes);
        setTrends(trendsRes);
        setAnomalies(anomRes);
        setSegments(segRes);
        setFinance(finRes);
        setOperations(opsRes);
        setMarketing(mktRes);
      } catch (err) {
        toast.error('Failed to load analytical metrics.');
      } finally {
        setAnalyticsLoading(false);
      }
    }

    loadAnalytics();
  }, [selectedDatasetId]);

  // ── Chart Data Preparations ────────────────────────────────────────────────
  const monthlyData = useMemo(() => {
    if (!trends?.monthly_metrics) return [];
    return trends.monthly_metrics.map((m) => ({
      month: m.month,
      Revenue: m.revenue || 0,
      Expenses: m.expenses || 0,
      COGS: m.cogs || 0,
      NetProfit: m.net_profit || 0,
      GrossProfit: m.gross_profit || 0,
      Orders: m.order_count || 0,
      MoMGrowth: m.mom_revenue_growth_pct || 0,
    }));
  }, [trends]);

  const expenseCategoryData = useMemo(() => {
    if (!finance?.expenses_by_category) return [];
    return finance.expenses_by_category.map((item) => ({
      name: item.category,
      value: item.amount,
      percentage: item.percentage,
    }));
  }, [finance]);

  const categoryMarginData = useMemo(() => {
    if (!finance?.margin_by_category) return [];
    return finance.margin_by_category.slice(0, 8).map((c) => ({
      category: c.category,
      Revenue: c.revenue || 0,
      Cost: c.cost || 0,
      MarginPct: c.margin_pct || 0,
    }));
  }, [finance]);

  const segmentData = useMemo(() => {
    if (!segments?.segments) return [];
    return segments.segments.map((s) => ({
      name: s.segment_name,
      customers: s.customer_count,
      revenue: s.total_revenue,
      revenueShare: s.revenue_share_pct,
    }));
  }, [segments]);

  const movementData = useMemo(() => {
    if (!operations?.movement_by_type) return [];
    return operations.movement_by_type.map((m) => ({
      name: m.movement_type,
      quantity: Math.abs(m.total_quantity || 0),
    }));
  }, [operations]);

  const channelData = useMemo(() => {
    if (!marketing?.channel_performance) return [];
    return marketing.channel_performance.map((c) => ({
      channel: c.channel,
      Revenue: c.revenue || 0,
      Orders: c.order_count || 0,
      AvgDiscount: c.avg_discount_pct || 0,
    }));
  }, [marketing]);

  // ── Render: Empty State if No Datasets Exist ───────────────────────────────
  if (!datasetsLoading && datasets.length === 0) {
    return (
      <div className="page-wrapper">
        <div className="page-header">
          <h2 className="page-header__title">Executive Retail Intelligence</h2>
          <p className="page-header__sub">Real-time analytical metrics, profitability, and operational insights.</p>
        </div>
        <div className="card empty-dashboard-card">
          <span className="empty-dashboard-card__icon">📊</span>
          <h3 className="empty-dashboard-card__title">No Ingested Datasets Found</h3>
          <p className="empty-dashboard-card__sub">
            The analytics dashboard consumes real Pandas computations calculated directly from your retail
            transactions and inventory files. Upload your first dataset workbook to unlock this view.
          </p>
          <Link to="/datasets" className="btn btn--primary">
            📁 Ingest a Dataset Now
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="page-wrapper dashboard-page">
      {/* ── Top Bar: Title & Dataset Selector ── */}
      <div className="dashboard-header">
        <div>
          <h2 className="page-header__title">Executive Retail Dashboard</h2>
          <p className="page-header__sub">
            Grounded intelligence generated via pure statistical analysis (Pandas/NumPy) with zero hallucination.
          </p>
        </div>

        {/* Dataset selector dropdown */}
        <div className="dataset-selector-box">
          <label htmlFor="dataset-select" className="dataset-selector-label">
            Active Dataset:
          </label>
          <select
            id="dataset-select"
            className="form-input dataset-select-input"
            value={selectedDatasetId}
            onChange={(e) => setSelectedDatasetId(e.target.value)}
            disabled={analyticsLoading || datasetsLoading}
          >
            {datasets.map((d) => (
              <option key={d.id} value={d.id}>
                {d.original_filename} ({formatNumber(d.total_rows)} rows)
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* ── Section 1: Executive KPI Scorecard (12 Cards) ── */}
      <div className="section-title-wrap">
        <h3 className="section-title">1. Executive Performance Scorecard</h3>
        <span className="section-badge">Verified Mathematical Metrics</span>
      </div>

      {analyticsLoading || !kpis ? (
        <div className="kpi-grid">
          {Array.from({ length: 12 }).map((_, i) => (
            <div key={i} className="kpi-card kpi-card--skeleton">
              <div className="skeleton-line skeleton-line--sm" />
              <div className="skeleton-line skeleton-line--lg" />
              <div className="skeleton-line skeleton-line--xs" />
            </div>
          ))}
        </div>
      ) : (
        <div className="kpi-grid">
          {/* Card 1: Total Revenue */}
          <div className="kpi-card kpi-card--primary">
            <span className="kpi-card__label">Total Revenue</span>
            <span className="kpi-card__value">{formatCurrency(kpis.total_revenue)}</span>
            <span className="kpi-card__sub">Completed transactions</span>
          </div>

          {/* Card 2: Total COGS */}
          <div className="kpi-card">
            <span className="kpi-card__label">Cost of Goods Sold (COGS)</span>
            <span className="kpi-card__value">{formatCurrency(kpis.total_cogs)}</span>
            <span className="kpi-card__sub">Product cost basis</span>
          </div>

          {/* Card 3: Gross Profit & Margin */}
          <div className="kpi-card kpi-card--success">
            <span className="kpi-card__label">Gross Profit</span>
            <span className="kpi-card__value">{formatCurrency(kpis.gross_profit)}</span>
            <span className="kpi-card__badge">
              Margin: {formatPercent(kpis.gross_margin_pct)}
            </span>
          </div>

          {/* Card 4: Operating Expenses */}
          <div className="kpi-card">
            <span className="kpi-card__label">Operating Expenses</span>
            <span className="kpi-card__value">{formatCurrency(kpis.total_expenses)}</span>
            <span className="kpi-card__sub">Overhead, marketing, logistics</span>
          </div>

          {/* Card 5: Net Profit & Net Margin */}
          <div className="kpi-card kpi-card--highlight">
            <span className="kpi-card__label">Net Operating Profit</span>
            <span className="kpi-card__value">{formatCurrency(kpis.net_profit)}</span>
            <span className="kpi-card__badge">
              Net Margin: {formatPercent(kpis.net_margin_pct)}
            </span>
          </div>

          {/* Card 6: Order Count */}
          <div className="kpi-card">
            <span className="kpi-card__label">Total Orders</span>
            <span className="kpi-card__value">{formatNumber(kpis.order_count)}</span>
            <span className="kpi-card__sub">Verified orders</span>
          </div>

          {/* Card 7: Average Order Value (AOV) */}
          <div className="kpi-card">
            <span className="kpi-card__label">Average Order Value (AOV)</span>
            <span className="kpi-card__value">{formatCurrency(kpis.avg_order_value)}</span>
            <span className="kpi-card__sub">Revenue / order</span>
          </div>

          {/* Card 8: Unique Customers */}
          <div className="kpi-card">
            <span className="kpi-card__label">Active Customers</span>
            <span className="kpi-card__value">{formatNumber(kpis.unique_customers)}</span>
            <span className="kpi-card__sub">Unique buyers in period</span>
          </div>

          {/* Card 9: Repeat Customer Rate */}
          <div className="kpi-card">
            <span className="kpi-card__label">Repeat Purchase Rate</span>
            <span className="kpi-card__value">{formatPercent(kpis.repeat_customer_rate_pct)}</span>
            <span className="kpi-card__sub">Customers with &gt;1 orders</span>
          </div>

          {/* Card 10: Inventory Turnover (Retail Specific) */}
          <div className="kpi-card kpi-card--retail">
            <span className="kpi-card__label">Inventory Turnover</span>
            <span className="kpi-card__value">
              {Number(kpis.inventory_turnover || 0).toFixed(2)}x
            </span>
            <span className="kpi-card__sub">COGS / avg inventory</span>
          </div>

          {/* Card 11: Stockout Incidents (Retail Specific) */}
          <div className="kpi-card kpi-card--warning">
            <span className="kpi-card__label">Stockout Incidents</span>
            <span className="kpi-card__value">{formatNumber(kpis.stockout_count)}</span>
            <span className="kpi-card__sub">Stock depleted to 0</span>
          </div>

          {/* Card 12: Return Rate (Retail Specific) */}
          <div className="kpi-card">
            <span className="kpi-card__label">Product Return Rate</span>
            <span className="kpi-card__value">{formatPercent(kpis.return_rate_pct)}</span>
            <span className="kpi-card__sub">Returns / total orders</span>
          </div>
        </div>
      )}

      {/* ── Section 2: Charts Grid Row 1 (Monthly Trends & Profit Progression) ── */}
      <div className="charts-grid charts-grid--2">
        {/* Chart A: Monthly Revenue vs Expense Composed Chart */}
        <div className="card chart-card">
          <div className="chart-card__header">
            <div>
              <h4 className="chart-card__title">Monthly Revenue vs Expenses &amp; COGS</h4>
              <p className="chart-card__sub">Monthly bar progression with Net Profit overlay line</p>
            </div>
          </div>
          {analyticsLoading ? (
            <div className="chart-skeleton" />
          ) : monthlyData.length === 0 ? (
            <div className="chart-empty">No monthly data available</div>
          ) : (
            <div className="chart-container">
              <ResponsiveContainer width="100%" height={300}>
                <ComposedChart data={monthlyData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                  <XAxis dataKey="month" stroke="#64748b" fontSize={12} />
                  <YAxis stroke="#64748b" fontSize={12} tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`} />
                  <Tooltip formatter={(value) => formatCurrency(value)} />
                  <Legend />
                  <Bar dataKey="Revenue" fill="#2563eb" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="COGS" fill="#94a3b8" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="Expenses" fill="#f59e0b" radius={[4, 4, 0, 0]} />
                  <Line type="monotone" dataKey="NetProfit" stroke="#16a34a" strokeWidth={3} dot={{ r: 4 }} />
                </ComposedChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>

        {/* Chart B: Profit Progression & Margin Trend */}
        <div className="card chart-card">
          <div className="chart-card__header">
            <div>
              <h4 className="chart-card__title">Profitability Progression (Gross vs Net)</h4>
              <p className="chart-card__sub">Cumulative operational value retained after direct &amp; indirect costs</p>
            </div>
          </div>
          {analyticsLoading ? (
            <div className="chart-skeleton" />
          ) : monthlyData.length === 0 ? (
            <div className="chart-empty">No profit trend data available</div>
          ) : (
            <div className="chart-container">
              <ResponsiveContainer width="100%" height={300}>
                <AreaChart data={monthlyData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                  <defs>
                    <linearGradient id="grossGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#2563eb" stopOpacity={0.4} />
                      <stop offset="95%" stopColor="#2563eb" stopOpacity={0} />
                    </linearGradient>
                    <linearGradient id="netGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#16a34a" stopOpacity={0.4} />
                      <stop offset="95%" stopColor="#16a34a" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                  <XAxis dataKey="month" stroke="#64748b" fontSize={12} />
                  <YAxis stroke="#64748b" fontSize={12} tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`} />
                  <Tooltip formatter={(value) => formatCurrency(value)} />
                  <Legend />
                  <Area type="monotone" dataKey="GrossProfit" stroke="#2563eb" fillOpacity={1} fill="url(#grossGrad)" />
                  <Area type="monotone" dataKey="NetProfit" stroke="#16a34a" fillOpacity={1} fill="url(#netGrad)" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>
      </div>

      {/* ── Section 3: Charts Grid Row 2 (Category Margins & Expense Breakdown) ── */}
      <div className="charts-grid charts-grid--2">
        {/* Chart C: Expense Breakdown (Donut Pie) */}
        <div className="card chart-card">
          <div className="chart-card__header">
            <div>
              <h4 className="chart-card__title">Operating Expense Breakdown</h4>
              <p className="chart-card__sub">Distribution of costs across marketing, payroll, logistics, rent</p>
            </div>
          </div>
          {analyticsLoading ? (
            <div className="chart-skeleton" />
          ) : expenseCategoryData.length === 0 ? (
            <div className="chart-empty">No expense category data</div>
          ) : (
            <div className="chart-container chart-container--pie">
              <ResponsiveContainer width="100%" height={280}>
                <PieChart>
                  <Pie
                    data={expenseCategoryData}
                    dataKey="value"
                    nameKey="name"
                    cx="50%"
                    cy="50%"
                    innerRadius={65}
                    outerRadius={95}
                    paddingAngle={3}
                  >
                    {expenseCategoryData.map((_, index) => (
                      <Cell key={`cell-${index}`} fill={CHART_COLORS[index % CHART_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip
                    formatter={(val, name, item) => [
                      `${formatCurrency(val)} (${formatPercent(item.payload.percentage)})`,
                      name,
                    ]}
                  />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>

        {/* Chart D: Category Margins Bar Chart */}
        <div className="card chart-card">
          <div className="chart-card__header">
            <div>
              <h4 className="chart-card__title">Product Category Revenue vs Cost</h4>
              <p className="chart-card__sub">Top merchandise categories ranked by volume</p>
            </div>
          </div>
          {analyticsLoading ? (
            <div className="chart-skeleton" />
          ) : categoryMarginData.length === 0 ? (
            <div className="chart-empty">No category margin data</div>
          ) : (
            <div className="chart-container">
              <ResponsiveContainer width="100%" height={280}>
                <BarChart data={categoryMarginData} layout="vertical" margin={{ top: 5, right: 20, left: 40, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                  <XAxis type="number" stroke="#64748b" fontSize={12} tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`} />
                  <YAxis type="category" dataKey="category" stroke="#64748b" fontSize={12} width={80} />
                  <Tooltip formatter={(value) => formatCurrency(value)} />
                  <Legend />
                  <Bar dataKey="Revenue" fill="#2563eb" radius={[0, 4, 4, 0]} />
                  <Bar dataKey="Cost" fill="#94a3b8" radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>
      </div>

      {/* ── Section 4: Customer RFM Segmentation & Retail Operations ── */}
      <div className="charts-grid charts-grid--2">
        {/* Chart E: Customer RFM Behavioral Segments */}
        <div className="card chart-card">
          <div className="chart-card__header">
            <div>
              <h4 className="chart-card__title">Customer RFM Behavioral Clusters</h4>
              <p className="chart-card__sub">Recency, Frequency, Monetary spend tiers &amp; revenue share</p>
            </div>
          </div>
          {analyticsLoading ? (
            <div className="chart-skeleton" />
          ) : segmentData.length === 0 ? (
            <div className="chart-empty">No customer segment data</div>
          ) : (
            <div className="chart-container">
              <ResponsiveContainer width="100%" height={260}>
                <BarChart data={segmentData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                  <XAxis dataKey="name" stroke="#64748b" fontSize={11} />
                  <YAxis yAxisId="left" stroke="#2563eb" fontSize={12} tickFormatter={(v) => formatNumber(v)} />
                  <YAxis yAxisId="right" orientation="right" stroke="#16a34a" fontSize={12} tickFormatter={(v) => `${v}%`} />
                  <Tooltip
                    formatter={(val, name) => [
                      name === 'revenueShare' ? formatPercent(val) : formatNumber(val),
                      name === 'revenueShare' ? 'Revenue Share' : 'Customer Count',
                    ]}
                  />
                  <Legend />
                  <Bar yAxisId="left" dataKey="customers" name="Customers" fill="#2563eb" radius={[4, 4, 0, 0]} />
                  <Bar yAxisId="right" dataKey="revenueShare" name="Revenue Share %" fill="#16a34a" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>

        {/* Chart F: Industry-Specific Retail Chart (Inventory Movements or Channel Mix) */}
        <div className="card chart-card">
          <div className="chart-card__header">
            <div>
              <h4 className="chart-card__title">Warehouse &amp; Inventory Movements</h4>
              <p className="chart-card__sub">Distribution of physical goods throughput by movement category</p>
            </div>
          </div>
          {analyticsLoading ? (
            <div className="chart-skeleton" />
          ) : movementData.length === 0 ? (
            <div className="chart-empty">No inventory movement data</div>
          ) : (
            <div className="chart-container">
              <ResponsiveContainer width="100%" height={260}>
                <BarChart data={movementData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                  <XAxis dataKey="name" stroke="#64748b" fontSize={12} />
                  <YAxis stroke="#64748b" fontSize={12} tickFormatter={(v) => formatNumber(v)} />
                  <Tooltip formatter={(value) => [formatNumber(value), 'Units Moved']} />
                  <Bar dataKey="quantity" fill="#8b5cf6" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>
      </div>

      {/* ── Section 5: Statistical & Business Anomalies Feed ── */}
      <div className="card anomalies-card">
        <div className="anomalies-header">
          <div>
            <h4 className="anomalies-title">Detected Business &amp; Statistical Anomalies</h4>
            <p className="anomalies-sub">
              Flagged data points deviating &gt; 1.5 standard deviations or experiencing &gt; 20% rapid MoM shifts.
            </p>
          </div>
          <span className="anomalies-count-badge">
            {anomalies?.anomalies ? `${anomalies.anomalies.length} Flags Detected` : '0 Flags'}
          </span>
        </div>

        {analyticsLoading ? (
          <div className="anomalies-skeleton-list">
            <div className="skeleton-line skeleton-line--md" />
            <div className="skeleton-line skeleton-line--md" />
            <div className="skeleton-line skeleton-line--md" />
          </div>
        ) : !anomalies?.anomalies || anomalies.anomalies.length === 0 ? (
          <div className="anomalies-empty">
            <span className="anomalies-empty__icon">✅</span>
            <p className="anomalies-empty__title">No Anomalies Detected</p>
            <p className="anomalies-empty__sub">
              All metrics operate within standard statistical variance thresholds (&plusmn;1.5 std dev).
            </p>
          </div>
        ) : (
          <div className="anomalies-list">
            {anomalies.anomalies.map((item, idx) => (
              <div key={idx} className={`anomaly-item anomaly-item--${(item.severity || 'medium').toLowerCase()}`}>
                <div className="anomaly-item__header">
                  <div className="anomaly-item__meta">
                    <span className={`severity-badge severity-badge--${(item.severity || 'medium').toLowerCase()}`}>
                      {item.severity || 'MEDIUM'}
                    </span>
                    <strong className="anomaly-item__metric">{item.metric_name}</strong>
                    {item.entity_or_month && (
                      <span className="anomaly-item__entity">({item.entity_or_month})</span>
                    )}
                  </div>
                  <div className="anomaly-item__values">
                    <span className="anomaly-val">
                      Observed: <strong>{typeof item.observed_value === 'number' ? Number(item.observed_value).toFixed(2) : String(item.observed_value)}</strong>
                    </span>
                    {item.baseline_or_prev !== undefined && (
                      <span className="anomaly-baseline">
                        Baseline: {typeof item.baseline_or_prev === 'number' ? Number(item.baseline_or_prev).toFixed(2) : String(item.baseline_or_prev)}
                      </span>
                    )}
                  </div>
                </div>
                <p className="anomaly-item__explanation">{item.explanation}</p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
