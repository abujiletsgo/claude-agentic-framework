export function parseEvalScore(text: string): number | null {
  const m1 = text.match(/(?:Score:|score:)\s*(\d+)/)
  if (m1 && m1[1] !== undefined) return parseInt(m1[1], 10)
  const m2 = text.match(/(\d+)\s*\/\s*100/)
  if (m2 && m2[1] !== undefined) return parseInt(m2[1], 10)
  return null
}

export function parseEvalVerdict(text: string): 'SHIP' | 'NEEDS REWORK' | null {
  if (text.includes('NEEDS REWORK')) return 'NEEDS REWORK'
  if (text.includes('SHIP')) return 'SHIP'
  return null
}
