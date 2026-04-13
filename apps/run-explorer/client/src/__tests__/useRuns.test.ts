import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { useRuns } from '../composables/useRuns'
import type { Run } from '@shared/types'

const mockRuns: Run[] = [
  {
    id: 'orch_abc123',
    startTime: '2024-01-01T00:00:00Z',
    leadCount: 2,
    status: 'PASS',
    waveCount: 2,
    tokenEstimate: 500,
  },
  {
    id: 'orch_def456',
    startTime: '2024-01-02T00:00:00Z',
    leadCount: 3,
    status: 'FAIL',
    waveCount: 1,
    tokenEstimate: 300,
  },
]

beforeEach(() => {
  vi.stubGlobal('fetch', vi.fn())
})

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('useRuns', () => {
  it('is loading=true immediately after call', () => {
    ;(fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: true,
      json: async () => mockRuns,
    })
    const { loading } = useRuns()
    expect(loading.value).toBe(true)
  })

  it('sets runs and clears loading after successful fetch', async () => {
    ;(fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: true,
      json: async () => mockRuns,
    })

    const { runs, loading, error } = useRuns()

    // flush microtasks
    await new Promise((r) => setTimeout(r, 0))

    expect(runs.value).toEqual(mockRuns)
    expect(error.value).toBeNull()
    expect(loading.value).toBe(false)
  })

  it('sets error when fetch throws a network error', async () => {
    ;(fetch as ReturnType<typeof vi.fn>).mockRejectedValueOnce(new Error('Network error'))

    const { error, loading } = useRuns()
    await new Promise((r) => setTimeout(r, 0))

    expect(error.value).toBe('Network error')
    expect(loading.value).toBe(false)
  })

  it('sets error when response is not ok and server returns error body', async () => {
    ;(fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: false,
      status: 500,
      json: async () => ({ error: 'Internal Server Error', code: 500 }),
    })

    const { error } = useRuns()
    await new Promise((r) => setTimeout(r, 0))

    expect(error.value).toBe('Internal Server Error')
  })

  it('refresh() re-fetches and updates runs', async () => {
    const secondBatch: Run[] = [{ ...mockRuns[0]!, id: 'orch_updated' }]

    ;(fetch as ReturnType<typeof vi.fn>)
      .mockResolvedValueOnce({ ok: true, json: async () => mockRuns })
      .mockResolvedValueOnce({ ok: true, json: async () => secondBatch })

    const { runs, refresh } = useRuns()
    await new Promise((r) => setTimeout(r, 0))
    expect(runs.value).toEqual(mockRuns)

    refresh()
    await new Promise((r) => setTimeout(r, 0))
    expect(runs.value).toEqual(secondBatch)
  })
})
