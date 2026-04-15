/**
 * frontend/src/pages/LabelQueue.jsx
 * ───────────────────────────────────
 * The core labeling interface.
 *
 * LESSON — UI/UX for labeling tools:
 * Labeling is repetitive work. Good labeling UIs:
 *   1. Show one item at a time (no scrolling, no pagination)
 *   2. Put the action buttons where your hands already are (keyboard shortcuts!)
 *   3. Show progress so the labeler doesn't feel like they're in an abyss
 *   4. Auto-advance to the next item immediately after labeling
 *
 * LESSON — Polling pattern in React:
 * We use a simple loop: fetch item → show it → labeler submits → fetch next.
 * This is NOT a traditional polling interval (setInterval) — we only fetch
 * the NEXT item AFTER the current one is labeled. This prevents race conditions
 * where two items are shown simultaneously.
 */

import React, { useCallback, useEffect, useRef, useState } from 'react'
import { fetchNextItem, submitLabel, skipItem } from '../hooks/useApi.js'
import { Badge, Button, Card, Divider, Label, Spinner, Textarea, Toast } from '../components/UI.jsx'

export default function LabelQueue() {
  const [item, setItem]             = useState(null)
  const [loading, setLoading]       = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [note, setNote]             = useState('')
  const [corrected, setCorrected]   = useState('')
  const [showEdit, setShowEdit]     = useState(false)
  const [toast, setToast]           = useState(null)
  const [labelCount, setLabelCount] = useState(0)
  const [labelerId]                 = useState(() => localStorage.getItem('labelerId') || 'anonymous')
  const pollingRef                  = useRef(true)

  const showToast = (message, type = 'info') => setToast({ message, type })

  // ── Fetch next item from queue ─────────────────────────────────────────
  const fetchNext = useCallback(async () => {
    setLoading(true)
    setNote('')
    setCorrected('')
    setShowEdit(false)

    try {
      // fetchNextItem calls GET /api/label/next
      // The server blocks for up to 5 seconds if queue is empty (long-polling)
      const data = await fetchNextItem()
      setItem(data)   // null if queue is empty
    } catch (err) {
      showToast(`Error fetching item: ${err.message}`, 'error')
      setItem(null)
    } finally {
      setLoading(false)
    }
  }, [])

  // Fetch first item on mount
  useEffect(() => {
    fetchNext()
    return () => { pollingRef.current = false }
  }, [fetchNext])

  // ── Submit a verdict ───────────────────────────────────────────────────
  const handleVerdict = async (verdict) => {
    if (!item || submitting) return

    // Validate "edited" requires correction
    if (verdict === 'edited' && !corrected.trim()) {
      showToast('Please provide a corrected output before submitting', 'error')
      return
    }

    setSubmitting(true)
    try {
      await submitLabel({
        itemId: item.item_id,
        verdict,
        correctedOutput: verdict === 'edited' ? corrected : undefined,
        note: note.trim() || undefined,
        labelerId,
      })

      setLabelCount(c => c + 1)
      showToast(
        verdict === 'good' ? '✅ Marked Good' :
        verdict === 'bad'  ? '❌ Marked Bad' :
        '✏️ Edit saved',
        'success'
      )

      // Auto-advance to next item
      await fetchNext()
    } catch (err) {
      showToast(`Error: ${err.message}`, 'error')
    } finally {
      setSubmitting(false)
    }
  }

  // ── Skip ───────────────────────────────────────────────────────────────
  const handleSkip = async () => {
    if (!item) return
    try {
      await skipItem(item.item_id)
      showToast('Item skipped', 'info')
      await fetchNext()
    } catch (err) {
      showToast(`Error: ${err.message}`, 'error')
    }
  }

  // ── Keyboard shortcuts ─────────────────────────────────────────────────
  // LESSON: Keyboard shortcuts are critical for labeling tools.
  // A labeler doing 200 items a day saves significant time with G/B/S keys.
  useEffect(() => {
    const handler = (e) => {
      if (e.target.tagName === 'TEXTAREA' || e.target.tagName === 'INPUT') return
      if (e.key === 'g' || e.key === 'G') handleVerdict('good')
      if (e.key === 'b' || e.key === 'B') handleVerdict('bad')
      if (e.key === 'e' || e.key === 'E') setShowEdit(v => !v)
      if (e.key === 's' || e.key === 'S') handleSkip()
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [item, corrected, submitting]) // eslint-disable-line

  // ── Render: loading ────────────────────────────────────────────────────
  if (loading) {
    return (
      <PageShell labelCount={labelCount}>
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 16, marginTop: 80 }}>
          <Spinner size={32} />
          <div style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', fontSize: 12 }}>
            Waiting for queue...
          </div>
        </div>
      </PageShell>
    )
  }

  // ── Render: empty queue ────────────────────────────────────────────────
  if (!item) {
    return (
      <PageShell labelCount={labelCount}>
        <div style={{
          textAlign: 'center', marginTop: 80,
          display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 16,
        }}>
          <div style={{ fontSize: 48 }}>◎</div>
          <div style={{ fontSize: 18, fontWeight: 600, color: 'var(--text)' }}>Queue is empty</div>
          <div style={{ color: 'var(--text-muted)', fontSize: 13, maxWidth: 360 }}>
            No items waiting for review. New items will appear here automatically
            when your application enqueues LLM outputs.
          </div>
          <Button onClick={fetchNext} variant="ghost" style={{ marginTop: 8 }}>
            ↺ Check again
          </Button>
        </div>
      </PageShell>
    )
  }

  // ── Render: item to label ──────────────────────────────────────────────
  return (
    <PageShell labelCount={labelCount}>
      {/* Header strip */}
      <div style={{
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        marginBottom: 20,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <Badge variant="default">{item.prompt_id}</Badge>
          {item.model && <Badge variant="pending">{item.model}</Badge>}
        </div>
        <div style={{
          fontSize: 11, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)',
        }}>
          {item.queue_depth} remaining · {item.item_id.slice(0, 8)}...
        </div>
      </div>

      {/* Prompt block */}
      <Card style={{ marginBottom: 16 }}>
        <Label>Prompt</Label>
        <pre style={{
          whiteSpace: 'pre-wrap', wordBreak: 'break-word',
          fontFamily: 'var(--font-mono)', fontSize: 12,
          color: 'var(--text-muted)', lineHeight: 1.7,
          maxHeight: 160, overflowY: 'auto',
        }}>
          {item.prompt}
        </pre>
      </Card>

      {/* Output block — this is what we're judging */}
      <Card style={{
        marginBottom: 16,
        borderColor: 'var(--border-hi)',
        background: 'var(--surface-2)',
      }}>
        <Label>LLM Output <span style={{ color: 'var(--accent)', fontWeight: 400 }}>← judge this</span></Label>
        <pre style={{
          whiteSpace: 'pre-wrap', wordBreak: 'break-word',
          fontFamily: 'var(--font-mono)', fontSize: 13,
          color: 'var(--text)', lineHeight: 1.8,
          maxHeight: 280, overflowY: 'auto',
        }}>
          {item.output}
        </pre>
      </Card>

      {/* Note field */}
      <div style={{ marginBottom: 16 }}>
        <Label>Note (optional)</Label>
        <Textarea
          value={note}
          onChange={setNote}
          placeholder="Why is this good or bad? (appears in the optimizer context)"
          rows={2}
        />
      </div>

      {/* Edit panel */}
      {showEdit && (
        <Card style={{ marginBottom: 16, borderColor: 'var(--edit)44' }}>
          <Label style={{ color: 'var(--edit)' }}>Corrected Output</Label>
          <Textarea
            value={corrected}
            onChange={setCorrected}
            placeholder="Write the ideal response here..."
            rows={5}
          />
          <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 8 }}>
            This corrected output will be used as a training example in the DSPy optimizer.
          </div>
        </Card>
      )}

      <Divider style={{ marginBottom: 16 }} />

      {/* Action buttons */}
      <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
        <Button
          variant="good"
          onClick={() => handleVerdict('good')}
          disabled={submitting}
          title="[G] Mark as Good"
          style={{ flex: 1, padding: '12px 0', fontSize: 14 }}
        >
          ✅ Good <Kbd>G</Kbd>
        </Button>
        <Button
          variant="bad"
          onClick={() => handleVerdict('bad')}
          disabled={submitting}
          title="[B] Mark as Bad"
          style={{ flex: 1, padding: '12px 0', fontSize: 14 }}
        >
          ❌ Bad <Kbd>B</Kbd>
        </Button>
        <Button
          variant="edit"
          onClick={() => {
            setShowEdit(v => !v)
            if (!showEdit) setTimeout(() => document.querySelector('textarea[placeholder*="ideal"]')?.focus(), 50)
          }}
          disabled={submitting}
          title="[E] Edit then submit"
          style={{ flex: 1, padding: '12px 0', fontSize: 14 }}
        >
          ✏️ Edit <Kbd>E</Kbd>
        </Button>
        {showEdit && (
          <Button
            variant="edit"
            onClick={() => handleVerdict('edited')}
            disabled={submitting || !corrected.trim()}
            style={{ padding: '12px 18px', fontSize: 14 }}
          >
            Save Edit
          </Button>
        )}
        <Button
          variant="ghost"
          onClick={handleSkip}
          disabled={submitting}
          title="[S] Skip this item"
          style={{ padding: '12px 14px' }}
        >
          Skip <Kbd>S</Kbd>
        </Button>
      </div>

      {toast && (
        <Toast
          message={toast.message}
          type={toast.type}
          onClose={() => setToast(null)}
        />
      )}
    </PageShell>
  )
}

// ── Sub-components ─────────────────────────────────────────────────────────────

function PageShell({ children, labelCount }) {
  return (
    <div style={{ maxWidth: 760, margin: '0 auto', padding: '32px 24px' }}>
      <div style={{
        display: 'flex', justifyContent: 'space-between', alignItems: 'baseline',
        marginBottom: 28,
      }}>
        <h1 style={{ fontSize: 20, fontWeight: 700 }}>Label Queue</h1>
        {labelCount > 0 && (
          <div style={{
            fontSize: 12, color: 'var(--good)',
            fontFamily: 'var(--font-mono)',
          }}>
            +{labelCount} labeled this session
          </div>
        )}
      </div>
      {children}
    </div>
  )
}

function Kbd({ children }) {
  return (
    <span style={{
      display: 'inline-block',
      fontSize: 10, fontFamily: 'var(--font-mono)',
      padding: '1px 5px',
      background: 'rgba(255,255,255,0.08)',
      borderRadius: 3,
      marginLeft: 4,
      opacity: 0.7,
    }}>
      {children}
    </span>
  )
}
