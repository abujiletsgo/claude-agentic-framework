import { ref, onMounted } from 'vue'
import { API_BASE_URL } from '@/config'

export interface CostSummary {
  totalCost: number
  totalTokens: number
  sessionCount: number
  period: string
}

export interface DailyCost {
  date: string
  cost: number
  tokens: number
}

export function useCosts() {
  const summary = ref<CostSummary | null>(null)
  const daily = ref<DailyCost[]>([])
  const loading = ref(false)

  async function refresh() {
    loading.value = true
    try {
      const [summaryRes, dailyRes] = await Promise.all([
        fetch(`${API_BASE_URL}/api/costs/summary?period=week`),
        fetch(`${API_BASE_URL}/api/costs/daily?days=7`),
      ])
      if (summaryRes.ok) {
        const wire = await summaryRes.json()
        summary.value = {
          totalCost: wire.total_cost,
          totalTokens: (wire.total_input_tokens ?? 0) + (wire.total_output_tokens ?? 0),
          sessionCount: wire.session_count,
          period: wire.period,
        }
      }
      if (dailyRes.ok) daily.value = await dailyRes.json()
    } catch {
      // ignore
    } finally {
      loading.value = false
    }
  }

  onMounted(() => {
    refresh()
  })

  return { summary, daily, loading, refresh }
}
