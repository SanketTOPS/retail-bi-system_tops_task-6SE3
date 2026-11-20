/**
 * src/pages/Approvals.jsx
 * ───────────────────────
 * Human-in-the-Loop (HITL) Managerial Approvals Page (Module 13.5).
 *
 * Gated to Manager and Admin roles only.
 *
 * Core Capabilities:
 *  - View pending strategic recommendations that require managerial consent.
 *  - Enforce rule: Only recommendations from VERIFIED parent reports are actionable.
 *  - Interactive Approve / Reject decision modal with operational comment field.
 *  - Real-time simulation of ERP/retail workflow dispatch upon approval.
 *  - Comprehensive chronological audit trail of all historical approval decisions.
 */

import React, { useEffect, useState } from 'react';
import toast from 'react-hot-toast';
import { useAuth } from '@/hooks/useAuth';
import {
  getPendingApprovalsApi,
  recordDecisionApi,
  getApprovalHistoryApi,
} from '@/api/approvals';

export default function Approvals() {
  const { role } = useAuth();

  const [pendingItems, setPendingItems] = useState([]);
  const [historyItems, setHistoryItems] = useState([]);
  const [loading, setLoading] = useState(true);

  // Decision Modal States
  const [selectedRec, setSelectedRec] = useState(null);
  const [decisionAction, setDecisionAction] = useState('approve'); // 'approve' | 'reject'
  const [decisionComment, setDecisionComment] = useState('');
  const [submitting, setSubmitting] = useState(false);

  // ── 1. Load Data ───────────────────────────────────────────────────────────
  const loadData = async () => {
    setLoading(true);
    try {
      const [pending, history] = await Promise.all([
        getPendingApprovalsApi().catch(() => []),
        getApprovalHistoryApi().catch(() => []),
      ]);
      setPendingItems(pending || []);
      setHistoryItems(history || []);
    } catch {
      toast.error('Failed to load approvals queue.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  // ── 2. Open Decision Modal ─────────────────────────────────────────────────
  const handleOpenDecision = (rec, action) => {
    setSelectedRec(rec);
    setDecisionAction(action);
    setDecisionComment('');
  };

  // ── 3. Submit Decision ─────────────────────────────────────────────────────
  const handleSubmitDecision = async () => {
    if (!selectedRec) return;

    setSubmitting(true);
    try {
      const result = await recordDecisionApi(selectedRec.recommendation_id, {
        action: decisionAction,
        comment: decisionComment.trim() || null,
      });

      const actionText = decisionAction === 'approve' ? 'approved' : 'rejected';
      toast.success(`Recommendation "${selectedRec.title}" ${actionText}!`);

      // Optimistically update lists
      setPendingItems((prev) =>
        prev.filter((i) => i.recommendation_id !== selectedRec.recommendation_id)
      );

      // Reload history to capture audit record
      getApprovalHistoryApi().then((h) => setHistoryItems(h || []));
      setSelectedRec(null);
    } catch (err) {
      const detail = err.response?.data?.detail;
      const msg = typeof detail === 'string' ? detail : 'Failed to record approval decision.';
      toast.error(msg);
    } finally {
      setSubmitting(false);
    }
  };

  // ── Guard for Non-Managers (Secondary UX Guard) ────────────────────────────
  if (role !== 'admin' && role !== 'manager') {
    return (
      <div className="page-wrapper">
        <div className="card" style={{ padding: '40px', textAlign: 'center' }}>
          <span style={{ fontSize: '3rem' }}>🔒</span>
          <h2 style={{ marginTop: '12px' }}>Managerial Approval Gate Restricted</h2>
          <p style={{ color: 'var(--color-text-muted)', marginTop: '6px' }}>
            Only designated store managers and administrators possess operational authority
            to approve or reject strategic retail initiatives.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="page-wrapper approvals-page">
      {/* ── Page Header ── */}
      <div className="page-header">
        <h2 className="page-header__title">Human-in-the-Loop Strategic Approvals</h2>
        <p className="page-header__sub">
          Review consequential initiatives synthesized by the multi-agent system.
          No automated operational action executes without explicit management consent.
        </p>
      </div>

      {/* ── Section 1: Pending Approvals Queue ── */}
      <div className="approvals-section">
        <div className="section-title-wrap">
          <h3 className="section-title">Pending Consequential Initiatives</h3>
          <span className="anomalies-count-badge">
            {pendingItems.length} Actions Awaiting Review
          </span>
        </div>

        {loading ? (
          <div className="card loading-card">
            <div className="spinner spinner--lg" />
            <p className="loading-text">Loading approval queue...</p>
          </div>
        ) : pendingItems.length === 0 ? (
          <div className="card empty-approvals-card">
            <span className="empty-approvals-icon">✨</span>
            <h4>No Actions Pending Approval</h4>
            <p className="empty-approvals-sub">
              All strategic recommendations from verified analysis runs have been reviewed and decided.
            </p>
          </div>
        ) : (
          <div className="pending-grid">
            {pendingItems.map((item) => (
              <div key={item.recommendation_id} className="card pending-rec-card">
                <div className="pending-rec-card__top">
                  <div className="pending-rec-meta">
                    <span className={`priority-tag priority-tag--p${item.priority}`}>
                      P{item.priority}
                    </span>
                    <span className="rec-cat-pill">{item.category || 'Operations'}</span>
                    <span className="ver-status-indicator">
                      🛡️ {item.report_verification_status || 'VERIFIED'}
                    </span>
                  </div>
                  <span className="rec-date">{new Date(item.created_at).toLocaleDateString()}</span>
                </div>

                <h4 className="pending-rec-title">{item.title}</h4>
                <p className="pending-rec-desc">{item.description}</p>

                {item.expected_impact && (
                  <div className="pending-rec-impact">
                    <strong>Expected Business Impact:</strong>
                    <span>{item.expected_impact}</span>
                  </div>
                )}

                <div className="pending-rec-actions">
                  <button
                    type="button"
                    className="btn btn--secondary btn--reject"
                    onClick={() => handleOpenDecision(item, 'reject')}
                  >
                    ❌ Reject Initiative
                  </button>
                  <button
                    type="button"
                    className="btn btn--primary btn--approve"
                    onClick={() => handleOpenDecision(item, 'approve')}
                  >
                    ✅ Authorize Execution
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* ── Section 2: Historical Audit Trail Table ── */}
      <div className="card approvals-history-card" style={{ marginTop: '32px' }}>
        <div className="inventory-header">
          <div>
            <h3 className="inventory-title">Managerial Decision Audit Log</h3>
            <p className="chart-card__sub">
              Immutable historical record of every authorized and rejected business initiative.
            </p>
          </div>
          <button className="btn btn--secondary btn--sm" onClick={loadData} disabled={loading}>
            ↻ Refresh Log
          </button>
        </div>

        {historyItems.length === 0 ? (
          <div className="table-empty">
            <span className="table-empty__icon">📋</span>
            <p className="table-empty__title">No Historical Decisions Logged</p>
            <p className="table-empty__sub">Decisions recorded above will appear in this audit log.</p>
          </div>
        ) : (
          <div className="table-responsive">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Decided Date</th>
                  <th>Initiative / Title</th>
                  <th>Category</th>
                  <th>Decision</th>
                  <th>Manager Rationale / Notes</th>
                  <th>Authorized By</th>
                </tr>
              </thead>
              <tbody>
                {historyItems.map((h, idx) => (
                  <tr key={idx}>
                    <td>{new Date(h.decided_at).toLocaleString()}</td>
                    <td>
                      <strong>{h.recommendation_title}</strong>
                    </td>
                    <td>{h.recommendation_category || 'Operations'}</td>
                    <td>
                      <span className={`decision-pill decision-pill--${h.decision}`}>
                        {h.decision === 'approve' ? 'APPROVED' : 'REJECTED'}
                      </span>
                    </td>
                    <td className="comment-cell">
                      {h.comment ? (
                        <span>"{h.comment}"</span>
                      ) : (
                        <span className="text-muted">No comment provided</span>
                      )}
                    </td>
                    <td>
                      <div className="approver-info">
                        <strong>{h.approver_name || 'Management'}</strong>
                        <span className="approver-role">({h.approver_role})</span>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* ── Modal: Approve / Reject Confirmation ── */}
      {selectedRec && (
        <div className="modal-backdrop" onClick={() => setSelectedRec(null)}>
          <div className="modal-dialog" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <div>
                <h3 className="modal-title">
                  {decisionAction === 'approve' ? 'Authorize Initiative' : 'Reject Initiative'}
                </h3>
                <p className="modal-sub">
                  Recording decision for: <strong>{selectedRec.title}</strong>
                </p>
              </div>
              <button className="modal-close-btn" onClick={() => setSelectedRec(null)}>
                ✕
              </button>
            </div>

            <div className="modal-body">
              <div
                className={`decision-callout ${
                  decisionAction === 'approve'
                    ? 'decision-callout--approve'
                    : 'decision-callout--reject'
                }`}
              >
                {decisionAction === 'approve' ? (
                  <p>
                    ⚡ Approving this recommendation will mark it as <code>approved_for_execution</code>{' '}
                    and dispatch simulated operational work orders to retail inventory &amp; ERP systems.
                  </p>
                ) : (
                  <p>
                    🛑 Rejecting this initiative will archive the recommendation as{' '}
                    <code>rejected_by_management</code> and cancel all related operational dispatches.
                  </p>
                )}
              </div>

              <div className="form-group" style={{ marginTop: '16px' }}>
                <label className="form-label" htmlFor="decision-comment">
                  Managerial Rationale / Comment (Optional):
                </label>
                <textarea
                  id="decision-comment"
                  rows={3}
                  className="form-input form-textarea"
                  placeholder="Explain why this initiative is approved or rejected for audit records..."
                  value={decisionComment}
                  onChange={(e) => setDecisionComment(e.target.value)}
                />
              </div>
            </div>

            <div className="modal-footer">
              <button
                type="button"
                className="btn btn--secondary"
                onClick={() => setSelectedRec(null)}
                disabled={submitting}
              >
                Cancel
              </button>
              <button
                type="button"
                className={`btn ${
                  decisionAction === 'approve' ? 'btn--primary' : 'btn--danger'
                }`}
                onClick={handleSubmitDecision}
                disabled={submitting}
              >
                {submitting ? (
                  <>
                    <span className="spinner" /> Recording...
                  </>
                ) : decisionAction === 'approve' ? (
                  'Confirm & Authorize Execution'
                ) : (
                  'Confirm Rejection'
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
