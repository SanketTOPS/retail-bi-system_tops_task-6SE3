/**
 * src/api/reports.js
 * ──────────────────
 * Report Listing, Retrieval, and PDF Download API client.
 */

import api from './axiosInstance';

/**
 * List all generated BI reports.
 */
export async function listReportsApi(skip = 0, limit = 20) {
  const res = await api.get('/reports', { params: { skip, limit } });
  return res.data.data ?? res.data;
}

/**
 * Get structured report JSON for an analysis.
 */
export async function getReportJsonApi(analysisId) {
  const res = await api.get(`/reports/${analysisId}`);
  return res.data.data ?? res.data;
}

/**
 * Download generated ReportLab PDF using authenticated Axios blob stream.
 * Automatically initiates browser download with proper filename.
 */
export async function downloadPdfReportApi(analysisId, defaultFilename = 'Retail_BI_Report.pdf') {
  const response = await api.get(`/reports/${analysisId}/pdf`, {
    responseType: 'blob',
  });

  // Extract filename from Content-Disposition header if available
  let filename = defaultFilename;
  const disposition = response.headers['content-disposition'];
  if (disposition && disposition.indexOf('filename=') !== -1) {
    const filenameRegex = /filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/;
    const matches = filenameRegex.exec(disposition);
    if (matches != null && matches[1]) {
      filename = matches[1].replace(/['"]/g, '');
    }
  }

  // Create temporary blob URL and click hidden anchor tag
  const blob = new Blob([response.data], { type: 'application/pdf' });
  const blobUrl = window.URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = blobUrl;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  window.URL.revokeObjectURL(blobUrl);

  return true;
}
