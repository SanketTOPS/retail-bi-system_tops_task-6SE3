/**
 * src/api/profile.js
 * ──────────────────
 * Business Profile API clients.
 */

import api from './axiosInstance';

/**
 * Fetch the authenticated user's business profile.
 * Returns profile data, or null if 404 (no profile created yet).
 */
export async function getProfileApi() {
  try {
    const res = await api.get('/profile');
    return res.data.data ?? res.data;
  } catch (err) {
    if (err.response?.status === 404) {
      return null;
    }
    throw err;
  }
}

/**
 * Create a new business profile.
 */
export async function createProfileApi(profileData) {
  const res = await api.post('/profile', profileData);
  return res.data.data ?? res.data;
}

/**
 * Update an existing business profile.
 */
export async function updateProfileApi(profileData) {
  const res = await api.put('/profile', profileData);
  return res.data.data ?? res.data;
}

/**
 * List all company profiles (Admin only).
 */
export async function listAllProfilesApi(skip = 0, limit = 50) {
  const res = await api.get('/profile/all', { params: { skip, limit } });
  return res.data.data ?? res.data;
}
