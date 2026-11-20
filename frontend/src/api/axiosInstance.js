/**
 * src/api/axiosInstance.js
 * ────────────────────────
 * Singleton Axios instance shared across the entire application.
 *
 * Responsibilities:
 *  1. Set `baseURL` from VITE_API_URL env variable (falls back to /api/v1
 *     which the Vite dev proxy forwards to FastAPI).
 *  2. REQUEST interceptor — attach the JWT `Authorization: Bearer <token>`
 *     header to every outgoing request automatically, so callers never
 *     need to pass the token manually.
 *  3. RESPONSE interceptor — if the server returns HTTP 401 (Unauthorized),
 *     clear local storage and redirect to /login (auto-logout). This handles
 *     expired tokens without each API call needing its own error handler.
 *
 * Design: Why a singleton instead of calling axios directly?
 *  - Centralised auth header injection (DRY — one place to change token key).
 *  - Centralised error handling (401 auto-logout, global error logging).
 *  - Easy to mock in tests (replace one module, not dozens of axios calls).
 *  - Consistent `Content-Type: application/json` on all requests.
 *
 * Token storage: localStorage is used for simplicity. For production,
 * consider httpOnly cookies (immune to XSS) with a CSRF token header.
 */

import axios from 'axios';

// ── Create instance ──────────────────────────────────────────────────────────
const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api/v1',
  timeout: 30_000,                // 30 s — LLM calls can be slow
  headers: {
    'Content-Type': 'application/json',
  },
});

// ── Token helpers ────────────────────────────────────────────────────────────
export const TOKEN_KEY = 'retail_bi_token';
export const USER_KEY  = 'retail_bi_user';

export const getToken  = ()        => localStorage.getItem(TOKEN_KEY);
export const setToken  = (token)   => localStorage.setItem(TOKEN_KEY, token);
export const clearAuth = ()        => {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
};

// ── REQUEST interceptor — attach JWT ────────────────────────────────────────
api.interceptors.request.use(
  (config) => {
    const token = getToken();
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error),
);

// ── RESPONSE interceptor — handle 401 auto-logout ───────────────────────────
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Token expired or revoked — clear local state and force re-login.
      // We dispatch a custom event so AuthContext can react without a direct
      // dependency loop (axiosInstance doesn't import AuthContext).
      clearAuth();
      window.dispatchEvent(new CustomEvent('auth:logout'));

      // Only redirect if we're not already on the login page
      if (!window.location.pathname.startsWith('/login')) {
        window.location.replace('/login?reason=session_expired');
      }
    }
    return Promise.reject(error);
  },
);

export default api;
