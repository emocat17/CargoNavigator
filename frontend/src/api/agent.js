/**
 * Agent Chat API — wraps SSE-streamed POST /agent/chat and GET /agent/*.
 *
 * The chat endpoint returns an SSE stream (text/event-stream).  This module
 * provides both a raw ReadableStream helper for components that need per-token
 * rendering, and a convenience async generator.
 */
const API = import.meta.env.VITE_API_BASE || 'http://localhost:19876'
const BASE = `${API}/api/v1`

/**
 * Start a streaming chat and yield parsed SSE events.
 *
 * Usage:
 *   for await (const { event, data } of streamChat("从福州到厦门怎么走？")) {
 *     if (event === 'token')  appendToMessage(data)
 *     if (event === 'bridge') showBridgeCard(data)
 *     if (event === 'done')   finalize()
 *   }
 *
 * @param {string} message  - User message (may contain [路线上下文] prefix)
 * @returns {AsyncGenerator<{event:string, data:any}, void, void>}
 */
export async function* streamChat(message) {
  const resp = await fetch(`${BASE}/agent/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message }),
  })
  if (!resp.ok) throw new Error(`Agent chat HTTP ${resp.status}`)

  const reader = resp.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })

    const events = buffer.split('\n\n')
    buffer = events.pop()  // keep incomplete last frame

    for (const frame of events) {
      if (!frame.trim()) continue
      const lines = frame.split('\n')
      let eventType = '', dataStr = ''
      for (const line of lines) {
        if (line.startsWith('event: ')) eventType = line.slice(7).trim()
        else if (line.startsWith('data: ')) dataStr = line.slice(6)
      }
      if (!eventType) continue
      let parsed
      try { parsed = JSON.parse(dataStr) } catch { parsed = dataStr }
      yield { event: eventType, data: parsed }
    }
  }
}

/** GET /agent/health — quick liveness check. */
export const getAgentHealth = async () => {
  const resp = await fetch(`${BASE}/agent/health`)
  return resp.json()
}

/** GET /agent/chat/sessions — list chat sessions. */
export const getSessions = async () => {
  const resp = await fetch(`${BASE}/agent/chat/sessions`)
  return resp.json()
}

/** GET /agent/chat/sessions/{id} — single session detail. */
export const getSession = async (sessionId) => {
  const resp = await fetch(`${BASE}/agent/chat/sessions/${sessionId}`)
  return resp.json()
}

/** DELETE /agent/chat/sessions/{id} — remove a session. */
export const deleteSession = async (sessionId) => {
  const resp = await fetch(`${BASE}/agent/chat/sessions/${sessionId}`, { method: 'DELETE' })
  return resp.json()
}
