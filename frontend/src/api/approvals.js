/**
 * src/api/approvals.js
 * ────────────────────
 * Human-in-the-Loop (HITL) Approvals API Client.
 */

import api from './axiosInstance';

/**
 * Fetch pending recommendations requiring managerial sign-off.
 * Restricted to manager and admin roles.
 */
export async function getPendingApprovalsApi() {
  const res = await api.get('/approvals/pending');
  return res.data.data ?? res.data;
}

/**
 * Record managerial decision on a consequential recommendation.
 *
 * @param {string} recommendationId - UUID
 * @param {string} action - 'approve' | 'reject'
 * @param {string} [comment] - Optional rationale
 */
export async function recordDecisionApi(recommendationId, { action, comment }) {
  const res = await api.post(`/approvals/${recommendationId}/decision`, {
    action,
    comment,
  });
  return res.data.data ?? res.data;
}

/**
 * Fetch chronological audit trail of all managerial decisions.
 */
export async function getApprovalHistoryApi(skip = 0, limit = 50) {
  const res = await api.get('/approvals/history', {
    params: { skip, limit },
  });
  return res.data.data ?? res.data;
}
