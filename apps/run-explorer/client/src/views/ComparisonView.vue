<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useRuns } from '@/composables/useRuns'
import { useComparison } from '@/composables/useComparison'
import RunSelector from '@/components/RunSelector.vue'
import ComparisonTable from '@/components/ComparisonTable.vue'
import StatusBadge from '@/components/StatusBadge.vue'
import EmptyState from '@/components/EmptyState.vue'

const route = useRoute()
const router = useRouter()

const { runs, loading: runsLoading } = useRuns()

const selectedA = ref((route.query.a as string) ?? '')
const selectedB = ref((route.query.b as string) ?? '')

// Sync URL query params
watch([selectedA, selectedB], ([a, b]) => {
  router.replace({ query: { ...(a ? { a } : {}), ...(b ? { b } : {}) } })
})

const { result, loading: compLoading, error: compError } = useComparison(selectedA, selectedB)

const runA = computed(() => runs.value.find(r => r.id === selectedA.value) ?? null)
const runB = computed(() => runs.value.find(r => r.id === selectedB.value) ?? null)
const hasSelection = computed(() => !!selectedA.value && !!selectedB.value)
</script>

<template>
  <div class="space-y-6 fade-in">
    <div>
      <h1 class="text-xl font-semibold text-slate-900 dark:text-white tracking-tight">Compare Runs</h1>
      <p class="text-xs text-slate-500 dark:text-slate-400 mt-0.5">Side-by-side metric comparison</p>
    </div>

    <!-- Run selectors -->
    <div class="glass-card p-5">
      <div class="flex flex-col sm:flex-row gap-4 items-end">
        <RunSelector
          v-model="selectedA"
          :runs="runs"
          label="Run A"
          :disabled="runsLoading"
        />
        <div class="flex-shrink-0 pb-0.5">
          <svg class="w-5 h-5 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" />
          </svg>
        </div>
        <RunSelector
          v-model="selectedB"
          :runs="runs"
          label="Run B"
          :disabled="runsLoading"
        />
      </div>
    </div>

    <!-- Empty: no selection -->
    <EmptyState
      v-if="!hasSelection"
      title="Select two runs to compare"
      description="Choose runs from the dropdowns above to see a side-by-side comparison."
      icon="compare"
    />

    <!-- Loading comparison -->
    <div v-else-if="compLoading" class="space-y-4">
      <!-- Header row skeleton -->
      <div class="glass-card p-5 animate-pulse">
        <div class="flex gap-6">
          <div class="h-6 bg-slate-200 dark:bg-slate-700 rounded w-40"></div>
          <div class="h-6 bg-slate-200 dark:bg-slate-700 rounded w-40"></div>
        </div>
      </div>
      <!-- Table skeleton -->
      <div class="glass-card overflow-hidden">
        <div v-for="i in 3" :key="i" class="flex items-center gap-4 px-4 py-3 border-b border-slate-100 dark:border-slate-700/50 animate-pulse">
          <div class="h-4 bg-slate-200 dark:bg-slate-700 rounded w-24"></div>
          <div class="flex-1 h-4 bg-slate-200 dark:bg-slate-700 rounded"></div>
          <div class="flex-1 h-4 bg-slate-200 dark:bg-slate-700 rounded"></div>
        </div>
      </div>
    </div>

    <!-- Error -->
    <div v-else-if="compError" class="glass-card p-6 text-center">
      <p class="text-sm text-red-600 dark:text-red-400">{{ compError }}</p>
    </div>

    <!-- Result -->
    <template v-else-if="result">
      <!-- Run headers -->
      <div class="grid grid-cols-2 gap-4">
        <div class="glass-card p-4">
          <div class="text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-2">Run A</div>
          <div class="font-mono text-sm font-semibold text-slate-800 dark:text-slate-200 mb-1">{{ result.runA.id.slice(0, 16) }}</div>
          <StatusBadge :status="result.runA.status" />
        </div>
        <div class="glass-card p-4">
          <div class="text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-2">Run B</div>
          <div class="font-mono text-sm font-semibold text-slate-800 dark:text-slate-200 mb-1">{{ result.runB.id.slice(0, 16) }}</div>
          <StatusBadge :status="result.runB.status" />
        </div>
      </div>

      <!-- Comparison table -->
      <ComparisonTable :result="result" />
    </template>
  </div>
</template>
