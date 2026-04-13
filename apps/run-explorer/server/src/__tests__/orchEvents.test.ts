import { describe, it, expect, beforeEach, afterEach } from 'bun:test'
import { mkdtemp, writeFile, rm } from 'fs/promises'
import { join } from 'path'
import { tmpdir } from 'os'
import { readOrchEvents } from '../services/orchEventReader'

let tmpDir: string

beforeEach(async () => {
  tmpDir = await mkdtemp(join(tmpdir(), 'orch-events-test-'))
})

afterEach(async () => {
  await rm(tmpDir, { recursive: true, force: true })
})

describe('readOrchEvents', () => {
  it('returns [] for missing file', async () => {
    const result = await readOrchEvents('nonexistent-run', tmpDir)
    expect(result).toEqual([])
  })

  it('parses valid events correctly', async () => {
    const runDir = join(tmpDir, 'run-001')
    await mkdir(runDir)
    const lines = [
      JSON.stringify({ ts: '2024-01-01T10:00:00Z', agent: 'backend-lead', status: 'running', summary: 'started', wave: 0, orch_id: 'orch_123' }),
      JSON.stringify({ ts: '2024-01-01T10:01:00Z', agent: 'frontend-lead', status: 'done', summary: 'finished', reason: 'all tasks complete' }),
    ]
    await writeFile(join(runDir, 'events.jsonl'), lines.join('\n'))

    const result = await readOrchEvents('run-001', tmpDir)
    expect(result).toHaveLength(2)
    // newest first (reversed)
    expect(result[0]!.agent).toBe('frontend-lead')
    expect(result[0]!.status).toBe('done')
    expect(result[0]!.reason).toBe('all tasks complete')
    expect(result[1]!.agent).toBe('backend-lead')
    expect(result[1]!.wave).toBe(0)
    expect(result[1]!.orch_id).toBe('orch_123')
  })

  it('skips malformed lines', async () => {
    const runDir = join(tmpDir, 'run-002')
    await mkdir(runDir)
    const lines = [
      JSON.stringify({ ts: '2024-01-01T10:00:00Z', agent: 'backend-lead', status: 'running', summary: 'ok' }),
      'not-valid-json{{{{',
      JSON.stringify({ ts: '2024-01-01T10:01:00Z', agent: 'frontend-lead', status: 'done', summary: 'done' }),
    ]
    await writeFile(join(runDir, 'events.jsonl'), lines.join('\n'))

    const result = await readOrchEvents('run-002', tmpDir)
    expect(result).toHaveLength(2)
  })

  it('returns events newest-first (reversed)', async () => {
    const runDir = join(tmpDir, 'run-003')
    await mkdir(runDir)
    const lines = [
      JSON.stringify({ ts: '2024-01-01T10:00:00Z', agent: 'agent-a', status: 'running', summary: 'first' }),
      JSON.stringify({ ts: '2024-01-01T10:01:00Z', agent: 'agent-b', status: 'running', summary: 'second' }),
      JSON.stringify({ ts: '2024-01-01T10:02:00Z', agent: 'agent-c', status: 'done', summary: 'third' }),
    ]
    await writeFile(join(runDir, 'events.jsonl'), lines.join('\n'))

    const result = await readOrchEvents('run-003', tmpDir)
    expect(result[0]!.summary).toBe('third')
    expect(result[1]!.summary).toBe('second')
    expect(result[2]!.summary).toBe('first')
  })

  it('filters out lines without required ts/agent fields', async () => {
    const runDir = join(tmpDir, 'run-004')
    await mkdir(runDir)
    const lines = [
      JSON.stringify({ ts: '2024-01-01T10:00:00Z', agent: 'backend-lead', status: 'running', summary: 'valid' }),
      JSON.stringify({ agent: 'backend-lead', status: 'running', summary: 'missing ts' }),
      JSON.stringify({ ts: '2024-01-01T10:00:00Z', status: 'running', summary: 'missing agent' }),
      JSON.stringify({ status: 'running', summary: 'missing both' }),
    ]
    await writeFile(join(runDir, 'events.jsonl'), lines.join('\n'))

    const result = await readOrchEvents('run-004', tmpDir)
    expect(result).toHaveLength(1)
    expect(result[0]!.summary).toBe('valid')
  })
})

// Helper — Bun doesn't re-export mkdir from fs/promises in the same way
import { mkdir } from 'fs/promises'
