import { ref } from 'vue'
import type { Run } from '@shared/types'
import { API_BASE_URL } from '@/config'

export function useRuns() {
  const runs = ref<Run[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function refresh() {
    loading.value = true
    error.value = null
    try {
      const res = await fetch(`${API_BASE_URL}/api/runs`)
      if (!res.ok) {
        const body = await res.json().catch(() => ({ error: 'Unknown error', code: res.status }))
        throw new Error(body.error ?? `HTTP ${res.status}`)
      }
      runs.value = await res.json() as Run[]
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to load runs'
    } finally {
      loading.value = false
    }
  }

  refresh()

  return { runs, loading, error, refresh }
}
