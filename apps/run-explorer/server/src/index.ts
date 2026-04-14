import { PORT, CORS_HEADERS } from './config'
import { handleGetRuns, handleGetRunDetail } from './handlers/runs'
import { handleGetLeadOutput } from './handlers/leads'
import { handleCompare } from './handlers/compare'
import { handleGetEvents } from './handlers/events'
import { handleGetOrchEvents } from './handlers/orchEvents'
import {
  wsClients,
  dbGetRecentEvents,
  handleGetLiveEvents,
  handleGetLiveFilterOptions,
  handlePostLiveEvent,
  handlePostLiveEventRespond,
} from './handlers/live'
import {
  handleGetCostSummary,
  handleGetCostDaily,
  handleGetCostProjection,
  handlePostCost,
} from './handlers/costs'
import { handleGetSessions, handleGetSessionDetail } from './handlers/sessions'
import type { ApiError } from '../../shared/types'

const server = Bun.serve({
  port: PORT,

  async fetch(req: Request): Promise<Response> {
    const url = new URL(req.url)
    const { pathname } = url

    // OPTIONS preflight
    if (req.method === 'OPTIONS') {
      return new Response(null, { status: 204, headers: CORS_HEADERS })
    }

    // WebSocket upgrade for /stream
    if (pathname === '/stream') {
      const success = server.upgrade(req)
      if (success) {
        return new Response()
      }
    }

    // GET /api/runs
    if (req.method === 'GET' && pathname === '/api/runs') {
      return handleGetRuns()
    }

    // GET /api/runs/:id/leads/:leadName
    const leadMatch = pathname.match(/^\/api\/runs\/([^/]+)\/leads\/([^/]+)$/)
    if (req.method === 'GET' && leadMatch) {
      return handleGetLeadOutput(leadMatch[1] ?? '', leadMatch[2] ?? '')
    }

    // GET /api/runs/:id/events
    const eventsMatch = pathname.match(/^\/api\/runs\/([^/]+)\/events$/)
    if (req.method === 'GET' && eventsMatch) {
      return handleGetOrchEvents(eventsMatch[1] ?? '')
    }

    // GET /api/runs/:id
    const runMatch = pathname.match(/^\/api\/runs\/([^/]+)$/)
    if (req.method === 'GET' && runMatch) {
      return handleGetRunDetail(runMatch[1] ?? '')
    }

    // GET /api/compare?a=...&b=...
    if (req.method === 'GET' && pathname === '/api/compare') {
      return handleCompare(url.searchParams.get('a') ?? '', url.searchParams.get('b') ?? '')
    }

    // GET /api/events/recent
    if (req.method === 'GET' && pathname === '/api/events/recent') {
      return handleGetEvents()
    }

    // ── Live events (observability) ──────────────────────────────

    // GET /api/live/events
    if (req.method === 'GET' && pathname === '/api/live/events') {
      return handleGetLiveEvents(url)
    }

    // GET /api/live/filter-options
    if (req.method === 'GET' && pathname === '/api/live/filter-options') {
      return handleGetLiveFilterOptions()
    }

    // POST /api/live/events
    if (req.method === 'POST' && pathname === '/api/live/events') {
      return handlePostLiveEvent(req)
    }

    // POST /api/live/events/:id/respond
    const respondMatch = pathname.match(/^\/api\/live\/events\/(\d+)\/respond$/)
    if (req.method === 'POST' && respondMatch) {
      const id = parseInt(respondMatch[1] ?? '0')
      return handlePostLiveEventRespond(req, id)
    }

    // ── Cost tracking ────────────────────────────────────────────

    // GET /api/costs/summary
    if (req.method === 'GET' && pathname === '/api/costs/summary') {
      return handleGetCostSummary(url)
    }

    // GET /api/costs/daily
    if (req.method === 'GET' && pathname === '/api/costs/daily') {
      return handleGetCostDaily(url)
    }

    // GET /api/costs/projection
    if (req.method === 'GET' && pathname === '/api/costs/projection') {
      return handleGetCostProjection(url)
    }

    // POST /api/costs
    if (req.method === 'POST' && pathname === '/api/costs') {
      return handlePostCost(req)
    }

    // ── Sessions ─────────────────────────────────────────────────

    // GET /api/sessions
    if (req.method === 'GET' && pathname === '/api/sessions') {
      return handleGetSessions()
    }

    // GET /api/sessions/:id
    const sessionMatch = pathname.match(/^\/api\/sessions\/([^/]+)$/)
    if (req.method === 'GET' && sessionMatch) {
      return handleGetSessionDetail(sessionMatch[1] ?? '')
    }

    // 404
    const body: ApiError = { error: 'Not found', code: 404 }
    return new Response(JSON.stringify(body), { status: 404, headers: CORS_HEADERS })
  },

  websocket: {
    open(ws) {
      console.log('WebSocket client connected')
      wsClients.add(ws)

      // Send last 300 events as initial payload
      const events = dbGetRecentEvents(300)
      ws.send(JSON.stringify({ type: 'initial', data: events }))
    },

    message(ws, message) {
      console.log('Received message:', message)
    },

    close(ws) {
      console.log('WebSocket client disconnected')
      wsClients.delete(ws)
    },

  },
})

console.log(`CAF Run Explorer server on :${PORT}`)
console.log(`WebSocket endpoint: ws://localhost:${PORT}/stream`)
