<script setup lang="ts">
import { ref, watch, nextTick } from 'vue'
import { useLiveEvents } from '@/composables/useLiveEvents'
import { useCosts } from '@/composables/useCosts'
import LiveEventRow from '@/components/LiveEventRow.vue'
import CostSummaryCard from '@/components/CostSummaryCard.vue'

const { events, connected, filterOptions, activeFilters, filteredEvents } = useLiveEvents()
const { summary, loading: costsLoading } = useCosts()

const scrollContainer = ref<HTMLElement | null>(null)
const pauseScroll = ref(false)

// Auto-scroll to top when new events arrive (unless paused)
watch(
  () => events.value.length,
  async () => {
    if (pauseScroll.value) return
    await nextTick()
    scrollContainer.value?.scrollTo({ top: 0, behavior: 'smooth' })
  }
)
</script>

<template>
  <div class="space-y-6">
    <!-- Page header -->
    <div class="flex items-center justify-between">
      <div class="flex items-center gap-3">
        <h1 class="text-2xl font-bold text-slate-900 dark:text-white">Live Activity</h1>
        <!-- Connection indicator -->
        <span
          :class="[
            'inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold border',
            connected
              ? 'bg-emerald-50 border-emerald-200 text-emerald-700 dark:bg-emerald-900/20 dark:border-emerald-700 dark:text-emerald-300'
              : 'bg-red-50 border-red-200 text-red-700 dark:bg-red-900/20 dark:border-red-700 dark:text-red-300'
          ]"
        >
          <span
            :class="[
              'w-1.5 h-1.5 rounded-full flex-shrink-0',
              connected ? 'bg-emerald-500 animate-pulse' : 'bg-red-500'
            ]"
          ></span>
          {{ connected ? 'Connected' : 'Disconnected' }}
        </span>
      </div>

      <div class="flex items-center gap-2 text-sm text-slate-500 dark:text-slate-400">
        <span>{{ filteredEvents.length }} events</span>
      </div>
    </div>

    <!-- Top section: filters + cost card -->
    <div class="flex flex-col lg:flex-row gap-4">
      <!-- Filter bar -->
      <div class="flex-1 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-4 shadow-sm">
        <h3 class="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-3">Filters</h3>
        <div class="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <!-- source_app -->
          <div>
            <label class="block text-xs font-medium text-slate-500 dark:text-slate-400 mb-1">Source App</label>
            <select
              v-model="activeFilters.source_app"
              class="w-full text-sm rounded-lg border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-700 text-slate-700 dark:text-slate-200 px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-violet-500 focus:border-transparent"
            >
              <option value="">All</option>
              <option v-for="app in filterOptions.source_apps" :key="app" :value="app">{{ app }}</option>
            </select>
          </div>

          <!-- session_id -->
          <div>
            <label class="block text-xs font-medium text-slate-500 dark:text-slate-400 mb-1">Session</label>
            <select
              v-model="activeFilters.session_id"
              class="w-full text-sm rounded-lg border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-700 text-slate-700 dark:text-slate-200 px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-violet-500 focus:border-transparent"
            >
              <option value="">All</option>
              <option v-for="sid in filterOptions.session_ids" :key="sid" :value="sid">{{ sid.slice(0, 16) }}…</option>
            </select>
          </div>

          <!-- hook_event_type -->
          <div>
            <label class="block text-xs font-medium text-slate-500 dark:text-slate-400 mb-1">Event Type</label>
            <select
              v-model="activeFilters.hook_event_type"
              class="w-full text-sm rounded-lg border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-700 text-slate-700 dark:text-slate-200 px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-violet-500 focus:border-transparent"
            >
              <option value="">All</option>
              <option v-for="type in filterOptions.hook_event_types" :key="type" :value="type">{{ type }}</option>
            </select>
          </div>
        </div>
      </div>

      <!-- Cost summary card -->
      <div class="lg:w-72 flex-shrink-0">
        <CostSummaryCard :summary="summary" :loading="costsLoading" />
      </div>
    </div>

    <!-- Event list -->
    <div class="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl shadow-sm overflow-hidden">
      <!-- List toolbar -->
      <div class="flex items-center justify-between px-4 py-3 border-b border-slate-200 dark:border-slate-700">
        <span class="text-sm font-medium text-slate-700 dark:text-slate-300">Events</span>
        <label class="flex items-center gap-2 cursor-pointer select-none">
          <span class="text-xs text-slate-500 dark:text-slate-400">Pause scroll</span>
          <button
            @click="pauseScroll = !pauseScroll"
            :class="[
              'relative inline-flex h-5 w-9 items-center rounded-full transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-violet-500 focus:ring-offset-2',
              pauseScroll ? 'bg-violet-600' : 'bg-slate-200 dark:bg-slate-600'
            ]"
          >
            <span
              :class="[
                'inline-block h-3.5 w-3.5 rounded-full bg-white shadow transition-transform duration-200',
                pauseScroll ? 'translate-x-4.5' : 'translate-x-0.5'
              ]"
            ></span>
          </button>
        </label>
      </div>

      <!-- Scrollable list -->
      <div
        ref="scrollContainer"
        class="overflow-y-auto max-h-[60vh]"
      >
        <div v-if="filteredEvents.length === 0" class="flex flex-col items-center justify-center py-16 text-slate-400 dark:text-slate-500">
          <svg class="w-10 h-10 mb-3 opacity-40" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M13 10V3L4 14h7v7l9-11h-7z" />
          </svg>
          <p class="text-sm">No events yet</p>
          <p class="text-xs mt-1">{{ connected ? 'Waiting for hook events…' : 'Connecting to stream…' }}</p>
        </div>

        <div v-else class="divide-y divide-slate-100 dark:divide-slate-700/50 p-3 space-y-1.5">
          <LiveEventRow
            v-for="event in filteredEvents"
            :key="event.id"
            :event="event"
          />
        </div>
      </div>
    </div>
  </div>
</template>
