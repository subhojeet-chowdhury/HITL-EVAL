/**
 * frontend/src/App.jsx
 * ─────────────────────
 * Root component — sets up layout and routing.
 *
 * LESSON — React Router:
 * React Router v6 uses <Routes> and <Route> to map URL paths to components.
 * The layout wraps all pages — sidebar and main content area are persistent.
 */

import React from 'react'
import { Routes, Route } from 'react-router-dom'
import Sidebar from './components/Sidebar.jsx'
import LabelQueue from './pages/LabelQueue.jsx'
import Stats from './pages/Stats.jsx'
import Optimizer from './pages/Optimizer.jsx'
import Ingest from './pages/Ingest.jsx'

export default function App() {
  return (
    <div style={{ display: 'flex', minHeight: '100vh' }}>
      <Sidebar />
      <main style={{ flex: 1, overflowY: 'auto' }}>
        <Routes>
          <Route path="/"         element={<LabelQueue />} />
          <Route path="/stats"    element={<Stats />} />
          <Route path="/optimize" element={<Optimizer />} />
          <Route path="/ingest"   element={<Ingest />} />
        </Routes>
      </main>
    </div>
  )
}
