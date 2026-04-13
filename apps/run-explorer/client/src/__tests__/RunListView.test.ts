import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createRouter, createWebHashHistory } from 'vue-router'
import type { Run } from '@shared/types'

const mockRuns: Run[] = [
  {
    id: 'orch_abc123',
    startTime: '2024-01-15T10:30:00Z',
    leadCount: 2,
    status: 'PASS',
    waveCount: 3,
    tokenEstimate: 500,
  },
  {
    id: 'orch_def456',
    startTime: '2024-01-14T08:00:00Z',
    leadCount: 1,
    status: 'FAIL',
    waveCount: 1,
    tokenEstimate: 200,
  },
]

vi.mock('@/composables/useRuns', async () => {
  const { ref } = await import('vue')
  return {
    useRuns: () => ({
      runs: ref(mockRuns),
      loading: ref(false),
      error: ref(null),
      refresh: vi.fn(),
    }),
  }
})

const router = createRouter({
  history: createWebHashHistory(),
  routes: [{ path: '/', component: { template: '<div />' } }],
})

async function mountView() {
  const RunListView = (await import('../views/RunListView.vue')).default
  const wrapper = mount(RunListView, {
    global: { plugins: [router] },
  })
  await router.isReady()
  return wrapper
}

describe('RunListView', () => {
  it('renders a <table> element', async () => {
    const wrapper = await mountView()
    expect(wrapper.find('table').exists()).toBe(true)
  })

  it('renders one row per run in the table body', async () => {
    const wrapper = await mountView()
    const rows = wrapper.findAll('tbody tr')
    expect(rows.length).toBe(mockRuns.length)
  })

  it('displays truncated run IDs in the first column', async () => {
    const wrapper = await mountView()
    const firstRowText = wrapper.find('tbody tr td').text()
    // RunListView slices the id to the first 8 chars
    expect(firstRowText).toBe(mockRuns[0]!.id.slice(0, 8))
  })

  it('shows a StatusBadge for each run', async () => {
    const wrapper = await mountView()
    // StatusBadge renders a <span> with a coloured dot; at minimum the component renders inside each row
    const badges = wrapper.findAllComponents({ name: 'StatusBadge' })
    expect(badges.length).toBe(mockRuns.length)
  })

  it('renders the wave count for each run', async () => {
    const wrapper = await mountView()
    const html = wrapper.html()
    for (const run of mockRuns) {
      expect(html).toContain(String(run.waveCount))
    }
  })

  it('shows the Refresh button', async () => {
    const wrapper = await mountView()
    const btn = wrapper.find('button[aria-label="Refresh runs"]')
    expect(btn.exists()).toBe(true)
  })
})
