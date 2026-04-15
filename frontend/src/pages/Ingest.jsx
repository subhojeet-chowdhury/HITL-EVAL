/**
 * frontend/src/pages/Ingest.jsx
 * ───────────────────────────────
 * A developer UI for manually ingesting LLM outputs.
 *
 * LESSON — Why have a UI for this?
 * In production, your application calls POST /api/ingest programmatically.
 * But during development and demos, having a form to manually push items
 * into the queue lets you test the full pipeline without writing any code.
 *
 * This page also serves as living documentation of the ingest API contract.
 */

import React, { useState } from 'react'
import { ingestItem } from '../hooks/useApi.js'
import { Button, Card, Input, Label, Spinner, Textarea, Toast } from '../components/UI.jsx'

const EXAMPLES = [
  {
    label: 'Summarisation',
    promptId: 'summariser_v1',
    prompt: 'Summarise the following text in 2-3 sentences:\n\nArtificial intelligence is transforming industries at an unprecedented pace. From healthcare diagnostics to autonomous vehicles, AI systems are being deployed in high-stakes environments where accuracy and reliability are paramount. The challenge for organizations is not just adopting these technologies but building the evaluation frameworks needed to trust them.',
    output: 'AI is rapidly being adopted across industries including healthcare and transportation. Organizations face the challenge of building reliable evaluation frameworks as AI systems are deployed in critical contexts.',
    model: 'gpt-4o',
  },
  {
    label: 'Code Generation',
    promptId: 'codegen_v2',
    prompt: 'Write a Python function that takes a list of numbers and returns the median.',
    output: 'def median(nums):\n    sorted_nums = sorted(nums)\n    n = len(sorted_nums)\n    mid = n // 2\n    if n % 2 == 0:\n        return (sorted_nums[mid - 1] + sorted_nums[mid]) / 2\n    return sorted_nums[mid]',
    model: 'claude-3-5-sonnet',
  },
  {
    label: 'Customer Support (Bad)',
    promptId: 'support_v1',
    prompt: 'Customer message: "My order has been stuck in processing for 5 days. What do I do?"',
    output: "Orders can take 3-7 business days to process depending on inventory. Please check your email for updates. If you haven't received an email, your order is still processing.",
    model: 'gpt-3.5-turbo',
  },
]

export default function Ingest() {
  const [prompt, setPrompt]     = useState('')
  const [output, setOutput]     = useState('')
  const [promptId, setPromptId] = useState('')
  const [model, setModel]       = useState('')
  const [loading, setLoading]   = useState(false)
  const [toast, setToast]       = useState(null)
  const [lastId, setLastId]     = useState(null)

  const handleSubmit = async () => {
    if (!prompt.trim() || !output.trim() || !promptId.trim()) {
      setToast({ message: 'Prompt, Output, and Prompt ID are required', type: 'error' })
      return
    }
    setLoading(true)
    try {
      const res = await ingestItem({ prompt, output, promptId, model: model || null })
      setLastId(res.item_id)
      setToast({ message: `✅ Enqueued! Queue depth: ${res.queue_depth}`, type: 'success' })
      // Clear form
      setPrompt('')
      setOutput('')
    } catch (err) {
      setToast({ message: err.message, type: 'error' })
    } finally {
      setLoading(false)
    }
  }

  const loadExample = (ex) => {
    setPrompt(ex.prompt)
    setOutput(ex.output)
    setPromptId(ex.promptId)
    setModel(ex.model || '')
  }

  return (
    <div style={{ maxWidth: 800, margin: '0 auto', padding: '32px 24px' }}>
      <h1 style={{ fontSize: 20, fontWeight: 700, marginBottom: 6 }}>Ingest Item</h1>
      <p style={{ color: 'var(--text-muted)', fontSize: 13, marginBottom: 24 }}>
        Manually push an LLM output into the evaluation queue. In production,
        your app calls <code style={{ color: 'var(--accent)' }}>POST /api/ingest/</code> directly.
      </p>

      {/* Example loader */}
      <Card style={{ marginBottom: 20 }}>
        <Label>Load an example</Label>
        <div style={{ display: 'flex', gap: 8 }}>
          {EXAMPLES.map(ex => (
            <button
              key={ex.label}
              onClick={() => loadExample(ex)}
              style={{
                padding: '6px 14px', fontSize: 12, borderRadius: 'var(--radius)',
                background: 'var(--surface-2)', color: 'var(--text-muted)',
                border: '1px solid var(--border)', cursor: 'pointer',
              }}
            >
              {ex.label}
            </button>
          ))}
        </div>
      </Card>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 12 }}>
        <div>
          <Label>Prompt ID *</Label>
          <Input value={promptId} onChange={setPromptId} placeholder="e.g. summariser_v3" />
          <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>
            Logical name for your prompt — groups items for the optimizer.
          </div>
        </div>
        <div>
          <Label>Model</Label>
          <Input value={model} onChange={setModel} placeholder="e.g. gpt-4o, claude-3-5-sonnet" />
        </div>
      </div>

      <div style={{ marginBottom: 12 }}>
        <Label>Prompt *</Label>
        <Textarea value={prompt} onChange={setPrompt} placeholder="The prompt sent to the LLM..." rows={5} />
      </div>

      <div style={{ marginBottom: 20 }}>
        <Label>LLM Output *</Label>
        <Textarea value={output} onChange={setOutput} placeholder="The model's response to evaluate..." rows={6} />
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
        <Button
          variant="primary"
          onClick={handleSubmit}
          disabled={loading}
          style={{ padding: '10px 28px' }}
        >
          {loading ? <><Spinner size={14} /> Enqueueing...</> : '↑ Enqueue for Labeling'}
        </Button>
        {lastId && (
          <div style={{ fontSize: 12, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
            Last: {lastId.slice(0, 12)}...
          </div>
        )}
      </div>

      {/* API reference */}
      <Card style={{ marginTop: 32, borderColor: 'var(--border)' }}>
        <Label>API Reference — programmatic usage</Label>
        <pre style={{
          fontFamily: 'var(--font-mono)', fontSize: 11,
          color: 'var(--text-muted)', lineHeight: 1.8,
          whiteSpace: 'pre', overflowX: 'auto',
        }}>
{`import httpx

client = httpx.Client(base_url="http://localhost:8000")

response = client.post("/api/ingest/", json={
    "prompt":    "Your prompt here",
    "output":    "The LLM's response",
    "prompt_id": "my_prompt_v1",
    "model":     "gpt-4o",
    "metadata":  {"user_id": "u_123"}
})

print(response.json())
# → {"item_id": "uuid...", "queue_depth": 3, "message": "..."}`}
        </pre>
      </Card>

      {toast && <Toast message={toast.message} type={toast.type} onClose={() => setToast(null)} />}
    </div>
  )
}
