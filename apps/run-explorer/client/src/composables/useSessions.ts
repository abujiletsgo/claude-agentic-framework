import { ref, onMounted } from 'vue'
import type { SessionSummary } from '@shared/types'
import { API_BASE_URL } from '@/config'

export function useSessions() {
  const sessions = ref<SessionSummary[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function fetchSessions() {
    loading.value = true
    error.value = null
    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), 10000)
    try {
      const res = await fetch(`${API_BASE_URL}/api/sessions`, { signal: controller.signal })
      clearTimeout(timeoutId)
      if (!res.ok) {
        const body = await res.json().catch(() => ({ error: 'Unknown error', code: res.status }))
        throw new Error(body.error ?? `HTTP ${res.status}`)
      }
      sessions.value = await res.json() as SessionSummary[]
    } catch (e) {
      clearTimeout(timeoutId)
      error.value = e instanceof Error ? e.message : 'Failed to load sessions'
    } finally {
      loading.value = false
    }
  }

  onMounted(fetchSessions)
  return { sessions, loading, error, refresh: fetchSessions }
}
