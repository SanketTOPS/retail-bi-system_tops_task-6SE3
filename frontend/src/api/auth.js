/**
 * src/api/auth.js
 * ───────────────
 * Authentication API calls — thin wrappers around axiosInstance.
 *
 * All functions return the `data` field of the response body
 * (FastAPI always wraps responses as { success, data, message }).
 *
 * Why separate from AuthContext?
 *   AuthContext manages React state (user, token, loading).
 *   auth.js manages HTTP transport. Separation keeps both files testable
 *   in isolation and follows the Repository pattern for API access.
 */

import api from './axiosInstance';

/**
 * Login with email + password.
 * Returns { access_token, token_type, user: { id, email, full_name, role } }
 */
export async function loginApi({ email, password }) {
  // FastAPI OAuth2 form expects x-www-form-urlencoded, not JSON
  const form = new URLSearchParams({ username: email, password });
  const res = await api.post('/auth/login', form, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  });
  return res.data.data ?? res.data;
}

/**
 * Register a new user.
 * Returns the created user object.
 */
export async function registerApi({ full_name, email, password }) {
  const res = await api.post('/auth/register', { full_name, email, password });
  return res.data.data ?? res.data;
}

/**
 * Get the currently authenticated user's profile.
 * Used to hydrate AuthContext on page refresh (token still valid).
 */
export async function getMeApi() {
  const res = await api.get('/auth/me');
  return res.data.data ?? res.data;
}

/**
 * Change current user's password.
 */
export async function changePasswordApi({ current_password, new_password }) {
  const res = await api.post('/auth/change-password', {
    current_password,
    new_password,
  });
  return res.data;
}
