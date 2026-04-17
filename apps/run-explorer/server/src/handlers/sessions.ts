import { CORS_HEADERS } from '../config'
import { listSessions, getSessionDetail } from '../services/sessionParser'
import type { ApiError } from '../../../shared/types'

export async function handleGetSessions(): Promise<Response> {
  try {
    const sessions = await listSessions()
    return new Response(JSON.stringify(sessions), { headers: CORS_HEADERS })
  } catch (err) {
    console.error('sessions handler error:', err)
    return new Response(JSON.stringify({ error: 'internal server error' }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    })
  }
}

export async function handleGetSessionDetail(id: string): Promise<Response> {
  const detail = await getSessionDetail(id)
  if (!detail) {
    const body: ApiError = { error: 'Session not found', code: 404 }
    return new Response(JSON.stringify(body), { status: 404, headers: CORS_HEADERS })
  }
  return new Response(JSON.stringify(detail), { headers: CORS_HEADERS })
}

export async function handleGetRunSessions(runId: string): Promise<Response> {
  try {
    const sessions = await listSessions()
    const filtered = sessions.filter((s) => s.orchRunId === runId)
    return new Response(JSON.stringify(filtered), { headers: CORS_HEADERS })
  } catch (err) {
    console.error('sessions handler error:', err)
    return new Response(JSON.stringify({ error: 'internal server error' }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    })
  }
}
