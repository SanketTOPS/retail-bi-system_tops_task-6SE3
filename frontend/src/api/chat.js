/**
 * src/api/chat.js
 * ───────────────
 * Business Intelligence AI Advisor Chat API Client.
 */

import api from './axiosInstance';

/**
 * Send inquiry to grounded Business AI Advisor.
 *
 * @param {string} message - User question
 * @param {string} [analysisId] - Optional UUID of analysis for specific context
 */
export async function sendChatMessageApi({ message, analysis_id = null }) {
  const res = await api.post('/chat', {
    message,
    analysis_id,
  });
  return res.data.data ?? res.data;
}

/**
 * Fetch chronological chat message history.
 */
export async function getChatHistoryApi(skip = 0, limit = 50) {
  const res = await api.get('/chat/history', {
    params: { skip, limit },
  });
  return res.data.data ?? res.data;
}

/**
 * Clear all chat history for authenticated user.
 */
export async function clearChatHistoryApi() {
  const res = await api.delete('/chat/history');
  return res.data.data ?? res.data;
}
