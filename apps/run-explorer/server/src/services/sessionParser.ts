import { readdir, readFile } from 'fs/promises'
import { join } from 'path'
import { homedir } from 'node:os'

const SESSIONS_DIR = join(homedir(), '.caf', 'sessions')

export interface SessionSummary {
  id: string
  startTime: string
  endTime?: string
  project?: string
  promptCount: number
  status: 'active' | 'ended'
  durationSeconds?: number
}

export interface SessionMessage {
  id: number
  type: string
  content: string
  timestamp: string
}

export interface SessionDetail extends SessionSummary {
  messages: SessionMessage[]
}

// ─── JSONL event shape written by caf-hooks session-recorder ─────────────────

interface RawEvent {
  ts: string      // ISO 8601
  ms: number      // epoch ms
  type: string    // SessionStart | UserPromptSubmit | Stop
  cwd?: string
  prompt?: string
}

// ─── helpers ─────────────────────────────────────────────────────────────────

async function readJsonl(filePath: string): Promise<RawEvent[]> {
  let raw: string
  try {
    raw = await readFile(filePath, 'utf-8')
  } catch {
    return []
  }
  const events: RawEvent[] = []
  for (const line of raw.split('\n')) {
    const t = line.trim()
    if (!t) continue
    try {
      events.push(JSON.parse(t) as RawEvent)
    } catch {
      // skip malformed line
    }
  }
  return events
}

function extractProject(cwd: string | undefined): string | undefined {
  if (!cwd) return undefined
  const parts = cwd.replace(/\/$/, '').split('/')
  return parts[parts.length - 1] || undefined
}

function buildSummary(sessionId: string, events: RawEvent[]): SessionSummary {
  const startEvent = events.find((e) => e.type === 'SessionStart')
  const stopEvent  = events.find((e) => e.type === 'Stop')
  const prompts    = events.filter((e) => e.type === 'UserPromptSubmit')

  const startTime = events[0]?.ts ?? new Date(0).toISOString()
  const endTime   = stopEvent?.ts
  const status: 'active' | 'ended' = stopEvent ? 'ended' : 'active'
  const project   = extractProject(startEvent?.cwd ?? events[0]?.cwd)

  let durationSeconds: number | undefined
  if (events[0] && stopEvent) {
    durationSeconds = Math.round((stopEvent.ms - events[0].ms) / 1000)
  }

  return { id: sessionId, startTime, endTime, project, promptCount: prompts.length, status, durationSeconds }
}

// ─── listSessions ─────────────────────────────────────────────────────────────

export async function listSessions(): Promise<SessionSummary[]> {
  let files: string[]
  try {
    files = await readdir(SESSIONS_DIR)
  } catch {
    return []  // directory doesn't exist yet — no sessions recorded
  }

  const jsonlFiles = files.filter((f) => f.endsWith('.jsonl'))
  const summaries: SessionSummary[] = []

  for (const file of jsonlFiles) {
    const sessionId = file.replace(/\.jsonl$/, '')
    const events = await readJsonl(join(SESSIONS_DIR, file))
    if (events.length === 0) continue
    summaries.push(buildSummary(sessionId, events))
  }

  summaries.sort((a, b) => new Date(b.startTime).getTime() - new Date(a.startTime).getTime())
  return summaries
}

// ─── getSessionDetail ─────────────────────────────────────────────────────────

export async function getSessionDetail(id: string): Promise<SessionDetail | null> {
  const filePath = join(SESSIONS_DIR, `${id}.jsonl`)
  const events = await readJsonl(filePath)
  if (events.length === 0) return null

  const summary = buildSummary(id, events)
  const messages: SessionMessage[] = events.map((e, i) => ({
    id: i,
    type: e.type,
    content: e.prompt ?? e.cwd ?? '',
    timestamp: e.ts,
  }))

  return { ...summary, messages }
}
