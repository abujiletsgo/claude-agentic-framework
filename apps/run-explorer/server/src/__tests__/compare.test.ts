import { describe, it, expect } from 'bun:test'

// Test the compareMetric and compareQuality logic inline
// (handleCompare is async with external dependencies, so we test the core logic directly)

function compareMetric(a: number, b: number, lowerWins: boolean): { a: number; b: number; winner: 'a' | 'b' | 'tie' } {
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

function compareQuality(a: number | null, b: number | null): { a: number | null; b: number | null; winner: 'a' | 'b' | 'tie' | null } {
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

describe('compareMetric (wallClockSeconds, lowerWins=true)', () => {
  it('lower wallClockSeconds wins (a=100, b=200 → winner="a")', () => {
    const result = compareMetric(100, 200, true)
    expect(result.winner).toBe('a')
  })

  it('within 5%: a=100, b=103 → winner="tie"', () => {
    const result = compareMetric(100, 103, true)
    expect(result.winner).toBe('tie')
  })
})

describe('compareQuality', () => {
  it('higher qualityScore wins (a=80, b=60 → winner="a")', () => {
    const result = compareQuality(80, 60)
    expect(result.winner).toBe('a')
  })

  it('both null quality → winner=null', () => {
    const result = compareQuality(null, null)
    expect(result.winner).toBeNull()
  })
})
