/**
 * src/pages/History.jsx
 * ─────────────────────
 * Multi-Agent Analysis Execution History & Audit Log (Module 13.5).
 */

import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import { getAnalysisHistoryApi } from '@/api/analysis';
import { downloadPdfReportApi } from '@/api/reports';

export default function History() {
  const [runs, setRuns] = useState([]);
  const [loading, setLoading] = useState(true);
  const [downloadingId, setDownloadingId] = useState(null);
  const navigate = useNavigate();

  const loadHistory = async () => {
    setLoading(true);
    try {
      const data = await getAnalysisHistoryApi();
      setRuns(data || []);
    } catch {
      toast.error('Failed to load analysis history.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadHistory();
  }, []);

  const handleDownloadPdf = async (analysisId) => {
    setDownloadingId(analysisId);
    try {
      await downloadPdfReportApi(analysisId);
      toast.success('Official PDF Report downloaded!');
    } catch {
      toast.error('Could not download PDF. Verify analysis was completed.');
    } finally {
      setDownloadingId(null);
    }
  };

  return (
    <div className="page-wrapper history-page">
      <div className="page-header">
        <h2 className="page-header__title">Analysis Execution History</h2>
        <p className="page-header__sub">
          Complete chronological ledger of all multi-agent intelligence executions and verified report generations.
        </p>
      </div>

      <div className="card">
        <div className="inventory-header">
          <h3 className="inventory-title">Past Intelligence Analyses</h3>
          <button className="btn btn--secondary btn--sm" onClick={loadHistory} disabled={loading}>
            ↻ Refresh
          </button>
        </div>

        {loading ? (
          <div className="table-loading">
            <div className="spinner spinner--lg" />
            <p className="loading-text">Loading historical records...</p>
          </div>
        ) : runs.length === 0 ? (
          <div className="table-empty">
            <span className="table-empty__icon">🔬</span>
            <p className="table-empty__title">No Analysis Runs Found</p>
            <p className="table-empty__sub">Launch your first 6-agent analysis run to build audit history.</p>
            <button
              className="btn btn--primary"
              style={{ marginTop: '12px' }}
              onClick={() => navigate('/analysis')}
            >
              🚀 Launch Analysis
            </button>
          </div>
        ) : (
          <div className="table-responsive">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Analysis Run</th>
                  <th>Dataset Target</th>
                  <th>Status</th>
                  <th>Duration</th>
                  <th>Started At</th>
                  <th>Completed At</th>
                  <th style={{ textAlign: 'right' }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {runs.map((run) => (
                  <tr key={run.id}>
                    <td>
                      <div className="dataset-cell-name">
                        <span className="file-icon">🔬</span>
                        <code>{run.id.slice(0, 8)}</code>
                      </div>
                    </td>
                    <td>{run.dataset_name || run.dataset_id?.slice(0, 8) || 'Retail Dataset'}</td>
                    <td>
                      <span className={`status-pill status-pill--${run.status}`}>
                        {run.status.replace('_', ' ')}
                      </span>
                    </td>
                    <td>{run.duration_seconds ? `${run.duration_seconds.toFixed(1)}s` : '—'}</td>
                    <td>{new Date(run.started_at).toLocaleString()}</td>
                    <td>{run.completed_at ? new Date(run.completed_at).toLocaleString() : 'In Progress'}</td>
                    <td style={{ textAlign: 'right' }}>
                      <div className="action-buttons-group">
                        <button
                          className="btn-action"
                          onClick={() => navigate('/analysis')}
                          title="Open in Pipeline Viewer"
                        >
                          👁️ Inspect
                        </button>
                        {run.status === 'completed' && (
                          <button
                            className="btn-action"
                            style={{ color: 'var(--color-primary)' }}
                            onClick={() => handleDownloadPdf(run.id)}
                            disabled={downloadingId === run.id}
                            title="Download PDF Dossier"
                          >
                            {downloadingId === run.id ? '⏳' : '📥 PDF'}
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
