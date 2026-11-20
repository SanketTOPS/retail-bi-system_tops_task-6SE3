/**
 * src/api/datasets.js
 * ───────────────────
 * Dataset Upload, Ingestion, Preview, and Deletion API clients.
 */

import api from './axiosInstance';

/**
 * List accessible datasets with pagination.
 */
export async function listDatasetsApi(skip = 0, limit = 50) {
  const res = await api.get('/datasets', { params: { skip, limit } });
  return res.data.data ?? res.data;
}

/**
 * Get detailed dataset metadata, row counts, and cleaning summary.
 */
export async function getDatasetApi(datasetId) {
  const res = await api.get(`/datasets/${datasetId}`);
  return res.data.data ?? res.data;
}

/**
 * Upload an Excel dataset file (.xlsx) with progress tracking.
 *
 * @param {File} file - Excel file object
 * @param {Function} onProgress - Callback with percentage integer (0-100)
 */
export async function uploadDatasetApi(file, onProgress) {
  const formData = new FormData();
  formData.append('file', file);

  const res = await api.post('/datasets/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
    onUploadProgress: (progressEvent) => {
      if (progressEvent.total && onProgress) {
        const percent = Math.round((progressEvent.loaded * 100) / progressEvent.total);
        onProgress(percent);
      }
    },
  });

  return res.data.data ?? res.data;
}

/**
 * Preview sample records across all retail tables.
 */
export async function previewDatasetApi(datasetId, limit = 5) {
  const res = await api.get(`/datasets/${datasetId}/preview`, {
    params: { limit },
  });
  return res.data.data ?? res.data;
}

/**
 * Delete a dataset and its cascading database records.
 */
export async function deleteDatasetApi(datasetId) {
  const res = await api.delete(`/datasets/${datasetId}`);
  return res.data.data ?? res.data;
}
