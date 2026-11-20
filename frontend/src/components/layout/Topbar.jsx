/**
 * src/components/layout/Topbar.jsx
 * ──────────────────────────────────
 * Top navigation bar.
 */

import React from 'react';
import { useLocation } from 'react-router-dom';
import { useAuth } from '@/context/AuthContext';

// Map route prefixes → human-readable page titles
const ROUTE_TITLES = {
  '/dashboard': 'Executive Dashboard',
  '/datasets': 'Dataset Ingestion',
  '/analysis': 'Multi-Agent Pipeline',
  '/history': 'Analysis History',
  '/reports': 'Verified BI Reports',
  '/approvals': 'Strategic Approvals',
  '/chat': 'Business AI Advisor',
  '/profile': 'Business Profile',
  '/admin': 'System Administration',
};

function getPageTitle(pathname) {
  for (const [prefix, title] of Object.entries(ROUTE_TITLES)) {
    if (pathname.startsWith(prefix)) return title;
  }
  return 'Retail BI';
}

const ROLE_COLORS = {
  admin: '#dc2626',
  manager: '#d97706',
  analyst: '#2563eb',
};

export default function Topbar({ onMenuToggle }) {
  const { user, role } = useAuth();
  const location = useLocation();

  return (
    <header className="topbar">
      <button
        className="topbar__menu-btn"
        onClick={onMenuToggle}
        aria-label="Toggle navigation menu"
      >
        ☰
      </button>

      <h1 className="topbar__title">
        {getPageTitle(location.pathname)}
      </h1>

      <div className="topbar__right">
        <span
          className="topbar__role-badge"
          style={{ backgroundColor: ROLE_COLORS[role] ?? '#6b7280' }}
        >
          {role}
        </span>

        <span className="topbar__email" title={user?.email}>
          {user?.email}
        </span>
      </div>
    </header>
  );
}
