import { describe, it, expect, beforeEach, afterEach } from 'bun:test'
import { mkdtemp, mkdir, writeFile, rm } from 'fs/promises'
import { join } from 'path'
import { tmpdir } from 'os'
import {
  parseLeadCount,
  parseWaveCount,
  parseRunStatus,
  parseTokenEstimate,
} from '../services/runParser'

describe('runParser — mock orch dir', () => {
  let orchDir: string

  beforeEach(async () => {
    orchDir = await mkdtemp(join(tmpdir(), 'test_orch_'))
    await mkdir(join(orchDir, 'prompts'), { recursive: true })
    await mkdir(join(orchDir, 'results'), { recursive: true })

    // 4 prompt files: 2 leads × 2 waves each
    await writeFile(join(orchDir, 'prompts', 'backend-lead-wave0.md'), '# backend-lead wave 0')
    await writeFile(join(orchDir, 'prompts', 'backend-lead-wave2.md'), '# backend-lead wave 2')
    await writeFile(join(orchDir, 'prompts', 'frontend-lead-wave0.md'), '# frontend-lead wave 0')
    await writeFile(join(orchDir, 'prompts', 'frontend-lead-wave2.md'), '# frontend-lead wave 2')

    // 1 result file — exactly 100 words → Math.ceil(100 * 1.3) = 130 tokens
    const hundredWords = Array.from({ length: 100 }, (_, i) => `word${i}`).join(' ')
    await writeFile(join(orchDir, 'results', 'backend-lead-wave2.md'), hundredWords)

    // evaluation report with SHIP verdict
    await writeFile(join(orchDir, 'evaluation_report.md'), 'The verdict is SHIP\nScore: 85')

    // acceptance criteria (required for listRuns to pick up the dir; not needed by unit fns)
    await writeFile(join(orchDir, 'acceptance_criteria.md'), '# Criteria')
  })

  afterEach(async () => {
    await rm(orchDir, { recursive: true, force: true })
  })

  describe('parseLeadCount', () => {
    it('returns 2 for backend-lead and frontend-lead', async () => {
      expect(await parseLeadCount(orchDir)).toBe(2)
    })

    it('returns 0 for an empty prompts dir', async () => {
      const emptyDir = await mkdtemp(join(tmpdir(), 'test_empty_'))
      await mkdir(join(emptyDir, 'prompts'), { recursive: true })
      try {
        expect(await parseLeadCount(emptyDir)).toBe(0)
      } finally {
        await rm(emptyDir, { recursive: true, force: true })
      }
    })
  })

  describe('parseWaveCount', () => {
    it('returns 2 (max wave number across all prompts)', async () => {
      expect(await parseWaveCount(orchDir)).toBe(2)
    })

    it('returns 0 when prompts dir is empty', async () => {
      const emptyDir = await mkdtemp(join(tmpdir(), 'test_empty_'))
      await mkdir(join(emptyDir, 'prompts'), { recursive: true })
      try {
        expect(await parseWaveCount(emptyDir)).toBe(0)
      } finally {
        await rm(emptyDir, { recursive: true, force: true })
      }
    })
  })

  describe('parseRunStatus', () => {
    it('returns PASS when evaluation_report.md contains SHIP', async () => {
      expect(await parseRunStatus(orchDir)).toBe('PASS')
    })

    it('returns FAIL when evaluation_report.md contains NEEDS REWORK', async () => {
      await writeFile(join(orchDir, 'evaluation_report.md'), 'This NEEDS REWORK before shipping')
      expect(await parseRunStatus(orchDir)).toBe('FAIL')
    })

    it('returns FAIL when a .status file has status=failed', async () => {
      // Remove eval report to isolate status-file check
      await rm(join(orchDir, 'evaluation_report.md'))
      await writeFile(
        join(orchDir, 'backend-lead.status'),
        JSON.stringify({ status: 'failed', error: 'out of tokens' }),
      )
      expect(await parseRunStatus(orchDir)).toBe('FAIL')
    })
  })

  describe('parseTokenEstimate', () => {
    it('returns > 0 for a 100-word result file', async () => {
      const tokens = await parseTokenEstimate(orchDir)
      expect(tokens).toBeGreaterThan(0)
    })

    it('returns 130 for exactly 100 words (Math.ceil(100 * 1.3))', async () => {
      expect(await parseTokenEstimate(orchDir)).toBe(130)
    })

    it('returns 0 when results dir is empty', async () => {
      const emptyDir = await mkdtemp(join(tmpdir(), 'test_empty_'))
      await mkdir(join(emptyDir, 'results'), { recursive: true })
      try {
        expect(await parseTokenEstimate(emptyDir)).toBe(0)
      } finally {
        await rm(emptyDir, { recursive: true, force: true })
      }
    })
  })
})
