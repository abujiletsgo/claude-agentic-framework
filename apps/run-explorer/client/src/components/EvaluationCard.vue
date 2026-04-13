<script setup lang="ts">
defineProps<{
  score: number | null
  verdict: 'SHIP' | 'NEEDS REWORK' | null
}>()
</script>

<template>
  <div class="glass-card p-5">
    <h2 class="text-base font-semibold text-slate-800 dark:text-slate-200 tracking-tight mb-4">Evaluation</h2>

    <div class="flex items-center gap-4">
      <!-- Score -->
      <div class="flex flex-col items-center justify-center w-20 h-20 rounded-2xl bg-slate-50 dark:bg-slate-700/50 border border-slate-200 dark:border-slate-600">
        <span v-if="score !== null" class="text-2xl font-bold text-slate-900 dark:text-white tabular-nums">{{ score }}</span>
        <span v-else class="text-2xl font-bold text-slate-400">—</span>
        <span class="text-xs text-slate-500 dark:text-slate-400 mt-0.5">Score</span>
      </div>

      <!-- Verdict -->
      <div>
        <div v-if="verdict === 'SHIP'" class="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-700">
          <svg class="w-5 h-5 text-emerald-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <span class="text-sm font-bold text-emerald-700 dark:text-emerald-300">SHIP</span>
        </div>
        <div v-else-if="verdict === 'NEEDS REWORK'" class="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-700">
          <svg class="w-5 h-5 text-amber-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
          <span class="text-sm font-bold text-amber-700 dark:text-amber-300">NEEDS REWORK</span>
        </div>
        <div v-else class="text-sm text-slate-400 dark:text-slate-500 italic">No evaluation available</div>
      </div>
    </div>
  </div>
</template>
