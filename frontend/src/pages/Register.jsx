/**
 * src/pages/Register.jsx
 * ───────────────────────
 * User registration page — public route.
 *
 * Form fields:    full_name, email, password, confirmPassword
 * Validation:
 *   - All fields required
 *   - Email format check (regex)
 *   - Password ≥ 8 characters, must contain letter + digit
 *   - Passwords must match
 *
 * On success:
 *   AuthContext.register() auto-logs the user in and navigates to /dashboard.
 *
 * Role note:
 *   The first user registered automatically becomes 'admin' (enforced by the
 *   backend seed rule in auth_service.py). Subsequent users are 'analyst' by
 *   default; an admin can promote them via the Admin Panel.
 */

import React, { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import { useAuth } from '@/context/AuthContext';

// ── Validation ───────────────────────────────────────────────────────────────
function validate({ full_name, email, password, confirmPassword }) {
  const errors = {};

  if (!full_name.trim())
    errors.full_name = 'Full name is required.';

  if (!email.trim())
    errors.email = 'Email is required.';
  else if (!/\S+@\S+\.\S+/.test(email))
    errors.email = 'Enter a valid email address.';

  if (!password)
    errors.password = 'Password is required.';
  else if (password.length < 8)
    errors.password = 'Password must be at least 8 characters.';
  else if (!/[a-zA-Z]/.test(password) || !/\d/.test(password))
    errors.password = 'Password must contain at least one letter and one number.';

  if (!confirmPassword)
    errors.confirmPassword = 'Please confirm your password.';
  else if (password !== confirmPassword)
    errors.confirmPassword = 'Passwords do not match.';

  return errors;
}

// ── Password strength ─────────────────────────────────────────────────────────
function getStrength(pw) {
  if (!pw) return { level: 0, label: '', color: '#e5e7eb' };
  let score = 0;
  if (pw.length >= 8)              score++;
  if (pw.length >= 12)             score++;
  if (/[A-Z]/.test(pw))           score++;
  if (/\d/.test(pw))              score++;
  if (/[^A-Za-z0-9]/.test(pw))   score++;
  const levels = [
    { label: '',         color: '#e5e7eb' },
    { label: 'Weak',     color: '#ef4444' },
    { label: 'Fair',     color: '#f97316' },
    { label: 'Good',     color: '#eab308' },
    { label: 'Strong',   color: '#22c55e' },
    { label: 'Excellent',color: '#16a34a' },
  ];
  return { level: score, ...levels[score] };
}

// ── Component ─────────────────────────────────────────────────────────────────
export default function Register() {
  const { register, isAuthenticated } = useAuth();
  const navigate = useNavigate();

  const [form, setForm] = useState({
    full_name: '', email: '', password: '', confirmPassword: '',
  });
  const [errors,  setErrors]  = useState({});
  const [loading, setLoading] = useState(false);
  const [showPw,  setShowPw]  = useState(false);

  const strength = getStrength(form.password);

  useEffect(() => {
    if (isAuthenticated) navigate('/dashboard', { replace: true });
  }, [isAuthenticated, navigate]);

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
      await register({
        full_name: form.full_name.trim(),
        email:     form.email.trim(),
        password:  form.password,
      });
      // AuthContext.register() auto-logs in and navigates to /dashboard
    } catch (err) {
      const detail = err?.response?.data?.detail;
      const msg =
        typeof detail === 'string'
          ? detail
          : err?.response?.data?.message ?? 'Registration failed. Please try again.';
      toast.error(msg);
      if (msg.toLowerCase().includes('email')) {
        setErrors({ email: msg });
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="auth-page">
      <div className="auth-card auth-card--wide">
        {/* Brand */}
        <div className="auth-card__brand">
          <span className="auth-card__logo">📈</span>
          <h1 className="auth-card__title">Create Account</h1>
          <p className="auth-card__subtitle">Join the Retail BI System</p>
        </div>

        {/* Form */}
        <form className="auth-form" onSubmit={handleSubmit} noValidate>
          {/* Full name */}
          <div className={`form-group ${errors.full_name ? 'form-group--error' : ''}`}>
            <label className="form-label" htmlFor="full_name">Full name</label>
            <input
              id="full_name"
              name="full_name"
              type="text"
              autoComplete="name"
              className="form-input"
              placeholder="Jane Smith"
              value={form.full_name}
              onChange={handleChange}
              disabled={loading}
            />
            {errors.full_name && (
              <p className="form-error" role="alert">{errors.full_name}</p>
            )}
          </div>

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
            />
            {errors.email && (
              <p className="form-error" role="alert">{errors.email}</p>
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
                autoComplete="new-password"
                className="form-input form-input--pw"
                placeholder="Min. 8 characters"
                value={form.password}
                onChange={handleChange}
                disabled={loading}
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

            {/* Strength bar */}
            {form.password && (
              <div className="pw-strength">
                <div
                  className="pw-strength__bar"
                  style={{
                    width: `${(strength.level / 5) * 100}%`,
                    backgroundColor: strength.color,
                  }}
                />
                <span className="pw-strength__label" style={{ color: strength.color }}>
                  {strength.label}
                </span>
              </div>
            )}
            {errors.password && (
              <p className="form-error" role="alert">{errors.password}</p>
            )}
          </div>

          {/* Confirm password */}
          <div className={`form-group ${errors.confirmPassword ? 'form-group--error' : ''}`}>
            <label className="form-label" htmlFor="confirmPassword">Confirm password</label>
            <input
              id="confirmPassword"
              name="confirmPassword"
              type={showPw ? 'text' : 'password'}
              autoComplete="new-password"
              className="form-input"
              placeholder="Re-enter password"
              value={form.confirmPassword}
              onChange={handleChange}
              disabled={loading}
            />
            {errors.confirmPassword && (
              <p className="form-error" role="alert">{errors.confirmPassword}</p>
            )}
          </div>

          {/* Note about first user */}
          <p className="auth-form__note">
            💡 The first registered user automatically becomes an <strong>Admin</strong>.
          </p>

          {/* Submit */}
          <button
            type="submit"
            className="btn btn--primary btn--full"
            disabled={loading}
          >
            {loading ? <span className="spinner" /> : 'Create Account'}
          </button>
        </form>

        <p className="auth-card__switch">
          Already have an account?{' '}
          <Link to="/login" className="auth-card__link">Sign in</Link>
        </p>
      </div>
    </div>
  );
}
