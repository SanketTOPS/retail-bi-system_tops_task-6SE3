/**
 * src/pages/Admin.jsx
 * ───────────────────
 * System Administration & Enterprise Governance Dashboard (Module 13.5).
 *
 * Restricted exclusively to users with role === 'admin'.
 *
 * Capabilities:
 *  - Platform-wide statistics: User headcounts by role, total datasets,
 *    analyses success/failure rates, average pipeline duration, and report audit stats.
 *  - Interactive Recharts visualization of users by role & analysis status distribution.
 *  - User Directory Management:
 *      - Live role assignment (Admin, Manager, Analyst) via PATCH /admin/users/{id}/role.
 *      - Account Activation / Deactivation toggle via PATCH /admin/users/{id}/status.
 *      - Self-demotion and self-lockout prevention guards.
 *      - Real-time search by user name or email.
 *  - Enterprise Analysis Oversight: Table of all intelligence runs across all users.
 */

import React, { useEffect, useState, useMemo } from 'react';
import toast from 'react-hot-toast';
import {
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from 'recharts';

import { useAuth } from '@/hooks/useAuth';
import {
  getAdminStatsApi,
  getAdminUsersApi,
  patchUserRoleApi,
  patchUserStatusApi,
  getAdminAnalysesApi,
} from '@/api/admin';

const ROLE_COLORS = {
  admin: '#dc2626',
  manager: '#d97706',
  analyst: '#2563eb',
};

const CHART_PALETTE = ['#2563eb', '#16a34a', '#f59e0b', '#dc2626', '#8b5cf6'];

export default function Admin() {
  const { user: currentAdmin, role } = useAuth();

  const [stats, setStats] = useState(null);
  const [users, setUsers] = useState([]);
  const [analyses, setAnalyses] = useState([]);
  const [loading, setLoading] = useState(true);

  // User search & filters
  const [searchQuery, setSearchQuery] = useState('');
  const [roleFilter, setRoleFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');

  // ── 1. Fetch All Admin Data ────────────────────────────────────────────────
  const loadAdminData = async () => {
    setLoading(true);
    try {
      const [statsData, usersData, analysesData] = await Promise.all([
        getAdminStatsApi().catch(() => null),
        getAdminUsersApi({ search: searchQuery || undefined, role: roleFilter || undefined }).catch(
          () => ({ items: [] })
        ),
        getAdminAnalysesApi().catch(() => ({ items: [] })),
      ]);

      setStats(statsData);
      setUsers(usersData.items || []);
      setAnalyses(analysesData.items || []);
    } catch {
      toast.error('Failed to load administrative governance data.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAdminData();
  }, [searchQuery, roleFilter]);

  // ── 2. Handle Role Change ──────────────────────────────────────────────────
  const handleRoleChange = async (userId, newRole) => {
    if (String(userId) === String(currentAdmin?.id)) {
      toast.error('Self-demotion forbidden. You cannot change your own admin role.');
      return;
    }

    try {
      await patchUserRoleApi(userId, newRole);
      toast.success(`User role updated to ${newRole}.`);
      setUsers((prev) =>
        prev.map((u) => (u.id === userId ? { ...u, role: newRole } : u))
      );
    } catch (err) {
      const detail = err.response?.data?.detail;
      toast.error(typeof detail === 'string' ? detail : 'Role modification failed.');
    }
  };

  // ── 3. Handle Status Toggle ────────────────────────────────────────────────
  const handleStatusToggle = async (userId, currentActive) => {
    if (String(userId) === String(currentAdmin?.id)) {
      toast.error('Self-lockout forbidden. You cannot deactivate your own account.');
      return;
    }

    const nextActive = !currentActive;
    const actionWord = nextActive ? 'activate' : 'deactivate';
    const confirmed = window.confirm(`Are you sure you want to ${actionWord} this account?`);
    if (!confirmed) return;

    try {
      await patchUserStatusApi(userId, nextActive);
      toast.success(`Account successfully ${actionWord}d.`);
      setUsers((prev) =>
        prev.map((u) => (u.id === userId ? { ...u, is_active: nextActive } : u))
      );
    } catch (err) {
      const detail = err.response?.data?.detail;
      toast.error(typeof detail === 'string' ? detail : 'Status change failed.');
    }
  };

  // ── Chart Data Transformation ──────────────────────────────────────────────
  const userRoleChartData = useMemo(() => {
    if (!stats?.users_by_role) return [];
    return Object.entries(stats.users_by_role).map(([roleKey, count]) => ({
      name: roleKey.charAt(0).toUpperCase() + roleKey.slice(1),
      count,
    }));
  }, [stats]);

  const analysisStatusChartData = useMemo(() => {
    if (!stats) return [];
    return [
      { status: 'Completed', count: stats.analyses_completed || 0 },
      { status: 'Running', count: stats.analyses_running || 0 },
      { status: 'Failed', count: stats.analyses_failed || 0 },
      { status: 'Ver. Failed', count: stats.analyses_verification_failed || 0 },
    ];
  }, [stats]);

  // ── Security Check (Redundant UX Guard) ────────────────────────────────────
  if (role !== 'admin') {
    return (
      <div className="page-wrapper">
        <div className="card" style={{ padding: '40px', textAlign: 'center' }}>
          <span style={{ fontSize: '3rem' }}>🛡️</span>
          <h2>System Administration Restricted</h2>
          <p style={{ color: 'var(--color-text-muted)', marginTop: '8px' }}>
            Only system administrators possess security clearance to access this control plane.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="page-wrapper admin-page">
      {/* ── Page Header ── */}
      <div className="page-header">
        <h2 className="page-header__title">System Administration &amp; Governance</h2>
        <p className="page-header__sub">
          Enterprise user provisioning, role-based access control, platform analytics, and multi-agent workload oversight.
        </p>
      </div>

      {/* ── Section 1: Platform Health Stats Cards ── */}
      {loading || !stats ? (
        <div className="kpi-grid">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="kpi-card kpi-card--skeleton">
              <div className="skeleton-line skeleton-line--sm" />
              <div className="skeleton-line skeleton-line--lg" />
            </div>
          ))}
        </div>
      ) : (
        <div className="kpi-grid">
          {/* Card 1: Users */}
          <div className="kpi-card kpi-card--primary">
            <span className="kpi-card__label">Total User Accounts</span>
            <span className="kpi-card__value">{stats.total_users}</span>
            <span className="kpi-card__sub">
              {stats.active_users} active &bull; {stats.inactive_users} deactivated
            </span>
          </div>

          {/* Card 2: Datasets */}
          <div className="kpi-card">
            <span className="kpi-card__label">Ingested Datasets</span>
            <span className="kpi-card__value">{stats.total_datasets}</span>
            <span className="kpi-card__sub">{stats.datasets_last_30_days} in last 30 days</span>
          </div>

          {/* Card 3: Total Analyses */}
          <div className="kpi-card kpi-card--success">
            <span className="kpi-card__label">Completed Analyses</span>
            <span className="kpi-card__value">{stats.analyses_completed}</span>
            <span className="kpi-card__badge">
              Success Rate: {stats.total_analyses > 0 ? ((stats.analyses_completed / stats.total_analyses) * 100).toFixed(0) : 100}%
            </span>
          </div>

          {/* Card 4: Verified Reports */}
          <div className="kpi-card">
            <span className="kpi-card__label">Verified Reports</span>
            <span className="kpi-card__value">{stats.total_reports}</span>
            <span className="kpi-card__sub">
              {stats.reports_pdf_generated} PDFs compiled on disk
            </span>
          </div>

          {/* Card 5: Approvals */}
          <div className="kpi-card kpi-card--highlight">
            <span className="kpi-card__label">Manager Approvals</span>
            <span className="kpi-card__value">{stats.total_approval_decisions}</span>
            <span className="kpi-card__sub">
              {stats.approvals_approved} approved &bull; {stats.pending_recommendations} pending
            </span>
          </div>

          {/* Card 6: Average Duration */}
          <div className="kpi-card kpi-card--retail">
            <span className="kpi-card__label">Avg Analysis Pipeline Duration</span>
            <span className="kpi-card__value">
              {stats.avg_analysis_duration_seconds ? `${stats.avg_analysis_duration_seconds}s` : '—'}
            </span>
            <span className="kpi-card__sub">Across all 6 sequential agents</span>
          </div>
        </div>
      )}

      {/* ── Section 2: Visual Statistics Breakdown ── */}
      {stats && (
        <div className="charts-grid charts-grid--2">
          {/* Chart A: Users by Role */}
          <div className="card chart-card">
            <div className="chart-card__header">
              <div>
                <h4 className="chart-card__title">User Headcount by RBAC Role</h4>
                <p className="chart-card__sub">Distribution of system roles across the organization</p>
              </div>
            </div>
            <div className="chart-container chart-container--pie">
              <ResponsiveContainer width="100%" height={240}>
                <PieChart>
                  <Pie
                    data={userRoleChartData}
                    dataKey="count"
                    nameKey="name"
                    cx="50%"
                    cy="50%"
                    innerRadius={55}
                    outerRadius={80}
                    paddingAngle={4}
                  >
                    {userRoleChartData.map((entry, idx) => (
                      <Cell
                        key={`cell-${idx}`}
                        fill={ROLE_COLORS[entry.name.toLowerCase()] || CHART_PALETTE[idx % CHART_PALETTE.length]}
                      />
                    ))}
                  </Pie>
                  <Tooltip formatter={(val, name) => [`${val} Users`, name]} />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Chart B: Analysis Pipeline Status Distribution */}
          <div className="card chart-card">
            <div className="chart-card__header">
              <div>
                <h4 className="chart-card__title">Multi-Agent Execution Outcomes</h4>
                <p className="chart-card__sub">Completed vs failed pipeline runs</p>
              </div>
            </div>
            <div className="chart-container">
              <ResponsiveContainer width="100%" height={240}>
                <BarChart data={analysisStatusChartData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                  <XAxis dataKey="status" stroke="#64748b" fontSize={12} />
                  <YAxis stroke="#64748b" fontSize={12} allowDecimals={false} />
                  <Tooltip formatter={(val) => [`${val} Runs`, 'Count']} />
                  <Bar dataKey="count" fill="#2563eb" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      )}

      {/* ── Section 3: User Management Table ── */}
      <div className="card" style={{ marginTop: '24px' }}>
        <div className="inventory-header">
          <div>
            <h3 className="inventory-title">User Account Directory &amp; RBAC</h3>
            <p className="chart-card__sub">
              Manage credentials, assign functional roles, and activate or deactivate accounts.
            </p>
          </div>

          {/* Search bar */}
          <div className="user-search-wrap">
            <input
              type="text"
              className="form-input"
              placeholder="Search user by name or email..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              style={{ width: '260px' }}
            />
          </div>
        </div>

        <div className="table-responsive">
          <table className="data-table">
            <thead>
              <tr>
                <th>User Identity</th>
                <th>Current Role</th>
                <th>Role Assignment</th>
                <th>Account Status</th>
                <th>Registered Date</th>
                <th style={{ textAlign: 'right' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => {
                const isSelf = String(u.id) === String(currentAdmin?.id);
                return (
                  <tr key={u.id}>
                    <td>
                      <div className="dataset-cell-name">
                        <div className="sidebar__avatar" style={{ width: '30px', height: '30px', fontSize: '0.75rem' }}>
                          {(u.full_name || u.email)[0].toUpperCase()}
                        </div>
                        <div>
                          <strong>{u.full_name}</strong>
                          <p className="user-email-sub">{u.email} {isSelf && <span className="you-pill">YOU</span>}</p>
                        </div>
                      </div>
                    </td>
                    <td>
                      <span
                        className="topbar__role-badge"
                        style={{ backgroundColor: ROLE_COLORS[u.role] || '#6b7280' }}
                      >
                        {u.role}
                      </span>
                    </td>
                    <td>
                      <select
                        className="form-input role-select-input"
                        value={u.role}
                        onChange={(e) => handleRoleChange(u.id, e.target.value)}
                        disabled={isSelf}
                        title={isSelf ? 'Cannot modify own role' : 'Assign role'}
                      >
                        <option value="analyst">Analyst</option>
                        <option value="manager">Manager</option>
                        <option value="admin">Admin</option>
                      </select>
                    </td>
                    <td>
                      <span className={`status-pill ${u.is_active ? 'status-pill--active' : 'status-pill--failed'}`}>
                        {u.is_active ? '● Active' : '○ Deactivated'}
                      </span>
                    </td>
                    <td>{new Date(u.created_at).toLocaleDateString()}</td>
                    <td style={{ textAlign: 'right' }}>
                      <button
                        type="button"
                        className={`btn-action ${u.is_active ? 'btn-action--danger' : ''}`}
                        onClick={() => handleStatusToggle(u.id, u.is_active)}
                        disabled={isSelf}
                        title={isSelf ? 'Cannot deactivate self' : u.is_active ? 'Deactivate account' : 'Activate account'}
                      >
                        {u.is_active ? 'Deactivate' : 'Activate'}
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* ── Section 4: Enterprise Analysis Oversight Table ── */}
      <div className="card" style={{ marginTop: '24px' }}>
        <div className="inventory-header">
          <div>
            <h3 className="inventory-title">Enterprise Workload Oversight</h3>
            <p className="chart-card__sub">Complete ledger of all multi-agent executions across the company</p>
          </div>
          <button className="btn btn--secondary btn--sm" onClick={loadAdminData} disabled={loading}>
            ↻ Refresh
          </button>
        </div>

        <div className="table-responsive">
          <table className="data-table">
            <thead>
              <tr>
                <th>Analysis ID</th>
                <th>Target Dataset</th>
                <th>Triggered By</th>
                <th>Status</th>
                <th>Duration</th>
                <th>Started At</th>
              </tr>
            </thead>
            <tbody>
              {analyses.map((an) => (
                <tr key={an.id}>
                  <td>
                    <code>{an.id.slice(0, 8)}</code>
                  </td>
                  <td>{an.dataset_name || an.dataset_id.slice(0, 8)}</td>
                  <td>{an.triggered_by_email || 'System'}</td>
                  <td>
                    <span className={`status-pill status-pill--${an.status}`}>
                      {an.status}
                    </span>
                  </td>
                  <td>{an.duration_seconds ? `${an.duration_seconds}s` : '—'}</td>
                  <td>{new Date(an.started_at).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
