/**
 * src/components/layout/Sidebar.jsx
 * ───────────────────────────────────
 * Responsive sidebar navigation.
 */

import React from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { useAuth } from '@/context/AuthContext';

// `roles: null` → visible to all authenticated users
const NAV_ITEMS = [
  { path: '/dashboard', label: 'Dashboard', icon: '📊', roles: null },
  { path: '/datasets', label: 'Datasets', icon: '🗄️', roles: null },
  { path: '/analysis', label: 'Analysis', icon: '🔬', roles: null },
  { path: '/history', label: 'History', icon: '⏱️', roles: null },
  { path: '/reports', label: 'Reports', icon: '📄', roles: null },
  { path: '/approvals', label: 'Approvals', icon: '✅', roles: ['admin', 'manager'] },
  { path: '/chat', label: 'AI Chat', icon: '💬', roles: null },
  { path: '/profile', label: 'Profile', icon: '👤', roles: null },
  { path: '/admin', label: 'Admin Panel', icon: '🛡️', roles: ['admin'] },
];

export default function Sidebar({ isOpen, onClose }) {
  const { user, role, logout } = useAuth();
  const location = useLocation();

  const visibleItems = NAV_ITEMS.filter(
    (item) => !item.roles || item.roles.includes(role),
  );

  return (
    <>
      {/* Mobile backdrop */}
      {isOpen && (
        <div
          className="sidebar-backdrop"
          onClick={onClose}
          aria-hidden="true"
        />
      )}

      <aside className={`sidebar ${isOpen ? 'sidebar--open' : ''}`}>
        {/* Brand */}
        <div className="sidebar__brand">
          <span className="sidebar__logo">📈</span>
          <span className="sidebar__app-name">
            {import.meta.env.VITE_APP_NAME || 'Retail BI'}
          </span>
        </div>

        {/* Navigation */}
        <nav className="sidebar__nav" aria-label="Main navigation">
          <ul className="sidebar__nav-list">
            {visibleItems.map((item) => (
              <li key={item.path} className="sidebar__nav-item">
                <NavLink
                  to={item.path}
                  className={({ isActive }) =>
                    `sidebar__nav-link ${isActive ? 'sidebar__nav-link--active' : ''}`
                  }
                  onClick={onClose}
                  end={item.path === '/dashboard'}
                >
                  <span className="sidebar__nav-icon" aria-hidden="true">
                    {item.icon}
                  </span>
                  <span className="sidebar__nav-label">{item.label}</span>
                </NavLink>
              </li>
            ))}
          </ul>
        </nav>

        {/* User card + logout at bottom */}
        <div className="sidebar__footer">
          <div className="sidebar__user">
            <div className="sidebar__avatar" aria-hidden="true">
              {(user?.full_name ?? user?.email ?? '?')[0].toUpperCase()}
            </div>
            <div className="sidebar__user-info">
              <p className="sidebar__user-name">
                {user?.full_name ?? 'User'}
              </p>
              <p className="sidebar__user-role">{role}</p>
            </div>
          </div>
          <button
            className="sidebar__logout-btn"
            onClick={logout}
            aria-label="Log out"
          >
            🚪 Logout
          </button>
        </div>
      </aside>
    </>
  );
}
