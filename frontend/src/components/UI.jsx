/**
 * frontend/src/components/UI.jsx
 * ───────────────────────────────
 * Reusable primitive components.
 * Keeping these small and dumb (no state) makes them easy to test and reuse.
 */

import React from 'react'

// ── Badge ─────────────────────────────────────────────────────────────────────

const badgeColors = {
  good:    { bg: 'var(--good-dim)',  color: 'var(--good)',  border: 'var(--good)' },
  bad:     { bg: 'var(--bad-dim)',   color: 'var(--bad)',   border: 'var(--bad)' },
  edited:  { bg: 'var(--edit-dim)', color: 'var(--edit)',  border: 'var(--edit)' },
  pending: { bg: 'var(--surface-2)',color: 'var(--text-muted)', border: 'var(--border)' },
  default: { bg: 'var(--accent-dim)',color: 'var(--accent)', border: 'var(--accent)' },
}

export function Badge({ children, variant = 'default', style }) {
  const c = badgeColors[variant] || badgeColors.default
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center',
      padding: '2px 8px',
      fontSize: '11px', fontWeight: 600, letterSpacing: '0.06em',
      textTransform: 'uppercase',
      borderRadius: 'var(--radius)',
      background: c.bg, color: c.color,
      border: `1px solid ${c.border}44`,
      ...style,
    }}>
      {children}
    </span>
  )
}

// ── Button ────────────────────────────────────────────────────────────────────

const btnStyles = {
  good: {
    background: 'var(--good-dim)', color: 'var(--good)',
    border: '1.5px solid var(--good)', hoverBg: '#00e67633',
  },
  bad: {
    background: 'var(--bad-dim)', color: 'var(--bad)',
    border: '1.5px solid var(--bad)', hoverBg: '#ff3d5a33',
  },
  edit: {
    background: 'var(--edit-dim)', color: 'var(--edit)',
    border: '1.5px solid var(--edit)', hoverBg: '#ffc40033',
  },
  ghost: {
    background: 'transparent', color: 'var(--text-muted)',
    border: '1.5px solid var(--border)', hoverBg: 'var(--surface-2)',
  },
  primary: {
    background: 'var(--accent)', color: 'white',
    border: '1.5px solid var(--accent)', hoverBg: '#9080ff',
  },
}

export function Button({ children, variant = 'ghost', onClick, disabled, style, title }) {
  const s = btnStyles[variant] || btnStyles.ghost
  const [hovered, setHovered] = React.useState(false)
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      title={title}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
        gap: '6px',
        padding: '8px 18px',
        fontSize: '13px', fontWeight: 600, fontFamily: 'var(--font-body)',
        borderRadius: 'var(--radius)',
        cursor: disabled ? 'not-allowed' : 'pointer',
        opacity: disabled ? 0.45 : 1,
        transition: 'all 0.15s ease',
        background: hovered && !disabled ? s.hoverBg : s.background,
        color: s.color,
        border: s.border,
        ...style,
      }}
    >
      {children}
    </button>
  )
}

// ── Card ──────────────────────────────────────────────────────────────────────

export function Card({ children, style }) {
  return (
    <div style={{
      background: 'var(--surface)',
      border: '1px solid var(--border)',
      borderRadius: 'var(--radius-lg)',
      padding: '20px',
      ...style,
    }}>
      {children}
    </div>
  )
}

// ── StatBox ───────────────────────────────────────────────────────────────────

export function StatBox({ label, value, color = 'var(--text)', sub }) {
  return (
    <div style={{
      background: 'var(--surface-2)',
      border: '1px solid var(--border)',
      borderRadius: 'var(--radius-lg)',
      padding: '16px 20px',
      minWidth: 100,
    }}>
      <div style={{ fontSize: 26, fontWeight: 700, color, fontFamily: 'var(--font-mono)' }}>
        {value}
      </div>
      <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.07em', marginTop: 2 }}>
        {label}
      </div>
      {sub && <div style={{ fontSize: 11, color, marginTop: 4, fontFamily: 'var(--font-mono)' }}>{sub}</div>}
    </div>
  )
}

// ── Spinner ───────────────────────────────────────────────────────────────────

export function Spinner({ size = 20 }) {
  return (
    <span style={{
      display: 'inline-block',
      width: size, height: size,
      border: `2px solid var(--border)`,
      borderTopColor: 'var(--accent)',
      borderRadius: '50%',
      animation: 'spin 0.7s linear infinite',
    }} />
  )
}

// Inject keyframes once
if (typeof document !== 'undefined') {
  const style = document.createElement('style')
  style.textContent = `@keyframes spin { to { transform: rotate(360deg); } }`
  document.head.appendChild(style)
}

// ── Label ─────────────────────────────────────────────────────────────────────

export function Label({ children, style }) {
  return (
    <div style={{
      fontSize: 11,
      textTransform: 'uppercase',
      letterSpacing: '0.08em',
      color: 'var(--text-muted)',
      fontWeight: 600,
      marginBottom: 6,
      ...style,
    }}>
      {children}
    </div>
  )
}

// ── Divider ───────────────────────────────────────────────────────────────────

export function Divider({ style }) {
  return (
    <hr style={{
      border: 'none',
      borderTop: '1px solid var(--border)',
      ...style,
    }} />
  )
}

// ── Textarea ──────────────────────────────────────────────────────────────────

export function Textarea({ value, onChange, placeholder, rows = 4, style }) {
  return (
    <textarea
      value={value}
      onChange={e => onChange(e.target.value)}
      placeholder={placeholder}
      rows={rows}
      style={{
        width: '100%',
        background: 'var(--surface-2)',
        border: '1px solid var(--border)',
        borderRadius: 'var(--radius)',
        color: 'var(--text)',
        fontFamily: 'var(--font-mono)',
        fontSize: 12,
        padding: '10px 12px',
        resize: 'vertical',
        outline: 'none',
        transition: 'border-color 0.15s',
        ...style,
      }}
      onFocus={e => e.target.style.borderColor = 'var(--accent)'}
      onBlur={e => e.target.style.borderColor = 'var(--border)'}
    />
  )
}

// ── Input ─────────────────────────────────────────────────────────────────────

export function Input({ value, onChange, placeholder, style }) {
  return (
    <input
      value={value}
      onChange={e => onChange(e.target.value)}
      placeholder={placeholder}
      style={{
        width: '100%',
        background: 'var(--surface-2)',
        border: '1px solid var(--border)',
        borderRadius: 'var(--radius)',
        color: 'var(--text)',
        fontFamily: 'var(--font-body)',
        fontSize: 13,
        padding: '8px 12px',
        outline: 'none',
        transition: 'border-color 0.15s',
        ...style,
      }}
      onFocus={e => e.target.style.borderColor = 'var(--accent)'}
      onBlur={e => e.target.style.borderColor = 'var(--border)'}
    />
  )
}

// ── Toast ─────────────────────────────────────────────────────────────────────

export function Toast({ message, type = 'info', onClose }) {
  const colors = { info: 'var(--accent)', success: 'var(--good)', error: 'var(--bad)' }
  React.useEffect(() => {
    const t = setTimeout(onClose, 3000)
    return () => clearTimeout(t)
  }, [onClose])
  return (
    <div style={{
      position: 'fixed', bottom: 24, right: 24, zIndex: 9999,
      background: 'var(--surface)',
      border: `1px solid ${colors[type]}`,
      borderLeft: `3px solid ${colors[type]}`,
      borderRadius: 'var(--radius)',
      padding: '12px 16px',
      color: 'var(--text)',
      fontSize: 13,
      boxShadow: '0 8px 24px rgba(0,0,0,0.4)',
      animation: 'slideIn 0.2s ease',
    }}>
      {message}
    </div>
  )
}

if (typeof document !== 'undefined') {
  const style = document.createElement('style')
  style.textContent = `@keyframes slideIn { from { transform: translateY(12px); opacity: 0; } to { transform: translateY(0); opacity: 1; } }`
  document.head.appendChild(style)
}
