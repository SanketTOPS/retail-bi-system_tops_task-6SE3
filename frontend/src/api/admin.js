/**
 * src/api/admin.js
 * ────────────────
 * Platform Administration API Client (Admin Role Only).
 */

import api from './axiosInstance';

/**
 * Fetch platform-wide health metrics & domain statistics.
 */
export async function getAdminStatsApi() {
  const res = await api.get('/admin/stats');
  return res.data.data ?? res.data;
}

/**
 * List all users with role/status filters and search.
 */
export async function getAdminUsersApi({ skip = 0, limit = 50, role, is_active, search } = {}) {
  const res = await api.get('/admin/users', {
    params: { skip, limit, role, is_active, search },
  });
  return res.data.data ?? res.data;
}

/**
 * Change a user's RBAC role (admin, manager, analyst).
 */
export async function patchUserRoleApi(userId, role) {
  const res = await api.patch(`/admin/users/${userId}/role`, { role });
  return res.data.data ?? res.data;
}

/**
 * Activate or deactivate a user account.
 */
export async function patchUserStatusApi(userId, isActive) {
  const res = await api.patch(`/admin/users/${userId}/status`, { is_active: isActive });
  return res.data.data ?? res.data;
}

/**
 * List all analyses across all users with filters.
 */
export async function getAdminAnalysesApi({ skip = 0, limit = 50, status, user_id, dataset_id } = {}) {
  const res = await api.get('/admin/analyses', {
    params: { skip, limit, status, user_id, dataset_id },
  });
  return res.data.data ?? res.data;
}

/**
 * List all generated reports across all users.
 */
export async function getAdminReportsApi({ skip = 0, limit = 50, verification_status } = {}) {
  const res = await api.get('/admin/reports', {
    params: { skip, limit, verification_status },
  });
  return res.data.data ?? res.data;
}
