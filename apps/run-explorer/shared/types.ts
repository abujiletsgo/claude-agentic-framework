// Shared types — imported by both server and client. Do not duplicate.

export type RunStatus = 'PASS' | 'FAIL' | 'IN_PROGRESS' | 'UNKNOWN'

export interface Run {
  id: string
  startTime: string        // ISO 8601 — from orch-start.json `start` field; fallback: run dir mtime
  leadCount: number        // count of unique lead-name prefixes in prompts/ (e.g. "backend-lead" from "backend-lead-wave0.md")
  status: RunStatus
  waveCount: number        // max wave number extracted from prompts/*-waveN.md filenames
  tokenEstimate: number    // sum of Math.ceil(wordCount * 1.3) across results/**/*.md files
  project?: string         // repo/project name derived from meta.json `cwd` field; absent for old runs
}

export interface LeadSummary {
  name: string             // e.g. "api-lead", "backend-lead"
  status: RunStatus
  wave: number             // highest wave number seen for this lead (from result filename e.g. backend-lead-wave2.md → 2)
}

export interface RunDetail extends Run {
  missionBrief: string                               // raw markdown from mission_brief.md
  acceptanceCriteria: string                         // raw markdown from acceptance_criteria.md; empty string if file absent
  evaluationFull: string                             // full text of evaluation_report.md; empty string if absent
  leads: LeadSummary[]
  evaluationScore: number | null                     // numeric score parsed from evaluation_report.md; null if absent
  evaluationVerdict: 'SHIP' | 'NEEDS REWORK' | null // verdict string from evaluation_report.md; null if absent
}

export interface LeadOutput {
  leadName: string
  wave: number             // highest wave for this lead
  content: string          // markdown content; multiple waves concatenated with "## Wave N" headers
}

export interface MetricComparison {
  a: number
  b: number
  winner: 'a' | 'b' | 'tie'
}

export interface QualityComparison {
  a: number | null
  b: number | null
  winner: 'a' | 'b' | 'tie' | null  // null when both scores are null
}

export interface ComparisonResult {
  runA: Run
  runB: Run
  metrics: {
    wallClockSeconds: MetricComparison
    tokenEstimate: MetricComparison
    qualityScore: QualityComparison
  }
}

export interface Event {
  id: number
  type: string             // hook_event_type column from events.db
  timestamp: string        // ISO 8601 converted from unix INTEGER (new Date(ts * 1000).toISOString())
  metadata: string         // first 200 chars of payload column
}

export interface ApiError {
  error: string
  code: number
}

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

export interface OrchEvent {
  ts: string            // ISO 8601 timestamp from events.jsonl
  agent: string         // lead/agent name (e.g. "backend-lead")
  status: 'domain-claim' | 'broadcast' | 'running' | 'done' | 'question' | 'memory'
  summary: string       // event description
  wave?: number         // optional wave number
  orch_id?: string      // optional orch job id
  reason?: string       // optional reason (seen on done events)
}
