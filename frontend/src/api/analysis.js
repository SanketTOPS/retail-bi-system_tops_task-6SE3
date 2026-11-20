/**
 * src/api/analysis.js
 * ───────────────────
 * Multi-Agent Analysis Execution & Polling API client.
 */

import api from './axiosInstance';

/**
 * Trigger background CrewAI multi-agent analysis.
 */
export async function runAnalysisApi({ dataset_id, user_question = null }) {
  const res = await api.post('/analysis/run', {
    dataset_id,
    user_question,
  });
  return res.data.data ?? res.data;
}

/**
 * Poll execution progress, active agent, and per-agent statuses.
 */
export async function getAnalysisStatusApi(analysisId) {
  const res = await api.get(`/analysis/${analysisId}/status`);
  return res.data.data ?? res.data;
}

/**
 * Fetch detailed agent traces, reasoning logs, and duration metrics.
 */
export async function getAnalysisLogsApi(analysisId) {
  const res = await api.get(`/analysis/${analysisId}/logs`);
  return res.data.data ?? res.data;
}

/**
 * Fetch completed business intelligence report and verification findings.
 */
export async function getAnalysisReportApi(analysisId) {
  const res = await api.get(`/analysis/${analysisId}/report`);
  return res.data.data ?? res.data;
}

/**
 * Fetch chronological analysis history for current user (or all if admin).
 */
export async function getAnalysisHistoryApi() {
  const res = await api.get('/analysis/history');
  return res.data.data ?? res.data;
}
