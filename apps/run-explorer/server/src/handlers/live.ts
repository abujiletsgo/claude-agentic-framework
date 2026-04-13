import { Database } from 'bun:sqlite'
import { CORS_HEADERS, EVENTS_DB_PATH } from '../config'

// Types mirroring the observability server shapes

export interface HumanInTheLoop {
  question: string
  responseWebSocketUrl: string
  type: 'question' | 'permission' | 'choice'
  choices?: string[]
  timeout?: number
  requiresResponse?: boolean
}

export interface HumanInTheLoopResponse {
  response?: string
  permission?: boolean
  choice?: string
  hookEvent: any
  respondedAt: number
  respondedBy?: string
}

export interface HumanInTheLoopStatus {
  status: 'pending' | 'responded' | 'timeout' | 'error'
  respondedAt?: number
  response?: HumanInTheLoopResponse
}

export interface HookEvent {
  id?: number
  source_app: string
  session_id: string
  hook_event_type: string
  payload: Record<string, any>
  chat?: any[]
  summary?: string
  timestamp?: number
  model_name?: string
  humanInTheLoop?: HumanInTheLoop
  humanInTheLoopStatus?: HumanInTheLoopStatus
}

export interface FilterOptions {
  source_apps: string[]
  session_ids: string[]
  hook_event_types: string[]
}

// Store WebSocket clients (exported so index.ts can broadcast)
export const wsClients = new Set<any>()

// ── Helper: open a writable DB connection ────────────────────────────────────

function openDb(): Database {
  const db = new Database(EVENTS_DB_PATH)
  db.exec('PRAGMA journal_mode = WAL')
  db.exec('PRAGMA synchronous = NORMAL')
  // Ensure columns exist (migration guard matching observability server)
  try {
    const columns = db.prepare('PRAGMA table_info(events)').all() as any[]
    const has = (name: string) => columns.some((c: any) => c.name === name)
    if (!has('chat')) db.exec('ALTER TABLE events ADD COLUMN chat TEXT')
    if (!has('summary')) db.exec('ALTER TABLE events ADD COLUMN summary TEXT')
    if (!has('humanInTheLoop')) db.exec('ALTER TABLE events ADD COLUMN humanInTheLoop TEXT')
    if (!has('humanInTheLoopStatus')) db.exec('ALTER TABLE events ADD COLUMN humanInTheLoopStatus TEXT')
    if (!has('model_name')) db.exec('ALTER TABLE events ADD COLUMN model_name TEXT')
  } catch {
    // table may not exist yet; callers will handle errors
  }
  return db
}

// ── Row mapper ───────────────────────────────────────────────────────────────

function mapRow(row: any): HookEvent {
  return {
    id: row.id,
    source_app: row.source_app,
    session_id: row.session_id,
    hook_event_type: row.hook_event_type,
    payload: JSON.parse(row.payload),
    chat: row.chat ? JSON.parse(row.chat) : undefined,
    summary: row.summary || undefined,
    timestamp: row.timestamp,
    humanInTheLoop: row.humanInTheLoop ? JSON.parse(row.humanInTheLoop) : undefined,
    humanInTheLoopStatus: row.humanInTheLoopStatus ? JSON.parse(row.humanInTheLoopStatus) : undefined,
    model_name: row.model_name || undefined,
  }
}

// ── DB helpers ───────────────────────────────────────────────────────────────

export function dbGetRecentEvents(limit: number = 300): HookEvent[] {
  try {
    const db = openDb()
    const rows = db
      .prepare(
        `SELECT id, source_app, session_id, hook_event_type, payload, chat, summary, timestamp, humanInTheLoop, humanInTheLoopStatus, model_name
         FROM events
         ORDER BY timestamp DESC
         LIMIT ?`
      )
      .all(limit) as any[]
    db.close()
    return rows.map(mapRow).reverse()
  } catch {
    return []
  }
}

export function dbGetFilterOptions(): FilterOptions {
  try {
    const db = openDb()
    const sourceApps = db.prepare('SELECT DISTINCT source_app FROM events ORDER BY source_app').all() as { source_app: string }[]
    const sessionIds = db.prepare('SELECT DISTINCT session_id FROM events ORDER BY session_id DESC LIMIT 300').all() as { session_id: string }[]
    const hookEventTypes = db.prepare('SELECT DISTINCT hook_event_type FROM events ORDER BY hook_event_type').all() as { hook_event_type: string }[]
    db.close()
    return {
      source_apps: sourceApps.map((r) => r.source_app),
      session_ids: sessionIds.map((r) => r.session_id),
      hook_event_types: hookEventTypes.map((r) => r.hook_event_type),
    }
  } catch {
    return { source_apps: [], session_ids: [], hook_event_types: [] }
  }
}

export function dbInsertEvent(event: HookEvent): HookEvent {
  const db = openDb()
  const stmt = db.prepare(
    `INSERT INTO events (source_app, session_id, hook_event_type, payload, chat, summary, timestamp, humanInTheLoop, humanInTheLoopStatus, model_name)
     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`
  )

  const timestamp = event.timestamp || Date.now()

  let humanInTheLoopStatus = event.humanInTheLoopStatus
  if (event.humanInTheLoop && !humanInTheLoopStatus) {
    humanInTheLoopStatus = { status: 'pending' }
  }

  const result = stmt.run(
    event.source_app,
    event.session_id,
    event.hook_event_type,
    JSON.stringify(event.payload),
    event.chat ? JSON.stringify(event.chat) : null,
    event.summary || null,
    timestamp,
    event.humanInTheLoop ? JSON.stringify(event.humanInTheLoop) : null,
    humanInTheLoopStatus ? JSON.stringify(humanInTheLoopStatus) : null,
    event.model_name || null
  )

  db.close()

  return {
    ...event,
    id: result.lastInsertRowid as number,
    timestamp,
    humanInTheLoopStatus,
  }
}

export function dbUpdateEventHITLResponse(id: number, response: HumanInTheLoopResponse): HookEvent | null {
  const db = openDb()
  const status: HumanInTheLoopStatus = {
    status: 'responded',
    respondedAt: response.respondedAt,
    response,
  }

  db.prepare('UPDATE events SET humanInTheLoopStatus = ? WHERE id = ?').run(JSON.stringify(status), id)

  const row = db
    .prepare(
      `SELECT id, source_app, session_id, hook_event_type, payload, chat, summary, timestamp, humanInTheLoop, humanInTheLoopStatus, model_name
       FROM events WHERE id = ?`
    )
    .get(id) as any

  db.close()

  if (!row) return null
  return mapRow(row)
}

// ── sendResponseToAgent (HITL relay) ────────────────────────────────────────

async function sendResponseToAgent(wsUrl: string, response: HumanInTheLoopResponse): Promise<void> {
  console.log(`[HITL] Connecting to agent WebSocket: ${wsUrl}`)

  return new Promise((resolve, reject) => {
    let ws: WebSocket | null = null
    let isResolved = false

    const cleanup = () => {
      if (ws) {
        try { ws.close() } catch { /* ignore */ }
      }
    }

    try {
      ws = new WebSocket(wsUrl)

      ws.onopen = () => {
        if (isResolved) return
        console.log('[HITL] WebSocket connection opened, sending response...')
        try {
          ws!.send(JSON.stringify(response))
          console.log('[HITL] Response sent successfully')
          setTimeout(() => {
            cleanup()
            if (!isResolved) { isResolved = true; resolve() }
          }, 500)
        } catch (error) {
          console.error('[HITL] Error sending message:', error)
          cleanup()
          if (!isResolved) { isResolved = true; reject(error) }
        }
      }

      ws.onerror = (error) => {
        console.error('[HITL] WebSocket error:', error)
        cleanup()
        if (!isResolved) { isResolved = true; reject(error) }
      }

      ws.onclose = () => { console.log('[HITL] WebSocket connection closed') }

      setTimeout(() => {
        if (!isResolved) {
          console.error('[HITL] Timeout sending response to agent')
          cleanup()
          isResolved = true
          reject(new Error('Timeout sending response to agent'))
        }
      }, 5000)
    } catch (error) {
      console.error('[HITL] Error creating WebSocket:', error)
      cleanup()
      if (!isResolved) { isResolved = true; reject(error) }
    }
  })
}

// ── Broadcast helper ─────────────────────────────────────────────────────────

function broadcast(message: string) {
  wsClients.forEach((client) => {
    try {
      client.send(message)
    } catch {
      wsClients.delete(client)
    }
  })
}

// ── HTTP handlers ────────────────────────────────────────────────────────────

export async function handleGetLiveEvents(url: URL): Promise<Response> {
  const limit = parseInt(url.searchParams.get('limit') || '300')
  const events = dbGetRecentEvents(limit)
  return new Response(JSON.stringify(events), { headers: CORS_HEADERS })
}

export async function handleGetLiveFilterOptions(): Promise<Response> {
  const options = dbGetFilterOptions()
  return new Response(JSON.stringify(options), { headers: CORS_HEADERS })
}

export async function handlePostLiveEvent(req: Request): Promise<Response> {
  try {
    const event = await req.json() as HookEvent

    if (!event.source_app || !event.session_id || !event.hook_event_type || !event.payload) {
      return new Response(JSON.stringify({ error: 'Missing required fields' }), {
        status: 400,
        headers: CORS_HEADERS,
      })
    }

    const savedEvent = dbInsertEvent(event)

    broadcast(JSON.stringify({ type: 'event', data: savedEvent }))

    return new Response(JSON.stringify(savedEvent), { headers: CORS_HEADERS })
  } catch (error) {
    console.error('Error processing event:', error)
    return new Response(JSON.stringify({ error: 'Invalid request' }), {
      status: 400,
      headers: CORS_HEADERS,
    })
  }
}

export async function handlePostLiveEventRespond(req: Request, id: number): Promise<Response> {
  try {
    const response = await req.json() as HumanInTheLoopResponse
    response.respondedAt = Date.now()

    const updatedEvent = dbUpdateEventHITLResponse(id, response)

    if (!updatedEvent) {
      return new Response(JSON.stringify({ error: 'Event not found' }), {
        status: 404,
        headers: CORS_HEADERS,
      })
    }

    if (updatedEvent.humanInTheLoop?.responseWebSocketUrl) {
      try {
        await sendResponseToAgent(updatedEvent.humanInTheLoop.responseWebSocketUrl, response)
      } catch (error) {
        console.error('Failed to send response to agent:', error)
        // Don't fail the request if we can't reach the agent
      }
    }

    broadcast(JSON.stringify({ type: 'event', data: updatedEvent }))

    return new Response(JSON.stringify(updatedEvent), { headers: CORS_HEADERS })
  } catch (error) {
    console.error('Error processing HITL response:', error)
    return new Response(JSON.stringify({ error: 'Invalid request' }), {
      status: 400,
      headers: CORS_HEADERS,
    })
  }
}
