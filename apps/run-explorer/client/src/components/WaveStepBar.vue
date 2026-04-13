<script setup lang="ts">
import type { LeadSummary, RunStatus } from '@shared/types'

const props = defineProps<{
  leads: LeadSummary[]
  waveCount: number
}>()

// Build wave nodes from leads
interface WaveNode {
  wave: number
  status: RunStatus
}

function buildWaves(): WaveNode[] {
  const waveMap = new Map<number, RunStatus[]>()
  for (const lead of props.leads) {
    const existing = waveMap.get(lead.wave) ?? []
    existing.push(lead.status)
    waveMap.set(lead.wave, existing)
  }

  const nodes: WaveNode[] = []
  for (let w = 0; w <= props.waveCount; w++) {
    const statuses = waveMap.get(w)
    if (!statuses) {
      nodes.push({ wave: w, status: 'UNKNOWN' })
      continue
    }
    if (statuses.includes('FAIL')) {
      nodes.push({ wave: w, status: 'FAIL' })
    } else if (statuses.includes('IN_PROGRESS')) {
      nodes.push({ wave: w, status: 'IN_PROGRESS' })
    } else if (statuses.every(s => s === 'PASS')) {
      nodes.push({ wave: w, status: 'PASS' })
    } else {
      nodes.push({ wave: w, status: 'UNKNOWN' })
    }
  }
  return nodes
}

function nodeClasses(status: RunStatus): string {
  switch (status) {
    case 'PASS': return 'bg-emerald-500 border-emerald-500 text-white shadow-md shadow-emerald-500/30'
    case 'IN_PROGRESS': return 'bg-amber-500 border-amber-500 text-white shadow-md shadow-amber-500/30 animate-pulse'
    case 'FAIL': return 'bg-red-500 border-red-500 text-white shadow-md shadow-red-500/30'
    default: return 'bg-white dark:bg-slate-800 border-slate-300 dark:border-slate-600 text-slate-400 dark:text-slate-500'
  }
}

function connectorClasses(status: RunStatus): string {
  switch (status) {
    case 'PASS': return 'bg-emerald-200 dark:bg-emerald-800/50'
    case 'FAIL': return 'bg-red-200 dark:bg-red-800/50'
    default: return 'bg-slate-200 dark:bg-slate-700'
  }
}
</script>

<template>
  <div class="relative flex items-center w-full px-4 py-6">
    <div class="relative z-10 flex items-start justify-between w-full">
      <template v-for="(node, i) in buildWaves()" :key="node.wave">
        <!-- Wave node -->
        <div class="flex flex-col items-center gap-1.5">
          <div
            :class="['w-8 h-8 rounded-full border-2 flex items-center justify-center text-xs font-bold', nodeClasses(node.status)]"
          >
            <svg v-if="node.status === 'PASS'" class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M5 13l4 4L19 7" />
            </svg>
            <svg v-else-if="node.status === 'FAIL'" class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M6 18L18 6M6 6l12 12" />
            </svg>
            <span v-else>{{ node.wave }}</span>
          </div>
          <span class="text-xs text-slate-500 dark:text-slate-400 font-medium whitespace-nowrap">Wave {{ node.wave }}</span>
        </div>

        <!-- Connector between nodes -->
        <div
          v-if="i < buildWaves().length - 1"
          :class="['flex-1 h-0.5 self-center mb-5', connectorClasses(node.status)]"
        ></div>
      </template>
    </div>
  </div>
</template>
