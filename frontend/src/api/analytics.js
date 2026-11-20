/**
 * src/api/analytics.js
 * ────────────────────
 * Analytics API Client — pure Pandas calculations from backend (no LLM).
 */

import api from './axiosInstance';

/**
 * Fetch Executive KPI Summary for a dataset.
 */
export async function getKpisApi(datasetId) {
  const res = await api.get(`/analytics/${datasetId}/kpis`);
  return res.data.data ?? res.data;
}

/**
 * Fetch Monthly Trends & MoM Growth metrics.
 */
export async function getTrendsApi(datasetId) {
  const res = await api.get(`/analytics/${datasetId}/trends`);
  return res.data.data ?? res.data;
}

/**
 * Fetch Statistical & Business Anomalies (>1.5 std dev or >20% MoM shift).
 */
export async function getAnomaliesApi(datasetId) {
  const res = await api.get(`/analytics/${datasetId}/anomalies`);
  return res.data.data ?? res.data;
}

/**
 * Fetch Customer RFM Segments and revenue shares.
 */
export async function getSegmentsApi(datasetId) {
  const res = await api.get(`/analytics/${datasetId}/segments`);
  return res.data.data ?? res.data;
}

/**
 * Fetch Sales & Marketing Channel Performance.
 */
export async function getMarketingApi(datasetId) {
  const res = await api.get(`/analytics/${datasetId}/marketing`);
  return res.data.data ?? res.data;
}

/**
 * Fetch Financial Breakdown (expenses by category, margins, cost ratio).
 */
export async function getFinanceApi(datasetId) {
  const res = await api.get(`/analytics/${datasetId}/finance`);
  return res.data.data ?? res.data;
}

/**
 * Fetch Operational & Inventory Health metrics.
 */
export async function getOperationsApi(datasetId) {
  const res = await api.get(`/analytics/${datasetId}/operations`);
  return res.data.data ?? res.data;
}

/**
 * Fetch consolidated dashboard overview (KPIs, trends, anomalies, marketing).
 */
export async function getDashboardSummaryApi(datasetId) {
  const res = await api.get(`/analytics/${datasetId}/dashboard-summary`);
  return res.data.data ?? res.data;
}
