/**
 * frontend/src/components/Sidebar.jsx
 * ─────────────────────────────────────
 * Persistent left navigation.
 */

import React from 'react'
import { NavLink } from 'react-router-dom'

const NAV = [
  { path: '/',          icon: '⬡',  label: 'Label Queue' },
  { path: '/stats',     icon: '◈',  label: 'Stats' },
  { path: '/optimize',  icon: '⟳',  label: 'Optimizer' },
  { path: '/ingest',    icon: '↑',  label: 'Ingest' },
]

export default function Sidebar() {
  return (
    <aside style={{
      width: 220,
      minHeight: '100vh',
      background: 'var(--surface)',
      borderRight: '1px solid var(--border)',
      display: 'flex',
      flexDirection: 'column',
      padding: '0',
      flexShrink: 0,
    }}>
      {/* Wordmark */}
      <div style={{
        padding: '22px 20px 18px',
        borderBottom: '1px solid var(--border)',
      }}>
        <div style={{
          fontFamily: 'var(--font-mono)',
          fontSize: 13,
          fontWeight: 700,
          color: 'var(--text)',
          letterSpacing: '0.05em',
        }}>
          <span style={{ color: 'var(--accent)' }}>▣</span> HITL EVAL
        </div>
        <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 3, letterSpacing: '0.06em' }}>
          HUMAN-IN-THE-LOOP
        </div>
      </div>

      {/* Nav items */}
      <nav style={{ padding: '12px 8px', flex: 1 }}>
        {NAV.map(({ path, icon, label }) => (
          <NavLink
            key={path}
            to={path}
            end={path === '/'}
            style={({ isActive }) => ({
              display: 'flex',
              alignItems: 'center',
              gap: 10,
              padding: '9px 12px',
              borderRadius: 'var(--radius)',
              marginBottom: 2,
              fontWeight: isActive ? 600 : 400,
              fontSize: 13,
              color: isActive ? 'var(--text)' : 'var(--text-muted)',
              background: isActive ? 'var(--surface-2)' : 'transparent',
              borderLeft: isActive ? '2px solid var(--accent)' : '2px solid transparent',
              transition: 'all 0.12s ease',
              textDecoration: 'none',
            })}
          >
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: 14 }}>{icon}</span>
            {label}
          </NavLink>
        ))}
      </nav>

      {/* Footer */}
      <div style={{
        padding: '16px 20px',
        borderTop: '1px solid var(--border)',
        fontSize: 10,
        color: 'var(--text-dim)',
        fontFamily: 'var(--font-mono)',
      }}>
        v0.1.0 · MIT License
      </div>
    </aside>
  )
}
