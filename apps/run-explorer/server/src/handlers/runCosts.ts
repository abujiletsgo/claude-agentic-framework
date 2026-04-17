import { CORS_HEADERS } from '../config'
import { getRunCosts } from '../services/costTracker'
import type { ApiError } from '../../../shared/types'

export async function handleGetRunCosts(runId: string): Promise<Response> {
  try {
    const costs = await getRunCosts(runId)
    if (!costs) {
      const body: ApiError = { error: 'No cost data for this run', code: 404 }
      return new Response(JSON.stringify(body), { status: 404, headers: CORS_HEADERS })
    }
    return new Response(JSON.stringify(costs), { headers: CORS_HEADERS })
  } catch (err) {
    console.error('runCosts handler error:', err)
    return new Response(JSON.stringify({ error: 'internal server error' }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    })
  }
}
