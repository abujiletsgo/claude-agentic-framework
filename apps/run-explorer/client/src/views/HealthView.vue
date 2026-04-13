<script setup lang="ts">
import { useHealth } from '@/composables/useHealth'
import EventsTable from '@/components/EventsTable.vue'
import EmptyState from '@/components/EmptyState.vue'

const { events, loading, error, refresh } = useHealth()
</script>

<template>
  <div class="space-y-6 fade-in">
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-xl font-semibold text-slate-900 dark:text-white tracking-tight">Health</h1>
        <p class="text-xs text-slate-500 dark:text-slate-400 mt-0.5">Recent hook events from events.db</p>
      </div>
      <button
        class="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors duration-200 focus-visible:ring-2 focus-visible:ring-violet-500 focus-visible:ring-offset-2"
        :disabled="loading"
        @click="refresh"
        aria-label="Refresh events"
      >
        <svg class="w-4 h-4" :class="{ 'animate-spin': loading }" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
        </svg>
        Refresh
      </button>
    </div>

    <!-- Stats card -->
    <div class="glass-card p-5">
      <div class="flex items-center gap-6">
        <div>
          <div class="text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-1">Total Events (shown)</div>
          <div v-if="loading" class="h-8 w-16 bg-slate-200 dark:bg-slate-700 rounded animate-pulse"></div>
          <div v-else class="text-2xl font-bold text-slate-900 dark:text-white tabular-nums">{{ events.length }}</div>
        </div>
        <div>
          <div class="text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-1">Status</div>
          <div class="flex items-center gap-1.5">
            <span :class="['w-2 h-2 rounded-full', error ? 'bg-red-500' : 'bg-emerald-500']"></span>
            <span class="text-sm font-medium text-slate-700 dark:text-slate-300">{{ error ? 'Error' : 'OK' }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Error state -->
    <div v-if="error" class="glass-card p-6 text-center">
      <p class="text-sm text-red-600 dark:text-red-400 mb-3">{{ error }}</p>
      <button
        class="px-4 py-2 rounded-xl bg-violet-600 hover:bg-violet-700 text-white text-sm font-medium transition-colors duration-200"
        @click="refresh"
      >
        Retry
      </button>
    </div>

    <!-- Events table -->
    <div v-else class="glass-card overflow-hidden">
      <div v-if="loading" class="divide-y divide-slate-100 dark:divide-slate-700/50">
        <div v-for="i in 5" :key="i" class="flex items-center gap-4 px-4 py-3 animate-pulse">
          <div class="h-4 bg-slate-200 dark:bg-slate-700 rounded w-8"></div>
          <div class="h-4 bg-slate-200 dark:bg-slate-700 rounded w-32"></div>
          <div class="h-4 bg-slate-200 dark:bg-slate-700 rounded w-28"></div>
          <div class="h-4 bg-slate-200 dark:bg-slate-700 rounded flex-1"></div>
        </div>
      </div>
      <EmptyState
        v-else-if="events.length === 0"
        title="No events"
        description="No hook events found in the database."
        icon="inbox"
      />
      <EventsTable v-else :events="events" />
    </div>
  </div>
</template>
