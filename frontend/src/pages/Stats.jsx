/**
 * frontend/src/pages/Stats.jsx
 * ──────────────────────────────
 * Analytics dashboard — overview and per-prompt breakdown.
 *
 * LESSON — Why display stats in the labeling tool?
 * Labelers need feedback to stay calibrated. If 85% of outputs are being
 * labeled "bad", that's a signal that the prompt is broken — and the labeler
 * should know that so they can flag it, not just grind through bad outputs.
 *
 * Stats also answer: "Is it worth running the optimizer yet?"
 */

import React, { useEffect, useState } from 'react'
import { fetchOverviewStats, fetchPromptIds, fetchPromptStats } from '../hooks/useApi.js'
import { Badge, Card, Spinner, StatBox } from '../components/UI.jsx'

export default function Stats() {
  const [overview, setOverview] = useState(null)
  const [promptIds, setPromptIds] = useState([])
  const [promptStats, setPromptStats] = useState({})
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const load = async () => {
      try {
        const [ov, pids] = await Promise.all([fetchOverviewStats(), fetchPromptIds()])
        setOverview(ov)
        setPromptIds(pids.prompt_ids || [])

        // Load per-prompt stats in parallel
        const entries = await Promise.all(
          (pids.prompt_ids || []).map(id =>
            fetchPromptStats(id).then(s => [id, s])
          )
        )
        setPromptStats(Object.fromEntries(entries))
      } catch (err) {
        console.error(err)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  if (loading) return (
    <Page>
      <div style={{ display: 'flex', justifyContent: 'center', marginTop: 60 }}>
        <Spinner size={28} />
      </div>
    </Page>
  )

  const goodRate = overview
    ? overview.good_labels + overview.bad_labels > 0
      ? Math.round(overview.good_labels / (overview.good_labels + overview.bad_labels + overview.edited_labels) * 100)
      : 0
    : 0

  return (
    <Page>
      {/* Overview row */}
      <Section title="Overview">
        <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
          <StatBox label="Total Items" value={overview?.total_items ?? 0} />
          <StatBox label="Labeled" value={overview?.labeled_items ?? 0} color="var(--good)" />
          <StatBox label="Pending" value={overview?.pending_items ?? 0} color="var(--edit)" />
          <StatBox label="Queue Depth" value={overview?.queue_depth ?? 0} color="var(--accent)" />
          <StatBox label="Good Rate"
            value={`${goodRate}%`}
            color={goodRate >= 70 ? 'var(--good)' : goodRate >= 40 ? 'var(--edit)' : 'var(--bad)'}
            sub={`${overview?.label_rate_pct ?? 0}% labeled`}
          />
        </div>
      </Section>

      {/* Label breakdown */}
      <Section title="Label Breakdown">
        <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
          <StatBox label="✅ Good"   value={overview?.good_labels ?? 0}   color="var(--good)" />
          <StatBox label="❌ Bad"    value={overview?.bad_labels ?? 0}    color="var(--bad)" />
          <StatBox label="✏️ Edited" value={overview?.edited_labels ?? 0} color="var(--edit)" />
        </div>
      </Section>

      {/* Per-prompt table */}
      {promptIds.length > 0 && (
        <Section title="Per-Prompt Breakdown">
          <Card style={{ padding: 0, overflow: 'hidden' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border)', background: 'var(--surface-2)' }}>
                  {['Prompt ID', 'Total', 'Good', 'Bad', 'Edited', 'Pending', 'Good Rate'].map(h => (
                    <Th key={h}>{h}</Th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {promptIds.map(id => {
                  const s = promptStats[id]
                  if (!s) return null
                  const rate = s.good + s.bad + s.edited > 0
                    ? Math.round(s.good / (s.good + s.bad + s.edited) * 100)
                    : null
                  return (
                    <tr key={id} style={{ borderBottom: '1px solid var(--border)' }}>
                      <Td>
                        <Badge variant="default">{id}</Badge>
                      </Td>
                      <Td mono>{s.total}</Td>
                      <Td mono color="var(--good)">{s.good}</Td>
                      <Td mono color="var(--bad)">{s.bad}</Td>
                      <Td mono color="var(--edit)">{s.edited}</Td>
                      <Td mono color="var(--text-muted)">{s.pending}</Td>
                      <Td>
                        {rate !== null ? (
                          <Badge variant={rate >= 70 ? 'good' : rate >= 40 ? 'edited' : 'bad'}>
                            {rate}%
                          </Badge>
                        ) : '—'}
                      </Td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </Card>
        </Section>
      )}

      {promptIds.length === 0 && (
        <div style={{ textAlign: 'center', marginTop: 60, color: 'var(--text-muted)' }}>
          No data yet. Enqueue some items and label them to see stats here.
        </div>
      )}
    </Page>
  )
}

// ── Sub-components ─────────────────────────────────────────────────────────────

function Page({ children }) {
  return (
    <div style={{ maxWidth: 900, margin: '0 auto', padding: '32px 24px' }}>
      <h1 style={{ fontSize: 20, fontWeight: 700, marginBottom: 28 }}>Stats</h1>
      {children}
    </div>
  )
}

function Section({ title, children }) {
  return (
    <div style={{ marginBottom: 32 }}>
      <div style={{
        fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.08em',
        color: 'var(--text-muted)', fontWeight: 600, marginBottom: 12,
      }}>
        {title}
      </div>
      {children}
    </div>
  )
}

function Th({ children }) {
  return (
    <th style={{
      padding: '10px 16px', textAlign: 'left',
      fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.07em',
      color: 'var(--text-muted)', fontWeight: 600,
    }}>
      {children}
    </th>
  )
}

function Td({ children, mono, color }) {
  return (
    <td style={{
      padding: '10px 16px',
      fontSize: 13,
      fontFamily: mono ? 'var(--font-mono)' : 'var(--font-body)',
      color: color || 'var(--text)',
    }}>
      {children}
    </td>
  )
}
