/**
 * frontend/src/pages/Optimizer.jsx
 * ──────────────────────────────────
 * UI to trigger DSPy optimization and inspect prompt version history.
 *
 * LESSON — Why put the optimizer in the UI?
 * The optimizer could be triggered by a cron job or CLI script, but
 * having it in the UI means:
 *   1. Non-engineers can trigger it (a PM, a data curator)
 *   2. You can see the diff between old and new prompt immediately
 *   3. You can copy the optimized prompt directly from the UI
 *
 * This embodies the "human in the loop" philosophy — the human decides
 * WHEN to optimize and inspects the result before deploying it.
 */

import React, { useEffect, useState } from 'react'
import { fetchOptimizationHistory, fetchPromptIds, runOptimizer } from '../hooks/useApi.js'
import { Badge, Button, Card, Divider, Input, Label, Spinner, Textarea, Toast } from '../components/UI.jsx'

export default function Optimizer() {
  const [promptIds, setPromptIds]     = useState([])
  const [selectedId, setSelectedId]   = useState('')
  const [basePrompt, setBasePrompt]   = useState('')
  const [minLabels, setMinLabels]     = useState('20')
  const [running, setRunning]         = useState(false)
  const [result, setResult]           = useState(null)
  const [history, setHistory]         = useState([])
  const [loadingHistory, setLoadingHistory] = useState(false)
  const [toast, setToast]             = useState(null)

  useEffect(() => {
    fetchPromptIds().then(d => setPromptIds(d.prompt_ids || []))
  }, [])

  const loadHistory = async (id) => {
    if (!id) return
    setLoadingHistory(true)
    try {
      const d = await fetchOptimizationHistory(id)
      setHistory(d.versions || [])
    } catch {
      setHistory([])
    } finally {
      setLoadingHistory(false)
    }
  }

  const handleSelectId = (id) => {
    setSelectedId(id)
    setResult(null)
    loadHistory(id)
  }

  const handleRun = async () => {
    if (!selectedId || !basePrompt.trim()) {
      setToast({ message: 'Select a prompt ID and enter the base prompt', type: 'error' })
      return
    }
    setRunning(true)
    setResult(null)
    try {
      const res = await runOptimizer({
        promptId: selectedId,
        basePrompt,
        minLabels: parseInt(minLabels) || 20,
      })
      setResult(res)
      setToast({ message: '✅ Optimization complete!', type: 'success' })
      await loadHistory(selectedId)
    } catch (err) {
      setToast({ message: err.message, type: 'error' })
    } finally {
      setRunning(false)
    }
  }

  return (
    <div style={{ maxWidth: 860, margin: '0 auto', padding: '32px 24px' }}>
      <h1 style={{ fontSize: 20, fontWeight: 700, marginBottom: 6 }}>Prompt Optimizer</h1>
      <p style={{ color: 'var(--text-muted)', fontSize: 13, marginBottom: 28 }}>
        Uses your human labels as training signal to rewrite and improve your prompts via DSPy.
      </p>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24 }}>
        {/* Left: config */}
        <div>
          <Card style={{ marginBottom: 16 }}>
            <Label>Prompt ID</Label>
            {promptIds.length > 0 ? (
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 8 }}>
                {promptIds.map(id => (
                  <button
                    key={id}
                    onClick={() => handleSelectId(id)}
                    style={{
                      padding: '5px 12px',
                      borderRadius: 'var(--radius)',
                      fontSize: 12,
                      fontFamily: 'var(--font-mono)',
                      cursor: 'pointer',
                      background: selectedId === id ? 'var(--accent-dim)' : 'var(--surface-2)',
                      color: selectedId === id ? 'var(--accent)' : 'var(--text-muted)',
                      border: selectedId === id ? '1px solid var(--accent)' : '1px solid var(--border)',
                    }}
                  >
                    {id}
                  </button>
                ))}
              </div>
            ) : (
              <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 8 }}>
                No prompt IDs found. Ingest some items first.
              </div>
            )}
            <Input
              value={selectedId}
              onChange={setSelectedId}
              placeholder="or type a prompt ID manually"
            />
          </Card>

          <Card style={{ marginBottom: 16 }}>
            <Label>Base Prompt (current version)</Label>
            <Textarea
              value={basePrompt}
              onChange={setBasePrompt}
              placeholder="Paste your current prompt here. The optimizer will rewrite it with few-shot examples from your good labels."
              rows={8}
            />
          </Card>

          <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
            <div style={{ flex: 1 }}>
              <Label>Min Labels Required</Label>
              <Input
                value={minLabels}
                onChange={setMinLabels}
                placeholder="20"
              />
            </div>
            <Button
              variant="primary"
              onClick={handleRun}
              disabled={running || !selectedId || !basePrompt.trim()}
              style={{ marginTop: 20, padding: '10px 24px' }}
            >
              {running ? <><Spinner size={14} /> Running...</> : '⟳ Run Optimizer'}
            </Button>
          </div>

          {/* Explainer */}
          <Card style={{ marginTop: 16, borderColor: 'var(--accent)33' }}>
            <div style={{ fontSize: 12, color: 'var(--text-muted)', lineHeight: 1.8 }}>
              <strong style={{ color: 'var(--accent)' }}>What happens when you run:</strong>
              <ol style={{ marginTop: 8, paddingLeft: 20 }}>
                <li>Loads all <Badge variant="good">good</Badge> + <Badge variant="edited">edited</Badge> labels for this prompt ID</li>
                <li>Selects the best few-shot examples</li>
                <li>Rewrites your prompt with those examples baked in</li>
                <li>Saves the result as a new <strong>PromptVersion</strong> in the DB</li>
              </ol>
            </div>
          </Card>
        </div>

        {/* Right: result + history */}
        <div>
          {result && (
            <Card style={{ marginBottom: 16, borderColor: 'var(--good)44' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                <Label style={{ marginBottom: 0 }}>Optimized Prompt</Label>
                <div style={{ display: 'flex', gap: 8 }}>
                  <Badge variant="good">{result.examples_used} examples</Badge>
                  <Badge variant="pending">{result.duration_ms}ms</Badge>
                </div>
              </div>
              <pre style={{
                whiteSpace: 'pre-wrap', wordBreak: 'break-word',
                fontFamily: 'var(--font-mono)', fontSize: 11,
                color: 'var(--text)', lineHeight: 1.8,
                maxHeight: 320, overflowY: 'auto',
                background: 'var(--surface-2)',
                padding: 12, borderRadius: 'var(--radius)',
              }}>
                {result.optimized_prompt}
              </pre>
              <button
                onClick={() => navigator.clipboard.writeText(result.optimized_prompt)}
                style={{
                  marginTop: 8, fontSize: 11, color: 'var(--accent)',
                  background: 'none', border: 'none', cursor: 'pointer',
                }}
              >
                ⎘ Copy to clipboard
              </button>
            </Card>
          )}

          <div style={{ fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--text-muted)', fontWeight: 600, marginBottom: 12 }}>
            Version History {selectedId && `— ${selectedId}`}
          </div>

          {loadingHistory ? (
            <div style={{ display: 'flex', justifyContent: 'center', padding: 24 }}>
              <Spinner size={20} />
            </div>
          ) : history.length === 0 ? (
            <div style={{ fontSize: 12, color: 'var(--text-muted)', textAlign: 'center', padding: 24 }}>
              No versions yet for this prompt ID.
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {history.map((v, i) => (
                <VersionCard key={v.id} version={v} isLatest={i === 0} />
              ))}
            </div>
          )}
        </div>
      </div>

      {toast && <Toast message={toast.message} type={toast.type} onClose={() => setToast(null)} />}
    </div>
  )
}

function VersionCard({ version, isLatest }) {
  const [expanded, setExpanded] = useState(false)
  const good = version.good_count_at_creation
  const bad = version.bad_count_at_creation
  const total = good + bad
  const rate = total > 0 ? Math.round(good / total * 100) : 0

  return (
    <Card style={{
      borderColor: isLatest ? 'var(--accent)44' : 'var(--border)',
      padding: '12px 16px',
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          {isLatest && <Badge variant="default">latest</Badge>}
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: 12 }}>{version.version_tag}</span>
        </div>
        <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
          <Badge variant="good">{good}✅</Badge>
          <Badge variant="bad">{bad}❌</Badge>
          <Badge variant={rate >= 70 ? 'good' : rate >= 40 ? 'edited' : 'bad'}>{rate}%</Badge>
          <button
            onClick={() => setExpanded(v => !v)}
            style={{
              background: 'none', border: '1px solid var(--border)',
              borderRadius: 'var(--radius)', color: 'var(--text-muted)',
              cursor: 'pointer', fontSize: 11, padding: '3px 8px',
            }}
          >
            {expanded ? 'hide' : 'view'}
          </button>
        </div>
      </div>
      <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>
        {version.optimizer} · {new Date(version.created_at).toLocaleString()}
      </div>
      {expanded && (
        <pre style={{
          marginTop: 12, whiteSpace: 'pre-wrap', wordBreak: 'break-word',
          fontFamily: 'var(--font-mono)', fontSize: 11,
          color: 'var(--text-muted)', maxHeight: 200, overflowY: 'auto',
          background: 'var(--surface-2)', padding: 10, borderRadius: 'var(--radius)',
        }}>
          {version.prompt_text}
        </pre>
      )}
    </Card>
  )
}
