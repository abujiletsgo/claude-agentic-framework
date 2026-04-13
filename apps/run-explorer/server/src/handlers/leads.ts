import { CORS_HEADERS } from '../config'
import { getLeadOutput } from '../services/runParser'
import type { ApiError } from '../../../shared/types'

export async function handleGetLeadOutput(id: string, leadName: string): Promise<Response> {
  const output = await getLeadOutput(id, leadName)
  if (!output) {
    const body: ApiError = { error: 'Lead output not found', code: 404 }
    return new Response(JSON.stringify(body), { status: 404, headers: CORS_HEADERS })
  }
  return new Response(JSON.stringify(output), { headers: CORS_HEADERS })
}
