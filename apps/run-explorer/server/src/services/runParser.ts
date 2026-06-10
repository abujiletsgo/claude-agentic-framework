import { readdir, stat, readFile } from 'fs/promises'
import { join } from 'path'
import { ORCH_BASE_DIR } from '../config'
import { estimateFileTokens } from './tokenEstimator'
import { parseEvalScore, parseEvalVerdict } from './evalParser'
import type { Run, RunDetail, RunStatus, LeadSummary, LeadOutput } from '../../../shared/types'

// ─── helpers ────────────────────────────────────────────────────────────────

async function listDir(dir: string): Promise<string[]> {
  try {
    return await readdir(dir)
  } catch {
    return []
  }
}

async function readText(filePath: string): Promise<string | null> {
  try {
    return await readFile(filePath, 'utf-8')
  } catch {
    return null
  }
}

async function fileMtime(filePath: string): Promise<Date | null> {
  try {
    const s = await stat(filePath)
    return s.mtime
  } catch {
    return null
  }
}

// ─── parseRunStatus ──────────────────────────────────────────────────────────

export async function parseRunStatus(orchDir: string): Promise<RunStatus> {
  // ── Consultant model (v5+): check events.jsonl for [done] broadcast ──────────
  const eventsText = await readText(join(orchDir, 'events.jsonl'))
  if (eventsText !== null) {
    const hasDone = eventsText.split('\n').some((line) => {
      try { return (JSON.parse(line) as Record<string, unknown>)['summary']?.toString().startsWith('[done]') } catch { return false }
    })
    // Check qa-report.md for verdict — match leading STATUS:/OVERALL: line or bare PASS/FAIL line
    const qaText = await readText(join(orchDir, 'qa-report.md'))
    if (qaText !== null) {
      const isFail = /^\s*(STATUS|OVERALL)[:\s]+FAIL\b|^\s*\**FAIL\**\s*$/im.test(qaText)
      const isPass = /^\s*(STATUS|OVERALL)[:\s]+PASS\b|^\s*\**PASS\**\s*$/im.test(qaText)
      if (isFail) return 'FAIL'
      if (isPass) return hasDone ? 'PASS' : 'IN_PROGRESS'
    }
    if (hasDone) return 'PASS'
    // Has events but no [done] → still running
    return 'IN_PROGRESS'
  }

  // ── Legacy lead model: .status files ─────────────────────────────────────────
  const entries = await listDir(orchDir)
  const statusFiles = entries.filter((e) => e.endsWith('.status'))

  for (const sf of statusFiles) {
    const raw = await readText(join(orchDir, sf))
    if (!raw) continue
    try {
      const parsed = JSON.parse(raw) as Record<string, unknown>
      if (typeof parsed['status'] === 'string' && parsed['status'] === 'failed') return 'FAIL'
    } catch { /* ignore */ }
  }

  const evalText = await readText(join(orchDir, 'evaluation_report.md'))
  if (evalText !== null) {
    const verdict = parseEvalVerdict(evalText)
    if (verdict === 'NEEDS REWORK') return 'FAIL'
    if (verdict === 'SHIP') return 'PASS'
  }

  if (statusFiles.length > 0) {
    let allDone = true
    for (const sf of statusFiles) {
      const raw = await readText(join(orchDir, sf))
      if (!raw) { allDone = false; break }
      try {
        const parsed = JSON.parse(raw) as Record<string, unknown>
        if (parsed['status'] !== 'done') { allDone = false; break }
      } catch { allDone = false; break }
    }
    if (allDone) return 'PASS'
  }

  return 'UNKNOWN'
}

// ─── parseLeadCount ──────────────────────────────────────────────────────────

export async function parseLeadCount(orchDir: string): Promise<number> {
  // ── Consultant model (v5+): count agent result files in results/ ──────────────
  const resultsEntries = await listDir(join(orchDir, 'results'))
  if (resultsEntries.length > 0) {
    const agentNames = new Set<string>()
    for (const e of resultsEntries) {
      if (e.endsWith('.md')) agentNames.add(e.replace(/\.md$/, ''))
    }
    return agentNames.size
  }

  // ── Legacy lead model: prompts/ directory ─────────────────────────────────────
  const entries = await listDir(join(orchDir, 'prompts'))
  const prefixes = new Set<string>()
  for (const e of entries) {
    const mWave = e.match(/^(.+)-wave\d+\.md$/)
    if (mWave && mWave[1] !== undefined) { prefixes.add(mWave[1]); continue }
    const mPlain = e.match(/^(.+)\.md$/)
    if (mPlain && mPlain[1] !== undefined) prefixes.add(mPlain[1])
  }
  return prefixes.size
}

// ─── parseWaveCount ──────────────────────────────────────────────────────────

export async function parseWaveCount(orchDir: string): Promise<number> {
  // ── Consultant model (v5+): count distinct wave-N broadcasts in events.jsonl ───
  const eventsText = await readText(join(orchDir, 'events.jsonl'))
  if (eventsText !== null) {
    const waveNums = new Set<number>()
    for (const line of eventsText.split('\n')) {
      try {
        const ev = JSON.parse(line) as Record<string, unknown>
        const summary = ev['summary']?.toString() ?? ''
        // Matches [wave-0b], [wave-1], [wave-2] etc.
        const m = summary.match(/^\[wave-(\d+)/)
        if (m && m[1] !== undefined) waveNums.add(parseInt(m[1], 10))
      } catch { /* skip */ }
    }
    return waveNums.size
  }

  // ── Legacy lead model: prompts/ directory ─────────────────────────────────────
  const entries = await listDir(join(orchDir, 'prompts'))
  let max = -1
  let hasPlainLeads = false
  for (const e of entries) {
    const mWave = e.match(/-wave(\d+)\.md$/)
    if (mWave && mWave[1] !== undefined) {
      const n = parseInt(mWave[1], 10)
      if (n > max) max = n
    } else if (e.endsWith('.md')) {
      hasPlainLeads = true
    }
  }
  if (max >= 0) return max
  if (hasPlainLeads) return 0
  return 0
}

// ─── parseTokenEstimate ──────────────────────────────────────────────────────

export async function parseTokenEstimate(orchDir: string): Promise<number> {
  const resultsDir = join(orchDir, 'results')
  const entries = await listDir(resultsDir)
  const mdFiles = entries.filter((e) => e.endsWith('.md'))
  const counts = await Promise.all(mdFiles.map((e) => estimateFileTokens(join(resultsDir, e))))
  return counts.reduce((sum, n) => sum + n, 0)
}

// ─── parseStartTime ──────────────────────────────────────────────────────────

export async function parseStartTime(orchDir: string): Promise<string> {
  const raw = await readText(join(orchDir, 'orch-start.json'))
  if (raw) {
    try {
      const parsed = JSON.parse(raw) as Record<string, unknown>
      if (typeof parsed['start'] === 'string') return parsed['start']
    } catch {
      // fall through
    }
  }
  // fallback: dir mtime
  const mtime = await fileMtime(orchDir)
  return mtime ? mtime.toISOString() : new Date(0).toISOString()
}

// ─── parseWallClockSeconds ───────────────────────────────────────────────────

export async function parseWallClockSeconds(orchDir: string): Promise<number> {
  const startStr = await parseStartTime(orchDir)
  const startMs = new Date(startStr).getTime()

  const entries = await listDir(orchDir)
  const statusFiles = entries.filter((e) => e.endsWith('.status'))

  let latestMs = startMs
  for (const sf of statusFiles) {
    const mtime = await fileMtime(join(orchDir, sf))
    if (mtime && mtime.getTime() > latestMs) {
      latestMs = mtime.getTime()
    }
  }

  return Math.round((latestMs - startMs) / 1000)
}

// ─── parseLeadSummaries ──────────────────────────────────────────────────────

export async function parseLeadSummaries(orchDir: string): Promise<LeadSummary[]> {
  const entries = await listDir(orchDir)
  const statusFiles = entries.filter((e) => e.endsWith('.status'))
  const summaries: LeadSummary[] = []

  for (const sf of statusFiles) {
    const role = sf.replace(/\.status$/, '')
    const raw = await readText(join(orchDir, sf))
    let status: RunStatus = 'UNKNOWN'
    if (raw) {
      try {
        const parsed = JSON.parse(raw) as Record<string, unknown>
        if (parsed['status'] === 'done') status = 'PASS'
        else if (parsed['status'] === 'failed') status = 'FAIL'
      } catch {
        // keep UNKNOWN
      }
    }

    // find max wave from results/<role>-waveN.md
    const resultsEntries = await listDir(join(orchDir, 'results'))
    let maxWave = 0
    for (const re of resultsEntries) {
      const m = re.match(new RegExp(`^${role}-wave(\\d+)\\.md$`))
      if (m) {
        const n = parseInt(m[1] ?? '0', 10)
        if (n > maxWave) maxWave = n
      }
    }

    summaries.push({ name: role, status, wave: maxWave })
  }

  return summaries
}

// ─── parseProject ────────────────────────────────────────────────────────────

export async function parseProject(orchDir: string): Promise<string | undefined> {
  const raw = await readText(join(orchDir, 'meta.json'))
  if (!raw) return undefined
  try {
    const parsed = JSON.parse(raw) as Record<string, unknown>
    const cwd = typeof parsed['cwd'] === 'string' ? parsed['cwd'] : null
    if (!cwd) return undefined
    // Use the last two path segments (e.g. /Users/tom/Documents/caf-team → caf-team)
    const parts = cwd.replace(/\/$/, '').split('/')
    return parts[parts.length - 1] || undefined
  } catch {
    return undefined
  }
}

// ─── parseMissionBrief ───────────────────────────────────────────────────────

export async function parseMissionBrief(orchDir: string): Promise<string> {
  const text = await readText(join(orchDir, 'mission_brief.md'))
  if (text !== null) return text
  // Consultant model (v5+) writes spec.md instead of mission_brief.md
  const specText = await readText(join(orchDir, 'spec.md'))
  if (specText !== null) return specText
  return ''
}

// ─── parseEvaluation ─────────────────────────────────────────────────────────

export async function parseEvaluation(
  orchDir: string
): Promise<{ score: number | null; verdict: 'SHIP' | 'NEEDS REWORK' | null }> {
  const text = await readText(join(orchDir, 'evaluation_report.md'))
  if (!text) return { score: null, verdict: null }
  return {
    score: parseEvalScore(text),
    verdict: parseEvalVerdict(text),
  }
}

// ─── parseAcceptanceCriteria ─────────────────────────────────────────────────

export async function parseAcceptanceCriteria(orchDir: string): Promise<string> {
  const text = await readText(join(orchDir, 'acceptance_criteria.md'))
  return text ?? ''
}

// ─── parseEvaluationFull ─────────────────────────────────────────────────────

export async function parseEvaluationFull(orchDir: string): Promise<string> {
  const text = await readText(join(orchDir, 'evaluation_report.md'))
  return text ?? ''
}

// ─── listRuns ────────────────────────────────────────────────────────────────

export async function listRuns(): Promise<Run[]> {
  const entries = await listDir(ORCH_BASE_DIR)
  const orchDirs = entries.filter((e) => e.startsWith('orch_'))

  const runs: Run[] = []
  for (const dir of orchDirs) {
    const orchDir = join(ORCH_BASE_DIR, dir)
    // must have at least one content sentinel to be shown:
    // - acceptance_criteria.md / mission_brief.md (old lead model)
    // - spec.md or research.md (consultant model v5+)
    // - qa-report.md (any completed run)
    const [criteriaText, briefText, specText, researchText, qaText] = await Promise.all([
      readText(join(orchDir, 'acceptance_criteria.md')),
      readText(join(orchDir, 'mission_brief.md')),
      readText(join(orchDir, 'spec.md')),
      readText(join(orchDir, 'research.md')),
      readText(join(orchDir, 'qa-report.md')),
    ])
    if (criteriaText === null && briefText === null && specText === null && researchText === null && qaText === null) continue

    const [startTime, leadCount, status, waveCount, tokenEstimate, project] = await Promise.all([
      parseStartTime(orchDir),
      parseLeadCount(orchDir),
      parseRunStatus(orchDir),
      parseWaveCount(orchDir),
      parseTokenEstimate(orchDir),
      parseProject(orchDir),
    ])

    runs.push({ id: dir, startTime, leadCount, status, waveCount, tokenEstimate, project })
  }

  runs.sort((a, b) => new Date(b.startTime).getTime() - new Date(a.startTime).getTime())
  return runs
}

// ─── getRunDetail ────────────────────────────────────────────────────────────

export async function getRunDetail(id: string): Promise<RunDetail | null> {
  const orchDir = join(ORCH_BASE_DIR, id)
  // check dir exists
  try {
    await stat(orchDir)
  } catch {
    return null
  }

  const [startTime, leadCount, status, waveCount, tokenEstimate, project, missionBrief, acceptanceCriteria, evaluationFull, leads, evaluation] =
    await Promise.all([
      parseStartTime(orchDir),
      parseLeadCount(orchDir),
      parseRunStatus(orchDir),
      parseWaveCount(orchDir),
      parseTokenEstimate(orchDir),
      parseProject(orchDir),
      parseMissionBrief(orchDir),
      parseAcceptanceCriteria(orchDir),
      parseEvaluationFull(orchDir),
      parseLeadSummaries(orchDir),
      parseEvaluation(orchDir),
    ])

  return {
    id,
    startTime,
    leadCount,
    status,
    waveCount,
    tokenEstimate,
    project,
    missionBrief,
    acceptanceCriteria,
    evaluationFull,
    leads,
    evaluationScore: evaluation.score,
    evaluationVerdict: evaluation.verdict,
  }
}

// ─── getLeadOutput ───────────────────────────────────────────────────────────

export async function getLeadOutput(id: string, leadName: string): Promise<LeadOutput | null> {
  const orchDir = join(ORCH_BASE_DIR, id)
  const resultsDir = join(orchDir, 'results')
  const promptsDir = join(orchDir, 'prompts')
  const resultsEntries = await listDir(resultsDir)
  const promptsEntries = await listDir(promptsDir)

  // ── Collect result wave files: <leadName>-waveN.md ──────────────────────────
  const waveFiles: Array<{ wave: number; path: string }> = []
  for (const e of resultsEntries) {
    const m = e.match(new RegExp(`^${leadName}-wave(\\d+)\\.md$`))
    if (m) {
      waveFiles.push({ wave: parseInt(m[1] ?? '0', 10), path: join(resultsDir, e) })
    }
  }
  // Also check for plain result file: <leadName>.md (wave 0)
  if (waveFiles.length === 0 && resultsEntries.includes(`${leadName}.md`)) {
    waveFiles.push({ wave: 0, path: join(resultsDir, `${leadName}.md`) })
  }

  if (waveFiles.length === 0) return null

  waveFiles.sort((a, b) => a.wave - b.wave)

  // ── Collect prompt wave files: <leadName>-waveN.md or <leadName>.md ──────────
  const promptWaveFiles: Array<{ wave: number; path: string }> = []
  for (const e of promptsEntries) {
    const m = e.match(new RegExp(`^${leadName}-wave(\\d+)\\.md$`))
    if (m) {
      promptWaveFiles.push({ wave: parseInt(m[1] ?? '0', 10), path: join(promptsDir, e) })
    }
  }
  if (promptWaveFiles.length === 0 && promptsEntries.includes(`${leadName}.md`)) {
    promptWaveFiles.push({ wave: 0, path: join(promptsDir, `${leadName}.md`) })
  }
  promptWaveFiles.sort((a, b) => a.wave - b.wave)

  // ── Build content: prompt section then results section ──────────────────────
  const parts: string[] = []
  let maxWave = 0

  if (promptWaveFiles.length > 0) {
    const promptParts: string[] = []
    for (const { wave, path } of promptWaveFiles) {
      const text = await readText(path)
      if (text !== null) {
        if (promptWaveFiles.length > 1) {
          promptParts.push(`### Wave ${wave}\n\n${text}`)
        } else {
          promptParts.push(text)
        }
      }
    }
    if (promptParts.length > 0) {
      parts.push(`## Prompt\n\n${promptParts.join('\n\n')}`)
    }
  }

  const resultParts: string[] = []
  for (const { wave, path } of waveFiles) {
    const text = await readText(path)
    if (text !== null) {
      if (waveFiles.length > 1) {
        resultParts.push(`### Wave ${wave}\n\n${text}`)
      } else {
        resultParts.push(text)
      }
      if (wave > maxWave) maxWave = wave
    }
  }
  if (resultParts.length > 0) {
    parts.push(`## Results\n\n${resultParts.join('\n\n')}`)
  }

  return {
    leadName,
    wave: maxWave,
    content: parts.join('\n\n---\n\n'),
  }
}
