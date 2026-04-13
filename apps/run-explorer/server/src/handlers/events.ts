import { CORS_HEADERS, EVENTS_DB_PATH, RECENT_EVENTS_LIMIT } from '../config'
import { getRecentEvents } from '../services/dbReader'

export async function handleGetEvents(): Promise<Response> {
  const events = getRecentEvents(EVENTS_DB_PATH, RECENT_EVENTS_LIMIT)
  return new Response(JSON.stringify(events), { headers: CORS_HEADERS })
}
