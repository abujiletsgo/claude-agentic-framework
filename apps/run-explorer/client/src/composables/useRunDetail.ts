import { ref, watch } from 'vue'
import type { Ref } from 'vue'
import type { RunDetail } from '@shared/types'
import { API_BASE_URL } from '@/config'

export function useRunDetail(id: Ref<string>) {
  const run = ref<RunDetail | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)
  const notFound = ref(false)

  async function refresh() {
    if (!id.value) return
    loading.value = true
    error.value = null
    notFound.value = false
    run.value = null
    try {
      const res = await fetch(`${API_BASE_URL}/api/runs/${id.value}`)
      if (res.status === 404) {
        notFound.value = true
        return
      }
      if (!res.ok) {
        const body = await res.json().catch(() => ({ error: 'Unknown error', code: res.status }))
        throw new Error(body.error ?? `HTTP ${res.status}`)
      }
      run.value = await res.json() as RunDetail
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to load run'
    } finally {
      loading.value = false
    }
  }

  watch(id, refresh, { immediate: true })

  return { run, loading, error, notFound, refresh }
}
