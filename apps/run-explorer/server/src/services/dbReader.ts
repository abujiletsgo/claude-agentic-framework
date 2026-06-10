import { Database } from 'bun:sqlite'
import type { Event } from '../../../shared/types'

interface EventRow {
  id: number
  hook_event_type: string
  payload: string
  timestamp: number
}

export function getRecentEvents(dbPath: string, limit: number): Event[] {
  try {
    const db = new Database(dbPath, { readonly: true })
    const rows = db
      .query<EventRow, []>(
        `SELECT id, hook_event_type, payload, timestamp
         FROM events
         ORDER BY timestamp DESC
         LIMIT ${limit}`
      )
      .all()
    db.close()
    return rows.map((row) => ({
      id: row.id,
      type: row.hook_event_type,
      timestamp: new Date(row.timestamp).toISOString(),
      metadata: row.payload.slice(0, 200),
    }))
  } catch {
    return []
  }
}
