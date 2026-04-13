import { ref } from 'vue'
import type { Event } from '@shared/types'
import { API_BASE_URL } from '@/config'

export function useHealth() {
  const events = ref<Event[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function refresh() {
    loading.value = true
    error.value = null
    try {
      const res = await fetch(`${API_BASE_URL}/api/events/recent`)
      if (!res.ok) {
        const body = await res.json().catch(() => ({ error: 'Unknown error', code: res.status }))
        throw new Error(body.error ?? `HTTP ${res.status}`)
      }
      events.value = await res.json() as Event[]
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to load events'
    } finally {
      loading.value = false
    }
  }

  refresh()

  return { events, loading, error, refresh }
}
