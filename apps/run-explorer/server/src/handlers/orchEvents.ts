import { CORS_HEADERS } from '../config'
import { readOrchEvents } from '../services/orchEventReader'

export async function handleGetOrchEvents(id: string): Promise<Response> {
  const events = await readOrchEvents(id)
  return new Response(JSON.stringify(events), { headers: CORS_HEADERS })
}
