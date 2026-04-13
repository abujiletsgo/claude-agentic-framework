import { CORS_HEADERS } from '../config'
import {
  getCostSummary,
  getDailyBreakdown,
  getCostProjection,
  recordCostEntry,
} from '../services/costTracker'

export async function handleGetCostSummary(url: URL): Promise<Response> {
  const period = (url.searchParams.get('period') || 'week') as 'today' | 'yesterday' | 'week' | 'month' | 'all'
  try {
    const summary = await getCostSummary(period)
    return new Response(JSON.stringify(summary), { headers: CORS_HEADERS })
  } catch (error) {
    console.error('Error getting cost summary:', error)
    return new Response(JSON.stringify({ error: 'Failed to get cost summary' }), {
      status: 500,
      headers: CORS_HEADERS,
    })
  }
}

export async function handleGetCostDaily(url: URL): Promise<Response> {
  const days = parseInt(url.searchParams.get('days') || '7')
  try {
    const daily = await getDailyBreakdown(days)
    return new Response(JSON.stringify(daily), { headers: CORS_HEADERS })
  } catch (error) {
    console.error('Error getting daily breakdown:', error)
    return new Response(JSON.stringify({ error: 'Failed to get daily breakdown' }), {
      status: 500,
      headers: CORS_HEADERS,
    })
  }
}

export async function handleGetCostProjection(url: URL): Promise<Response> {
  const days = parseInt(url.searchParams.get('days') || '7')
  try {
    const projection = await getCostProjection(days)
    return new Response(JSON.stringify(projection), { headers: CORS_HEADERS })
  } catch (error) {
    console.error('Error getting cost projection:', error)
    return new Response(JSON.stringify({ error: 'Failed to get cost projection' }), {
      status: 500,
      headers: CORS_HEADERS,
    })
  }
}

export async function handlePostCost(req: Request): Promise<Response> {
  try {
    const entry = await req.json() as Parameters<typeof recordCostEntry>[0]
    const recorded = await recordCostEntry(entry)
    return new Response(JSON.stringify(recorded), { status: 201, headers: CORS_HEADERS })
  } catch (error) {
    console.error('Error recording cost entry:', error)
    return new Response(JSON.stringify({ error: 'Failed to record cost entry' }), {
      status: 400,
      headers: CORS_HEADERS,
    })
  }
}
