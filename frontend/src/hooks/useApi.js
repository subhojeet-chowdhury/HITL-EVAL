/**
 * frontend/src/hooks/useApi.js
 * ─────────────────────────────
 * Thin wrapper around fetch() for talking to the FastAPI backend.
 *
 * LESSON — Why abstract fetch()?
 * Raw fetch() is verbose and error-prone:
 *   - You must manually check response.ok
 *   - You must manually set Content-Type headers
 *   - Error handling is inconsistent
 *
 * This module centralises all API calls in one place so:
 *   - Base URL changes in one spot
 *   - Error handling is consistent
 *   - Each function has a clear, named purpose (easier to read in components)
 */

const BASE = '/api'

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  })

  // 204 = No Content (queue empty) — return null explicitly
  if (res.status === 204) return null

  const data = await res.json()

  if (!res.ok) {
    // FastAPI validation errors have a `detail` field
    const msg = data?.detail || `HTTP ${res.status}`
    throw new Error(typeof msg === 'string' ? msg : JSON.stringify(msg))
  }

  return data
}

// ── Ingest ────────────────────────────────────────────────────────────────────

export async function ingestItem({ prompt, output, promptId, model, metadata }) {
  return request('/ingest/', {
    method: 'POST',
    body: JSON.stringify({
      prompt, output,
      prompt_id: promptId,
      model: model || null,
      metadata: metadata || null,
    }),
  })
}

// ── Labeling ──────────────────────────────────────────────────────────────────

/**
 * Pop the next item from the queue.
 * Returns null if the queue is empty (after server-side timeout).
 */
export async function fetchNextItem() {
  return request('/label/next')
}

export async function submitLabel({ itemId, verdict, correctedOutput, note, labelerId }) {
  return request(`/label/${itemId}`, {
    method: 'POST',
    body: JSON.stringify({
      verdict,
      corrected_output: correctedOutput || null,
      note: note || null,
      labeler_id: labelerId || null,
    }),
  })
}

export async function skipItem(itemId) {
  return request(`/label/${itemId}/skip`, { method: 'POST' })
}

// ── Stats ─────────────────────────────────────────────────────────────────────

export async function fetchOverviewStats() {
  return request('/stats/overview')
}

export async function fetchPromptStats(promptId) {
  return request(`/stats/prompt/${promptId}`)
}

export async function fetchPromptIds() {
  return request('/stats/prompts')
}

// ── Optimizer ─────────────────────────────────────────────────────────────────

export async function runOptimizer({ promptId, basePrompt, minLabels }) {
  return request(`/optimize/${promptId}`, {
    method: 'POST',
    body: JSON.stringify({ base_prompt: basePrompt, min_labels: minLabels || 20 }),
  })
}

export async function fetchOptimizationHistory(promptId) {
  return request(`/optimize/${promptId}/history`)
}

// ── Health ────────────────────────────────────────────────────────────────────

export async function checkHealth() {
  return request('/ingest/health')
}
