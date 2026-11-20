/**
 * src/pages/Datasets.jsx
 * ──────────────────────
 * Dataset Ingestion, Data Quality Audit & Management Page.
 *
 * Capabilities:
 *  - Drag-and-drop Excel (.xlsx) file upload with real-time percentage progress bar.
 *  - Automatic display of the Pandas cleaning summary returned by the backend:
 *    date range filtering (May 1 - Oct 31 2026), median imputation, duplicate pruning,
 *    and foreign-key orphan record elimination across 6 retail sheets.
 *  - Dataset table listing all ingested datasets with status pills, row counts, and timestamps.
 *  - Interactive sample preview modal showing live table records across all 6 entities.
 *  - Delete dataset action with confirmation and cascading database cleanup.
 */

import React, { useEffect, useRef, useState } from 'react';
import toast from 'react-hot-toast';
import {
  listDatasetsApi,
  uploadDatasetApi,
  previewDatasetApi,
  deleteDatasetApi,
  getDatasetApi,
} from '@/api/datasets';

function formatBytes(bytes, decimals = 2) {
  if (!bytes || bytes === 0) return '0 B';
  const k = 1024;
  const dm = decimals < 0 ? 0 : decimals;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(dm))} ${sizes[i]}`;
}

function formatDate(isoStr) {
  if (!isoStr) return '—';
  try {
    return new Date(isoStr).toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return isoStr;
  }
}

export default function Datasets() {
  // ── States ─────────────────────────────────────────────────────────────────
  const [datasets, setDatasets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Upload states
  const [dragActive, setDragActive] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);

  // Active cleaning summary (from latest upload or selected dataset)
  const [cleaningSummary, setCleaningSummary] = useState(null);
  const [activeDatasetName, setActiveDatasetName] = useState('');

  // Preview modal states
  const [previewModalOpen, setPreviewModalOpen] = useState(false);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewData, setPreviewData] = useState(null);
  const [activePreviewTab, setActivePreviewTab] = useState('');

  const fileInputRef = useRef(null);

  // ── 1. Fetch Datasets ──────────────────────────────────────────────────────
  const loadDatasets = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await listDatasetsApi();
      setDatasets(data || []);
    } catch (err) {
      setError('Failed to load datasets. Please check backend connection.');
      toast.error('Could not load dataset inventory.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDatasets();
  }, []);

  // ── 2. Drag & Drop Handlers ────────────────────────────────────────────────
  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileSelected(e.dataTransfer.files[0]);
    }
  };

  const handleFileInputChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      handleFileSelected(e.target.files[0]);
    }
  };

  const handleFileSelected = (file) => {
    if (!file.name.endsWith('.xlsx')) {
      toast.error('Please select an Excel workbook (.xlsx) containing the 6 required retail sheets.');
      return;
    }
    setSelectedFile(file);
    setUploadProgress(0);
  };

  // ── 3. Upload Execution ────────────────────────────────────────────────────
  const handleUpload = async () => {
    if (!selectedFile) return;

    setUploading(true);
    setUploadProgress(1);

    try {
      const result = await uploadDatasetApi(selectedFile, (percent) => {
        setUploadProgress(percent);
      });

      toast.success(result.message || 'Dataset uploaded and ingested successfully!');
      setSelectedFile(null);
      if (fileInputRef.current) fileInputRef.current.value = '';

      // Set cleaning summary to display immediately
      const ds = result.dataset;
      if (ds && ds.cleaning_summary) {
        setCleaningSummary(ds.cleaning_summary);
        setActiveDatasetName(ds.original_filename);
      }

      // Refresh list
      loadDatasets();
    } catch (err) {
      const errData = err.response?.data;
      const detail = errData?.error?.detail || errData?.detail;
      let msg = 'Dataset upload or validation failed.';
      if (typeof detail === 'string') {
        msg = detail;
      } else if (typeof detail === 'object' && detail?.message) {
        msg = detail.message;
      }
      toast.error(msg, { duration: 6000 });
    } finally {
      setUploading(false);
    }
  };

  // ── 4. View Existing Cleaning Summary ──────────────────────────────────────
  const handleViewCleaning = async (ds) => {
    if (ds.cleaning_summary) {
      setCleaningSummary(ds.cleaning_summary);
      setActiveDatasetName(ds.original_filename);
      window.scrollTo({ top: 380, behavior: 'smooth' });
      return;
    }

    try {
      const full = await getDatasetApi(ds.id);
      if (full.cleaning_summary) {
        setCleaningSummary(full.cleaning_summary);
        setActiveDatasetName(full.original_filename);
        window.scrollTo({ top: 380, behavior: 'smooth' });
      } else {
        toast('No detailed cleaning log available for this dataset.');
      }
    } catch {
      toast.error('Could not load cleaning report.');
    }
  };

  // ── 5. Preview Modal Handlers ──────────────────────────────────────────────
  const handleOpenPreview = async (datasetId, filename) => {
    setPreviewModalOpen(true);
    setPreviewLoading(true);
    setActiveDatasetName(filename);
    try {
      const preview = await previewDatasetApi(datasetId, 5);
      setPreviewData(preview.previews || {});
      const sheets = Object.keys(preview.previews || {});
      if (sheets.length > 0) {
        setActivePreviewTab(sheets[0]);
      }
    } catch {
      toast.error('Failed to load sample preview.');
      setPreviewModalOpen(false);
    } finally {
      setPreviewLoading(false);
    }
  };

  // ── 6. Delete Dataset ──────────────────────────────────────────────────────
  const handleDelete = async (datasetId, filename) => {
    const confirmed = window.confirm(
      `Are you sure you want to delete dataset "${filename}"?\n\nThis will permanently remove the raw file and all records from all 6 retail tables.`
    );
    if (!confirmed) return;

    try {
      await deleteDatasetApi(datasetId);
      toast.success('Dataset deleted successfully.');
      setDatasets((prev) => prev.filter((d) => d.id !== datasetId));
      if (activeDatasetName === filename) {
        setCleaningSummary(null);
      }
    } catch {
      toast.error('Failed to delete dataset.');
    }
  };

  return (
    <div className="page-wrapper">
      {/* Page Header */}
      <div className="page-header">
        <h2 className="page-header__title">Dataset Management & Ingestion</h2>
        <p className="page-header__sub">
          Upload and validate multi-sheet retail workbooks. Every uploaded dataset undergoes deterministic
          cleaning, date boundary enforcement, and orphan record pruning before ingestion.
        </p>
      </div>

      {/* ── Section A: Drag & Drop Upload Zone ── */}
      <div className="card upload-card">
        <div
          className={`dropzone ${dragActive ? 'dropzone--active' : ''} ${selectedFile ? 'dropzone--has-file' : ''}`}
          onDragEnter={handleDrag}
          onDragOver={handleDrag}
          onDragLeave={handleDrag}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".xlsx"
            style={{ display: 'none' }}
            onChange={handleFileInputChange}
          />

          <span className="dropzone__icon">📁</span>

          {selectedFile ? (
            <div className="dropzone__file-info">
              <p className="dropzone__filename">{selectedFile.name}</p>
              <p className="dropzone__filesize">{formatBytes(selectedFile.size)}</p>
              <p className="dropzone__hint">Ready for validation and ingestion. Click or drop to replace.</p>
            </div>
          ) : (
            <div className="dropzone__prompt">
              <p className="dropzone__title">Drag & drop your Excel workbook here, or click to browse</p>
              <p className="dropzone__sub">
                Supports <code>.xlsx</code> with required sheets: Customers, Products, Transactions,
                Transaction_Items, Inventory_Movements, Expenses
              </p>
            </div>
          )}
        </div>

        {/* Upload Progress Bar */}
        {uploading && (
          <div className="upload-progress-container">
            <div className="upload-progress-header">
              <span>Ingesting & Cleaning Dataset...</span>
              <span>{uploadProgress}%</span>
            </div>
            <div className="progress-track">
              <div
                className="progress-bar"
                style={{ width: `${uploadProgress}%` }}
              />
            </div>
          </div>
        )}

        {/* Upload Action Button */}
        {selectedFile && !uploading && (
          <div className="upload-actions">
            <button
              type="button"
              className="btn btn--primary"
              onClick={handleUpload}
            >
              🚀 Ingest Dataset
            </button>
            <button
              type="button"
              className="btn btn--secondary"
              onClick={(e) => {
                e.stopPropagation();
                setSelectedFile(null);
                if (fileInputRef.current) fileInputRef.current.value = '';
              }}
            >
              Clear
            </button>
          </div>
        )}
      </div>

      {/* ── Section B: Data Cleaning & Quality Audit Summary ── */}
      {cleaningSummary && (
        <div className="card cleaning-summary-card">
          <div className="cleaning-summary-header">
            <div>
              <h3 className="cleaning-summary-title">
                Data Quality & Cleaning Report
              </h3>
              <p className="cleaning-summary-sub">
                Audit trail for <strong>{activeDatasetName}</strong> (Normalized Period: {cleaningSummary.dataset_period || '2026-05-01 to 2026-10-31'})
              </p>
            </div>
            <div className="total-rows-badge">
              <span className="total-rows-label">Total Imported</span>
              <span className="total-rows-value">
                {(cleaningSummary.total_rows_imported || 0).toLocaleString()} rows
              </span>
            </div>
          </div>

          {/* Sheet by Sheet Cleaning Breakdown */}
          <div className="cleaning-table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Entity Sheet</th>
                  <th>Raw Rows</th>
                  <th>Final Rows</th>
                  <th>Duplicates Removed</th>
                  <th>Nulls Imputed</th>
                  <th>Period Filtered</th>
                  <th>Orphans Pruned</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(cleaningSummary.sheets || {}).map(([sheetName, stats]) => (
                  <tr key={sheetName}>
                    <td className="font-semibold">{sheetName}</td>
                    <td>{stats.rows_initial?.toLocaleString() ?? '—'}</td>
                    <td className="text-success font-semibold">{stats.rows_final?.toLocaleString() ?? '—'}</td>
                    <td>{stats.duplicates_removed > 0 ? <span className="stat-flag">{stats.duplicates_removed}</span> : '0'}</td>
                    <td>{stats.nulls_handled > 0 ? <span className="stat-flag">{stats.nulls_handled}</span> : '0'}</td>
                    <td>{stats.date_filtered_rows > 0 ? <span className="stat-flag stat-flag--warn">{stats.date_filtered_rows}</span> : '0'}</td>
                    <td>{stats.orphan_rows_dropped > 0 ? <span className="stat-flag stat-flag--danger">{stats.orphan_rows_dropped}</span> : '0'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ── Section C: Dataset Inventory Table ── */}
      <div className="card datasets-inventory-card">
        <div className="inventory-header">
          <h3 className="inventory-title">Ingested Datasets</h3>
          <button
            className="btn btn--secondary btn--sm"
            onClick={loadDatasets}
            disabled={loading}
          >
            ↻ Refresh
          </button>
        </div>

        {loading ? (
          <div className="table-loading">
            <div className="spinner spinner--lg" />
            <p className="loading-text">Loading dataset inventory...</p>
          </div>
        ) : error ? (
          <div className="table-error">
            <p>{error}</p>
            <button className="btn btn--secondary btn--sm" onClick={loadDatasets}>
              Try Again
            </button>
          </div>
        ) : datasets.length === 0 ? (
          <div className="table-empty">
            <span className="table-empty__icon">🗄️</span>
            <p className="table-empty__title">No Datasets Ingested Yet</p>
            <p className="table-empty__sub">
              Upload an Excel workbook above to start multi-agent analysis and business intelligence tracking.
            </p>
          </div>
        ) : (
          <div className="table-responsive">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Dataset Name</th>
                  <th>Size</th>
                  <th>Total Rows</th>
                  <th>Status</th>
                  <th>Ingested At</th>
                  <th style={{ textAlign: 'right' }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {datasets.map((ds) => (
                  <tr key={ds.id}>
                    <td>
                      <div className="dataset-cell-name">
                        <span className="file-icon">📊</span>
                        <span className="file-title">{ds.original_filename}</span>
                      </div>
                    </td>
                    <td>{formatBytes(ds.file_size_bytes)}</td>
                    <td className="font-semibold">{ds.total_rows?.toLocaleString() ?? '—'}</td>
                    <td>
                      <span className={`status-pill status-pill--${ds.status}`}>
                        {ds.status}
                      </span>
                    </td>
                    <td>{formatDate(ds.uploaded_at)}</td>
                    <td style={{ textAlign: 'right' }}>
                      <div className="action-buttons-group">
                        <button
                          className="btn-action"
                          title="View Data Cleaning Report"
                          onClick={() => handleViewCleaning(ds)}
                        >
                          📋 Audit
                        </button>
                        <button
                          className="btn-action"
                          title="Preview Sample Rows"
                          onClick={() => handleOpenPreview(ds.id, ds.original_filename)}
                        >
                          👁️ Preview
                        </button>
                        <button
                          className="btn-action btn-action--danger"
                          title="Delete Dataset"
                          onClick={() => handleDelete(ds.id, ds.original_filename)}
                        >
                          🗑️
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

      {/* ── Section D: Sample Data Preview Modal ── */}
      {previewModalOpen && (
        <div className="modal-backdrop" onClick={() => setPreviewModalOpen(false)}>
          <div
            className="modal-dialog modal-dialog--lg"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="modal-header">
              <div>
                <h3 className="modal-title">Sample Data Preview</h3>
                <p className="modal-sub">Previewing first 5 rows for <strong>{activeDatasetName}</strong></p>
              </div>
              <button
                className="modal-close-btn"
                onClick={() => setPreviewModalOpen(false)}
                aria-label="Close"
              >
                ✕
              </button>
            </div>

            {previewLoading ? (
              <div className="modal-loading">
                <div className="spinner spinner--lg" />
                <p className="loading-text">Fetching sample rows across all tables...</p>
              </div>
            ) : (
              <div className="modal-body">
                {/* Tab Navigation for 6 entities */}
                <div className="tab-nav">
                  {Object.keys(previewData || {}).map((entityKey) => (
                    <button
                      key={entityKey}
                      className={`tab-btn ${activePreviewTab === entityKey ? 'tab-btn--active' : ''}`}
                      onClick={() => setActivePreviewTab(entityKey)}
                    >
                      {entityKey}
                    </button>
                  ))}
                </div>

                {/* Table for Active Tab */}
                <div className="preview-table-container">
                  {(!previewData || !previewData[activePreviewTab] || previewData[activePreviewTab].length === 0) ? (
                    <p className="no-records-msg">No sample records found for this table.</p>
                  ) : (
                    <table className="data-table data-table--compact">
                      <thead>
                        <tr>
                          {Object.keys(previewData[activePreviewTab][0] || {}).map((col) => (
                            <th key={col}>{col}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {previewData[activePreviewTab].map((row, rIdx) => (
                          <tr key={rIdx}>
                            {Object.values(row).map((val, cIdx) => (
                              <td key={cIdx}>
                                {val === null || val === undefined ? (
                                  <span className="null-val">null</span>
                                ) : typeof val === 'object' ? (
                                  JSON.stringify(val)
                                ) : (
                                  String(val)
                                )}
                              </td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  )}
                </div>
              </div>
            )}

            <div className="modal-footer">
              <button
                className="btn btn--secondary"
                onClick={() => setPreviewModalOpen(false)}
              >
                Close Preview
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
