/**
 * src/pages/Reports.jsx
 * ─────────────────────
 * Reports Inventory & PDF Dossier Download Center (Module 13.4).
 *
 * Consumes GET /reports and GET /reports/{id}/pdf.
 */

import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import { listReportsApi, downloadPdfReportApi } from '@/api/reports';

export default function Reports() {
  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(true);
  const [downloadingId, setDownloadingId] = useState(null);
  const navigate = useNavigate();

  const loadReports = async () => {
    setLoading(true);
    try {
      const res = await listReportsApi();
      setReports(res.items || []);
    } catch {
      toast.error('Failed to load published reports.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadReports();
  }, []);

  const handleDownload = async (analysisId, title) => {
    setDownloadingId(analysisId);
    try {
      const safeTitle = (title || 'Report').replace(/[^a-zA-Z0-9_-]/g, '_');
      await downloadPdfReportApi(analysisId, `${safeTitle}.pdf`);
      toast.success('Official PDF report downloaded successfully!');
    } catch {
      toast.error('Could not download PDF. Verify analysis status.');
    } finally {
      setDownloadingId(null);
    }
  };

  return (
    <div className="page-wrapper">
      <div className="page-header">
        <h2 className="page-header__title">Verified BI Reports Archive</h2>
        <p className="page-header__sub">
          Official intelligence dossiers produced after multi-agent consensus and automated numerical verification.
        </p>
      </div>

      <div className="card">
        <div className="inventory-header">
          <h3 className="inventory-title">Published Intelligence Reports</h3>
          <button className="btn btn--secondary btn--sm" onClick={loadReports} disabled={loading}>
            ↻ Refresh
          </button>
        </div>

        {loading ? (
          <div className="table-loading">
            <div className="spinner spinner--lg" />
            <p className="loading-text">Loading verified reports...</p>
          </div>
        ) : reports.length === 0 ? (
          <div className="table-empty">
            <span className="table-empty__icon">📄</span>
            <p className="table-empty__title">No Verified Reports Yet</p>
            <p className="table-empty__sub">
              Execute a Multi-Agent Analysis from the Analysis workspace to generate your first audit-verified report.
            </p>
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
                  <th>Report Title</th>
                  <th>Dataset Source</th>
                  <th>Verification Status</th>
                  <th>Generated Date</th>
                  <th style={{ textAlign: 'right' }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {reports.map((rep) => (
                  <tr key={rep.report_id}>
                    <td>
                      <div className="dataset-cell-name">
                        <span className="file-icon">📋</span>
                        <strong className="file-title">{rep.title}</strong>
                      </div>
                    </td>
                    <td>{rep.dataset_name}</td>
                    <td>
                      <span className={`ver-badge ver-badge--${rep.verification_status?.toLowerCase()}`}>
                        🛡️ {rep.verification_status?.toUpperCase()}
                      </span>
                    </td>
                    <td>{new Date(rep.created_at).toLocaleDateString()}</td>
                    <td style={{ textAlign: 'right' }}>
                      <div className="action-buttons-group">
                        <button
                          className="btn-action"
                          onClick={() => navigate('/analysis')}
                          title="Inspect Pipeline & Recommendations"
                        >
                          👁️ View Dossier
                        </button>
                        <button
                          className="btn-action"
                          style={{ color: 'var(--color-primary)', fontWeight: 600 }}
                          onClick={() => handleDownload(rep.analysis_id, rep.title)}
                          disabled={downloadingId === rep.analysis_id}
                          title="Download Official PDF"
                        >
                          {downloadingId === rep.analysis_id ? '⏳' : '📥 PDF'}
                        </button>
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
