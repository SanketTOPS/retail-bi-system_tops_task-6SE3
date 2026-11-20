/**
 * src/pages/Chat.jsx
 * ──────────────────
 * Business Intelligence AI Advisor Chat Interface (Module 13.5).
 *
 * Capabilities:
 *  - ChatGPT-style conversation view with chronological message history.
 *  - Optional context binding: Ask questions grounded in a specific Analysis Run
 *    or against the entire active enterprise retail store.
 *  - Quick prompt recommendation pills for immediate insight exploration.
 *  - Typing animation indicator while the single-agent Q&A tool-grounded advisor runs.
 *  - Clear conversation history action.
 *  - Strict grounding: The agent is programmed to say "Data not available" instead
 *    of hallucinating, and only uses numbers derived from deterministic tools.
 */

import React, { useEffect, useRef, useState } from 'react';
import toast from 'react-hot-toast';
import {
  sendChatMessageApi,
  getChatHistoryApi,
  clearChatHistoryApi,
} from '@/api/chat';
import { getAnalysisHistoryApi } from '@/api/analysis';

const SUGGESTED_QUESTIONS = [
  'What were the primary drivers of the gross margin dip in Q3?',
  'Which product categories exhibited the highest return rates and why?',
  'How do our repeat purchase rates compare between Champions and At-Risk customer tiers?',
  'What are our top 3 stockout risk areas, and what reorder adjustments are recommended?',
  'Explain our operating cost-to-revenue ratio and major expense categories.',
];

export default function Chat() {
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [historyRuns, setHistoryRuns] = useState([]);
  const [selectedAnalysisId, setSelectedAnalysisId] = useState('');
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);

  const messagesEndRef = useRef(null);
  const textareaRef = useRef(null);

  // ── 1. Load Initial History ────────────────────────────────────────────────
  const loadChat = async () => {
    setLoading(true);
    try {
      const [histRes, runsRes] = await Promise.all([
        getChatHistoryApi().catch(() => ({ messages: [] })),
        getAnalysisHistoryApi().catch(() => []),
      ]);
      setMessages(histRes.messages || []);
      setHistoryRuns(runsRes || []);
    } catch {
      toast.error('Failed to load conversation history.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadChat();
  }, []);

  // ── 2. Scroll to bottom on new message ─────────────────────────────────────
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, sending]);

  // ── 3. Send Message ────────────────────────────────────────────────────────
  const handleSendMessage = async (textToSend) => {
    const text = (textToSend || inputMessage).trim();
    if (!text || sending) return;

    // Optimistically push user message to UI
    const tempUserMsg = {
      id: `temp-${Date.now()}`,
      sender: 'user',
      message: text,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, tempUserMsg]);
    setInputMessage('');
    setSending(true);

    try {
      const result = await sendChatMessageApi({
        message: text,
        analysis_id: selectedAnalysisId || null,
      });

      // Replace optimistic message and append assistant response
      setMessages((prev) => {
        const filtered = prev.filter((m) => m.id !== tempUserMsg.id);
        return [...filtered, result.user_message, result.assistant_message];
      });
    } catch (err) {
      const detail = err.response?.data?.detail;
      const msg = typeof detail === 'string' ? detail : 'Failed to send message to AI advisor.';
      toast.error(msg);
      // Remove failed message
      setMessages((prev) => prev.filter((m) => m.id !== tempUserMsg.id));
    } finally {
      setSending(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  // ── 4. Clear Conversation History ──────────────────────────────────────────
  const handleClearHistory = async () => {
    const confirmed = window.confirm('Are you sure you want to clear your conversation history?');
    if (!confirmed) return;

    try {
      await clearChatHistoryApi();
      setMessages([]);
      toast.success('Conversation history cleared.');
    } catch {
      toast.error('Failed to clear chat history.');
    }
  };

  return (
    <div className="page-wrapper chat-page">
      {/* ── Top Bar ── */}
      <div className="dashboard-header">
        <div>
          <h2 className="page-header__title">Grounded Business AI Advisor</h2>
          <p className="page-header__sub">
            Inquire directly with your data. The advisor accesses verified analytical tools and refuses to hallucinate.
          </p>
        </div>

        <div className="chat-header-actions">
          {/* Analysis Context Selector */}
          <div className="dataset-selector-box">
            <label htmlFor="chat-context-select" className="dataset-selector-label">
              Context:
            </label>
            <select
              id="chat-context-select"
              className="form-input dataset-select-input"
              value={selectedAnalysisId}
              onChange={(e) => setSelectedAnalysisId(e.target.value)}
              disabled={sending}
            >
              <option value="">Latest Store Intelligence (Default)</option>
              {historyRuns.map((r) => (
                <option key={r.id} value={r.id}>
                  Analysis {r.id.slice(0, 8)} ({new Date(r.started_at).toLocaleDateString()})
                </option>
              ))}
            </select>
          </div>

          <button
            type="button"
            className="btn btn--secondary btn--sm"
            onClick={handleClearHistory}
            disabled={messages.length === 0 || sending}
            title="Clear Chat Logs"
          >
            🗑️ Clear
          </button>
        </div>
      </div>

      {/* ── Chat Messages Container ── */}
      <div className="card chat-container-card">
        <div className="chat-messages-scroll">
          {loading ? (
            <div className="loading-card" style={{ height: '350px' }}>
              <div className="spinner spinner--lg" />
              <p className="loading-text">Loading conversation transcript...</p>
            </div>
          ) : messages.length === 0 ? (
            <div className="chat-welcome-box">
              <span className="chat-welcome-icon">💬</span>
              <h3 className="chat-welcome-title">Ask Your Retail Intelligence Advisor</h3>
              <p className="chat-welcome-sub">
                Answers are backed directly by Pandas analytics tools and verified report findings.
                Try one of the suggested inquiries below:
              </p>

              <div className="chat-suggestions-grid">
                {SUGGESTED_QUESTIONS.map((q, idx) => (
                  <button
                    key={idx}
                    type="button"
                    className="chat-suggestion-card"
                    onClick={() => handleSendMessage(q)}
                  >
                    <span>💡</span>
                    <p>{q}</p>
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="chat-stream">
              {messages.map((msg, index) => {
                const isUser = msg.sender === 'user';
                return (
                  <div
                    key={msg.id || index}
                    className={`chat-bubble-row ${isUser ? 'chat-bubble-row--user' : 'chat-bubble-row--assistant'}`}
                  >
                    {!isUser && (
                      <div className="chat-avatar" title="AI Retail Advisor">
                        🤖
                      </div>
                    )}

                    <div className={`chat-bubble ${isUser ? 'chat-bubble--user' : 'chat-bubble--assistant'}`}>
                      <div className="chat-bubble__content">
                        {msg.message}
                      </div>
                      <span className="chat-bubble__time">
                        {new Date(msg.created_at || Date.now()).toLocaleTimeString([], {
                          hour: '2-digit',
                          minute: '2-digit',
                        })}
                      </span>
                    </div>

                    {isUser && (
                      <div className="chat-avatar chat-avatar--user" title="You">
                        👤
                      </div>
                    )}
                  </div>
                );
              })}

              {/* Typing Indicator */}
              {sending && (
                <div className="chat-bubble-row chat-bubble-row--assistant">
                  <div className="chat-avatar">🤖</div>
                  <div className="chat-bubble chat-bubble--assistant chat-bubble--typing">
                    <div className="typing-dots">
                      <span />
                      <span />
                      <span />
                    </div>
                    <span className="typing-label">Analyzing PostgreSQL tables &amp; verifying metrics...</span>
                  </div>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* ── Suggested Questions Strip (When chat active) ── */}
        {messages.length > 0 && !sending && (
          <div className="chat-quick-strip">
            <span className="chat-quick-label">Suggested follow-ups:</span>
            <div className="chat-quick-scroll">
              {SUGGESTED_QUESTIONS.slice(0, 3).map((q, idx) => (
                <button
                  key={idx}
                  type="button"
                  className="chip chip--suggestion"
                  onClick={() => handleSendMessage(q)}
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* ── Input Box ── */}
        <div className="chat-input-bar">
          <textarea
            ref={textareaRef}
            className="chat-textarea"
            rows={1}
            placeholder="Ask a question about sales, inventory, profit margins, or anomalies..."
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={sending}
          />
          <button
            type="button"
            className="btn btn--primary btn--send"
            onClick={() => handleSendMessage()}
            disabled={!inputMessage.trim() || sending}
            aria-label="Send message"
          >
            {sending ? <span className="spinner spinner--sm" /> : '➤'}
          </button>
        </div>
      </div>
    </div>
  );
}
