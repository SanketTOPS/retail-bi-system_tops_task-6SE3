/**
 * src/components/ProtectedRoute.jsx
 * ───────────────────────────────────
 * Route guard component for React Router v6.
 *
 * Usage:
 *   <Route element={<ProtectedRoute />}>
 *     <Route path="/dashboard" element={<Dashboard />} />
 *   </Route>
 *
 *   <Route element={<ProtectedRoute allowedRoles={['admin']} />}>
 *     <Route path="/admin" element={<AdminPanel />} />
 *   </Route>
 *
 * Behaviour:
 *   1. While AuthContext is still loading (hydrating from localStorage) →
 *      show a full-screen spinner to prevent a flash of the login page.
 *   2. Not authenticated → redirect to /login (preserving `from` for
 *      post-login redirect).
 *   3. Authenticated but wrong role → redirect to /unauthorized (403 page).
 *   4. All checks pass → render <Outlet /> (child routes).
 *
 * Design: Why not check roles in each page component?
 *   Centralising the guard here keeps page components clean (pure business UI).
 *   Adding a new protected route only requires wrapping it in <ProtectedRoute>,
 *   not adding auth boilerplate to every page. It also makes role changes
 *   easy — update one place, all routes pick it up.
 */

import React from 'react';
import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { useAuth } from '@/context/AuthContext';

export default function ProtectedRoute({ allowedRoles = [] }) {
  const { isAuthenticated, isLoading, role } = useAuth();
  const location = useLocation();

  // ── 1. Still hydrating session from localStorage ──────────────────────────
  if (isLoading) {
    return (
      <div className="full-screen-center">
        <div className="spinner spinner--lg" />
        <p className="loading-text">Loading session…</p>
      </div>
    );
  }

  // ── 2. Not logged in → send to login with return path ────────────────────
  if (!isAuthenticated) {
    return (
      <Navigate
        to="/login"
        state={{ from: location }}
        replace
      />
    );
  }

  // ── 3. Role check (skip if no roles specified → any authenticated user) ───
  if (allowedRoles.length > 0 && !allowedRoles.includes(role)) {
    return <Navigate to="/unauthorized" replace />;
  }

  // ── 4. Authorised → render child routes ──────────────────────────────────
  return <Outlet />;
}
