import { join } from 'path'
import { CORS_HEADERS, ORCH_BASE_DIR } from '../config'
import { getRunDetail } from '../services/runParser'
import type { ComparisonResult, MetricComparison, QualityComparison, ApiError } from '../../../shared/types'

function compareMetric(a: number, b: number, lowerWins: boolean): MetricComparison {
  const threshold = 0.05
  const diff = Math.abs(a - b)
  const base = Math.max(a, b, 1)
  const winner: 'a' | 'b' | 'tie' =
    diff / base <= threshold
      ? 'tie'
      : lowerWins
        ? a < b ? 'a' : 'b'
        : a > b ? 'a' : 'b'
  return { a, b, winner }
}

function compareQuality(a: number | null, b: number | null): QualityComparison {
  if (a === null && b === null) return { a, b, winner: null }
  const threshold = 0.05
  if (a !== null && b !== null) {
    const diff = Math.abs(a - b)
    const base = Math.max(a, b, 1)
    const winner: 'a' | 'b' | 'tie' =
      diff / base <= threshold ? 'tie' : a > b ? 'a' : 'b'
    return { a, b, winner }
  }
  // one is null
  const winner: 'a' | 'b' | 'tie' = a !== null ? 'a' : 'b'
  return { a, b, winner }
}

export async function handleCompare(a: string | null, b: string | null): Promise<Response> {
  if (!a || !b) {
    const body: ApiError = { error: 'Missing required params: a, b', code: 400 }
    return new Response(JSON.stringify(body), { status: 400, headers: CORS_HEADERS })
  }

  const [runA, runB] = await Promise.all([getRunDetail(a), getRunDetail(b)])

  if (!runA) {
    const body: ApiError = { error: `Run not found: ${a}`, code: 404 }
    return new Response(JSON.stringify(body), { status: 404, headers: CORS_HEADERS })
  }
  if (!runB) {
    const body: ApiError = { error: `Run not found: ${b}`, code: 404 }
    return new Response(JSON.stringify(body), { status: 404, headers: CORS_HEADERS })
  }

  const wallClockA = await import('../services/runParser').then((m) =>
    m.parseWallClockSeconds(join(ORCH_BASE_DIR, a))
  )
  const wallClockB = await import('../services/runParser').then((m) =>
    m.parseWallClockSeconds(join(ORCH_BASE_DIR, b))
  )

  const result: ComparisonResult = {
    runA,
    runB,
    metrics: {
      wallClockSeconds: compareMetric(wallClockA, wallClockB, true),
      tokenEstimate: compareMetric(runA.tokenEstimate, runB.tokenEstimate, true),
      qualityScore: compareQuality(runA.evaluationScore, runB.evaluationScore),
    },
  }

  return new Response(JSON.stringify(result), { headers: CORS_HEADERS })
}
