/**
 * src/components/layout/Layout.jsx
 * ──────────────────────────────────
 * Root layout shell — renders for every authenticated page.
 *
 * Structure:
 *   <div.app-shell>
 *     <Sidebar />       ← fixed left column (collapsible on mobile)
 *     <div.main-area>
 *       <Topbar />      ← sticky top bar
 *       <main.page-content>
 *         <Outlet />    ← current page renders here
 *       </main>
 *     </div>
 *   </div>
 *
 * Mobile behaviour:
 *   The sidebar starts hidden on screens < 768 px. The hamburger button in
 *   the Topbar calls `setSidebarOpen(true)`. Clicking the backdrop or any
 *   nav link calls `setSidebarOpen(false)`. State is local to Layout — it
 *   doesn't need to be global because nothing outside the layout cares.
 *
 * Design: Why <Outlet /> instead of {children}?
 *   React Router v6 uses Outlet to render nested routes. Layout wraps all
 *   authenticated routes as a parent in the route tree, so child routes
 *   automatically render inside the <main> content area.
 */

import React, { useState } from 'react';
import { Outlet } from 'react-router-dom';
import Sidebar from './Sidebar';
import Topbar  from './Topbar';

export default function Layout() {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <div className="app-shell">
      <Sidebar
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
      />

      <div className="main-area">
        <Topbar onMenuToggle={() => setSidebarOpen((v) => !v)} />

        <main className="page-content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
