<script setup lang="ts">
import type { Run } from '@shared/types'

defineProps<{
  runs: Run[]
  modelValue: string
  label: string
  disabled?: boolean
}>()

defineEmits<{
  'update:modelValue': [value: string]
}>()

function formatDate(iso: string): string {
  const d = new Date(iso)
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) + ' ' +
    d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: false })
}
</script>

<template>
  <div class="flex-1 space-y-1.5">
    <label class="text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wide">{{ label }}</label>
    <select
      :value="modelValue"
      :disabled="disabled"
      class="w-full px-3 py-2 text-sm bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-600 rounded-xl text-slate-700 dark:text-slate-300 focus:outline-none focus:ring-2 focus:ring-violet-500 focus:border-transparent transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
      @change="$emit('update:modelValue', ($event.target as HTMLSelectElement).value)"
    >
      <option value="">Select a run...</option>
      <option v-for="run in runs" :key="run.id" :value="run.id">
        {{ run.id.slice(0, 12) }} — {{ formatDate(run.startTime) }} ({{ run.status }})
      </option>
    </select>
  </div>
</template>
