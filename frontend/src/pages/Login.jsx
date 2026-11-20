/**
 * src/pages/Login.jsx
 * ────────────────────
 * Login page — public route, redirects to /dashboard on success.
 *
 * Form fields:   email, password
 * Validation:    client-side (empty check, email format, min length)
 *                server-side errors surfaced as toast + field highlight
 *
 * Auth flow:
 *  1. User submits email + password.
 *  2. loginApi() sends POST /api/v1/auth/login with form-encoded body.
 *  3. Server returns { access_token, user }.
 *  4. AuthContext.login() stores token in localStorage, fetches full user
 *     profile via GET /auth/me, sets React state, navigates to /dashboard.
 *
 * Session-expired redirect:
 *  If the user arrives with ?reason=session_expired (set by axiosInstance
 *  on 401), an informational toast is shown before the form.
 */

import React, { useEffect, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import { useAuth } from '@/context/AuthContext';

// ── Validation ───────────────────────────────────────────────────────────────
function validate({ email, password }) {
  const errors = {};
  if (!email.trim())                              errors.email    = 'Email is required.';
  else if (!/\S+@\S+\.\S+/.test(email))          errors.email    = 'Enter a valid email.';
  if (!password)                                  errors.password = 'Password is required.';
  else if (password.length < 6)                   errors.password = 'Password must be ≥ 6 characters.';
  return errors;
}

// ── Component ────────────────────────────────────────────────────────────────
export default function Login() {
  const { login, isAuthenticated } = useAuth();
  const navigate  = useNavigate();
  const location  = useLocation();

  const [form,    setForm]    = useState({ email: '', password: '' });
  const [errors,  setErrors]  = useState({});
  const [loading, setLoading] = useState(false);
  const [showPw,  setShowPw]  = useState(false);

  // Redirect if already logged in
  useEffect(() => {
    if (isAuthenticated) navigate('/dashboard', { replace: true });
  }, [isAuthenticated, navigate]);

  // Show session-expired notice
  useEffect(() => {
    const params = new URLSearchParams(location.search);
    if (params.get('reason') === 'session_expired') {
      toast.error('Your session expired. Please log in again.', { id: 'session-expired' });
    }
  }, [location.search]);

  function handleChange(e) {
    const { name, value } = e.target;
    setForm((f) => ({ ...f, [name]: value }));
    if (errors[name]) setErrors((er) => ({ ...er, [name]: '' }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    const errs = validate(form);
    if (Object.keys(errs).length) { setErrors(errs); return; }

    setLoading(true);
    try {
      await login(form.email.trim(), form.password);
      // AuthContext.login() calls navigate('/dashboard') on success
    } catch (err) {
      const msg =
        err?.response?.data?.detail ??
        err?.response?.data?.message ??
        'Login failed. Check your credentials.';
      toast.error(msg);
      setErrors({ password: msg });
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="auth-page">
      <div className="auth-card">
        {/* Brand */}
        <div className="auth-card__brand">
          <span className="auth-card__logo">📈</span>
          <h1 className="auth-card__title">Retail BI System</h1>
          <p className="auth-card__subtitle">Sign in to your account</p>
        </div>

        {/* Form */}
        <form className="auth-form" onSubmit={handleSubmit} noValidate>
          {/* Email */}
          <div className={`form-group ${errors.email ? 'form-group--error' : ''}`}>
            <label className="form-label" htmlFor="email">Email address</label>
            <input
              id="email"
              name="email"
              type="email"
              autoComplete="email"
              className="form-input"
              placeholder="you@company.com"
              value={form.email}
              onChange={handleChange}
              disabled={loading}
              aria-describedby={errors.email ? 'email-err' : undefined}
            />
            {errors.email && (
              <p id="email-err" className="form-error" role="alert">{errors.email}</p>
            )}
          </div>

          {/* Password */}
          <div className={`form-group ${errors.password ? 'form-group--error' : ''}`}>
            <label className="form-label" htmlFor="password">Password</label>
            <div className="form-input-wrap">
              <input
                id="password"
                name="password"
                type={showPw ? 'text' : 'password'}
                autoComplete="current-password"
                className="form-input form-input--pw"
                placeholder="••••••••"
                value={form.password}
                onChange={handleChange}
                disabled={loading}
                aria-describedby={errors.password ? 'pw-err' : undefined}
              />
              <button
                type="button"
                className="form-pw-toggle"
                onClick={() => setShowPw((v) => !v)}
                aria-label={showPw ? 'Hide password' : 'Show password'}
              >
                {showPw ? '🙈' : '👁️'}
              </button>
            </div>
            {errors.password && (
              <p id="pw-err" className="form-error" role="alert">{errors.password}</p>
            )}
          </div>

          {/* Submit */}
          <button
            type="submit"
            className="btn btn--primary btn--full"
            disabled={loading}
          >
            {loading ? <span className="spinner" /> : 'Sign In'}
          </button>
        </form>

        {/* Register link */}
        <p className="auth-card__switch">
          Don't have an account?{' '}
          <Link to="/register" className="auth-card__link">
            Create one
          </Link>
        </p>
      </div>
    </div>
  );
}
