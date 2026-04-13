import { ref, watch } from 'vue'
import type { Ref } from 'vue'
import type { ComparisonResult } from '@shared/types'
import { API_BASE_URL } from '@/config'

export function useComparison(idA: Ref<string>, idB: Ref<string>) {
  const result = ref<ComparisonResult | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function fetch_() {
    if (!idA.value || !idB.value) {
      result.value = null
      return
    }
    loading.value = true
    error.value = null
    result.value = null
    try {
      const res = await fetch(`${API_BASE_URL}/api/compare?a=${encodeURIComponent(idA.value)}&b=${encodeURIComponent(idB.value)}`)
      if (!res.ok) {
        const body = await res.json().catch(() => ({ error: 'Unknown error', code: res.status }))
        throw new Error(body.error ?? `HTTP ${res.status}`)
      }
      result.value = await res.json() as ComparisonResult
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Comparison failed'
    } finally {
      loading.value = false
    }
  }

  watch([idA, idB], fetch_, { immediate: true })

  return { result, loading, error }
}
