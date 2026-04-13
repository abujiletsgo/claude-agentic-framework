import { CORS_HEADERS } from '../config'
import { listRuns, getRunDetail } from '../services/runParser'
import type { ApiError } from '../../../shared/types'

export async function handleGetRuns(): Promise<Response> {
  const runs = await listRuns()
  return new Response(JSON.stringify(runs), { headers: CORS_HEADERS })
}

export async function handleGetRunDetail(id: string): Promise<Response> {
  const detail = await getRunDetail(id)
  if (!detail) {
    const body: ApiError = { error: 'Run not found', code: 404 }
    return new Response(JSON.stringify(body), { status: 404, headers: CORS_HEADERS })
  }
  return new Response(JSON.stringify(detail), { headers: CORS_HEADERS })
}
