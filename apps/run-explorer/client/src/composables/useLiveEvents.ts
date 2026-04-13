import { ref, computed, onMounted, onUnmounted } from 'vue'
import { API_BASE_URL } from '@/config'

export interface LiveEvent {
  id: number
  source_app: string
  session_id: string
  hook_event_type: string
  payload: string
  summary: string | null
  timestamp: number
}

export interface FilterOptions {
  source_apps: string[]
  session_ids: string[]
  hook_event_types: string[]
}

const WS_URL = API_BASE_URL.replace(/^http/, 'ws') + '/stream'

export function useLiveEvents() {
  const events = ref<LiveEvent[]>([])
  const connected = ref(false)
  const filterOptions = ref<FilterOptions>({ source_apps: [], session_ids: [], hook_event_types: [] })
  const activeFilters = ref({ source_app: '', session_id: '', hook_event_type: '' })

  const filteredEvents = computed(() => {
    return events.value.filter(e => {
      if (activeFilters.value.source_app && e.source_app !== activeFilters.value.source_app) return false
      if (activeFilters.value.session_id && e.session_id !== activeFilters.value.session_id) return false
      if (activeFilters.value.hook_event_type && e.hook_event_type !== activeFilters.value.hook_event_type) return false
      return true
    })
  })

  let ws: WebSocket | null = null
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null
  let unmounted = false

  function connect() {
    if (unmounted) return
    ws = new WebSocket(WS_URL)

    ws.onopen = () => {
      connected.value = true
    }

    ws.onmessage = (msg) => {
      try {
        const parsed = JSON.parse(msg.data)
        if (parsed.type === 'initial' && Array.isArray(parsed.data)) {
          // newest first, cap at 500
          events.value = parsed.data.slice(0, 500).reverse()
        } else if (parsed.type === 'event' && parsed.data) {
          events.value.unshift(parsed.data)
          if (events.value.length > 500) {
            events.value.splice(500)
          }
        }
      } catch {
        // ignore parse errors
      }
    }

    ws.onclose = () => {
      connected.value = false
      ws = null
      if (!unmounted) {
        reconnectTimer = setTimeout(connect, 3000)
      }
    }

    ws.onerror = () => {
      ws?.close()
    }
  }

  async function fetchFilterOptions() {
    try {
      const res = await fetch(`${API_BASE_URL}/api/live/filter-options`)
      if (res.ok) {
        filterOptions.value = await res.json()
      }
    } catch {
      // ignore
    }
  }

  onMounted(() => {
    connect()
    fetchFilterOptions()
  })

  onUnmounted(() => {
    unmounted = true
    if (reconnectTimer !== null) clearTimeout(reconnectTimer)
    ws?.close()
  })

  return { events, connected, filterOptions, activeFilters, filteredEvents }
}
