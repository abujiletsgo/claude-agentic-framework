<script setup lang="ts">
import type { Event } from '@shared/types'

defineProps<{
  events: Event[]
}>()

function formatDate(iso: string): string {
  const d = new Date(iso)
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) + ' ' +
    d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false })
}
</script>

<template>
  <div class="overflow-x-auto">
    <table class="w-full text-sm">
      <thead class="bg-slate-50/80 dark:bg-slate-800/50">
        <tr>
          <th class="px-4 py-3 text-left text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wide">ID</th>
          <th class="px-4 py-3 text-left text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wide">Type</th>
          <th class="px-4 py-3 text-left text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wide">Timestamp</th>
          <th class="px-4 py-3 text-left text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wide">Metadata</th>
        </tr>
      </thead>
      <tbody class="divide-y divide-slate-100 dark:divide-slate-700/50">
        <tr v-for="event in events" :key="event.id" class="hover:bg-slate-50/50 dark:hover:bg-slate-700/10">
          <td class="px-4 py-3 text-xs text-slate-400 dark:text-slate-500 font-mono tabular-nums">{{ event.id }}</td>
          <td class="px-4 py-3">
            <span class="inline-flex items-center px-2 py-0.5 rounded-md bg-slate-100 dark:bg-slate-700 text-xs font-mono text-slate-600 dark:text-slate-300">
              {{ event.type }}
            </span>
          </td>
          <td class="px-4 py-3 text-xs text-slate-400 dark:text-slate-500 font-mono tabular-nums whitespace-nowrap">
            {{ formatDate(event.timestamp) }}
          </td>
          <td class="px-4 py-3 text-xs text-slate-500 dark:text-slate-400 font-mono max-w-xs truncate">
            {{ event.metadata }}
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
