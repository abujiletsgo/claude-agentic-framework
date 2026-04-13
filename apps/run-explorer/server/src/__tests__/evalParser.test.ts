import { describe, it, expect } from 'bun:test'
import { parseEvalScore, parseEvalVerdict } from '../services/evalParser'

describe('parseEvalScore', () => {
  it('"Score: 78" → 78', () => {
    expect(parseEvalScore('Score: 78')).toBe(78)
  })

  it('"78/100" → 78', () => {
    expect(parseEvalScore('78/100')).toBe(78)
  })

  it('no match → null', () => {
    expect(parseEvalScore('no score here')).toBeNull()
  })
})

describe('parseEvalVerdict', () => {
  it('text with "SHIP" → "SHIP"', () => {
    expect(parseEvalVerdict('The verdict is SHIP')).toBe('SHIP')
  })

  it('"NEEDS REWORK" → "NEEDS REWORK"', () => {
    expect(parseEvalVerdict('This NEEDS REWORK before merging')).toBe('NEEDS REWORK')
  })

  it('neither → null', () => {
    expect(parseEvalVerdict('no verdict here')).toBeNull()
  })
})
