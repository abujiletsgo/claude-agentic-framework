import { describe, it, expect } from 'bun:test'
import { estimateTokens } from '../services/tokenEstimator'

describe('estimateTokens', () => {
  it('empty string → 0', () => {
    expect(estimateTokens('')).toBe(0)
  })

  it('"hello world" (2 words) → Math.ceil(2*1.3)=3', () => {
    expect(estimateTokens('hello world')).toBe(3)
  })

  it('100 words → 130', () => {
    const text = Array.from({ length: 100 }, (_, i) => `word${i}`).join(' ')
    expect(estimateTokens(text)).toBe(130)
  })
})
