import { ref, watch, type Ref } from 'vue'
import type { OrchEvent } from '@shared/types'
import { API_BASE_URL } from '@/config'

export function useOrchEvents(runId: Ref<string>) {
  const events = ref<OrchEvent[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function refresh() {
    if (!runId.value) return
    loading.value = true
    error.value = null
    try {
      const res = await fetch(`${API_BASE_URL}/api/runs/${runId.value}/events`)
      if (!res.ok) {
        const body = await res.json().catch(() => ({ error: 'Unknown error' }))
        throw new Error(body.error ?? `HTTP ${res.status}`)
      }
      events.value = await res.json() as OrchEvent[]
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to load events'
    } finally {
      loading.value = false
    }
  }

  watch(runId, refresh, { immediate: true })
  return { events, loading, error, refresh }
}
