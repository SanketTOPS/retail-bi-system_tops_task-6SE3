/**
 * src/App.jsx
 * ───────────
 * Root Application Router & Notification Toaster Configuration.
 */

import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';

import { AuthProvider } from '@/context/AuthContext';
import ProtectedRoute from '@/components/ProtectedRoute';
import Layout from '@/components/layout/Layout';

// Pages
import Login from '@/pages/Login';
import Register from '@/pages/Register';
import Dashboard from '@/pages/Dashboard';
import Datasets from '@/pages/Datasets';
import Analysis from '@/pages/Analysis';
import History from '@/pages/History';
import Reports from '@/pages/Reports';
import Approvals from '@/pages/Approvals';
import Chat from '@/pages/Chat';
import Profile from '@/pages/Profile';
import Admin from '@/pages/Admin';
import Unauthorized from '@/pages/Unauthorized';
import NotFound from '@/pages/NotFound';

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Toaster
          position="top-right"
          toastOptions={{
            duration: 4000,
            style: {
              background: '#0f172a',
              color: '#ffffff',
              fontSize: '14px',
              borderRadius: '8px',
              padding: '12px 16px',
            },
            success: {
              iconTheme: {
                primary: '#22c55e',
                secondary: '#ffffff',
              },
            },
            error: {
              iconTheme: {
                primary: '#ef4444',
                secondary: '#ffffff',
              },
            },
          }}
        />

        <Routes>
          {/* Public Routes */}
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/unauthorized" element={<Unauthorized />} />

          {/* Protected Routes inside Common App Layout */}
          <Route element={<ProtectedRoute />}>
            <Route element={<Layout />}>
              <Route path="/" element={<Navigate to="/dashboard" replace />} />
              <Route path="/dashboard" element={<Dashboard />} />
              <Route path="/datasets" element={<Datasets />} />
              <Route path="/analysis" element={<Analysis />} />
              <Route path="/history" element={<History />} />
              <Route path="/reports" element={<Reports />} />
              <Route path="/chat" element={<Chat />} />
              <Route path="/profile" element={<Profile />} />

              {/* Role-Gated: Manager & Admin */}
              <Route
                element={<ProtectedRoute allowedRoles={['admin', 'manager']} />}
              >
                <Route path="/approvals" element={<Approvals />} />
              </Route>

              {/* Role-Gated: Admin Only */}
              <Route
                element={<ProtectedRoute allowedRoles={['admin']} />}
              >
                <Route path="/admin" element={<Admin />} />
              </Route>
            </Route>
          </Route>

          {/* Catch-all 404 Route */}
          <Route path="*" element={<NotFound />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}
