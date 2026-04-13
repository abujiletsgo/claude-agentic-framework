import { readFile } from 'fs/promises'
import { join } from 'path'
import { ORCH_BASE_DIR } from '../config'
import type { OrchEvent } from '../../../shared/types'

export async function readOrchEvents(id: string, basePath?: string): Promise<OrchEvent[]> {
  const base = basePath ?? ORCH_BASE_DIR
  const filePath = join(base, id, 'events.jsonl')
  let raw: string
  try {
    raw = await readFile(filePath, 'utf-8')
  } catch {
    return []  // file doesn't exist — normal for old runs
  }
  const events: OrchEvent[] = []
  for (const line of raw.split('\n')) {
    const trimmed = line.trim()
    if (!trimmed) continue
    try {
      const parsed = JSON.parse(trimmed) as Record<string, unknown>
      if (typeof parsed['ts'] === 'string' && typeof parsed['agent'] === 'string') {
        events.push({
          ts: parsed['ts'] as string,
          agent: parsed['agent'] as string,
          status: (parsed['status'] as OrchEvent['status']) ?? 'running',
          summary: (parsed['summary'] as string) ?? '',
          wave: typeof parsed['wave'] === 'number' ? parsed['wave'] : undefined,
          orch_id: typeof parsed['orch_id'] === 'string' ? parsed['orch_id'] : undefined,
          reason: typeof parsed['reason'] === 'string' ? parsed['reason'] : undefined,
        })
      }
    } catch {
      // skip malformed line
    }
  }
  // newest first
  return events.reverse()
}
