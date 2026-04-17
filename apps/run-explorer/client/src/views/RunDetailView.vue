<script setup lang="ts">
import { computed, ref, toRef, onMounted } from 'vue'
import { useRouter, RouterLink } from 'vue-router'
import { useRunDetail } from '@/composables/useRunDetail'
import { API_BASE_URL } from '@/config'
import type { RunCosts } from '@shared/types'
import { useOrchEvents } from '@/composables/useOrchEvents'
import StatusBadge from '@/components/StatusBadge.vue'
import WaveStepBar from '@/components/WaveStepBar.vue'
import LeadAccordion from '@/components/LeadAccordion.vue'
import EvaluationCard from '@/components/EvaluationCard.vue'
import EmptyState from '@/components/EmptyState.vue'
import TimelineEvent from '@/components/TimelineEvent.vue'
import EventStatusBadge from '@/components/EventStatusBadge.vue'
import { renderMarkdown } from '@/utils/markdown'

const props = defineProps<{ id: string }>()
const router = useRouter()

const idRef = toRef(props, 'id')
const { run, loading, error, notFound } = useRunDetail(idRef)

const activeTab = ref<'overview' | 'timeline'>('overview')
const { events: orchEvents, loading: eventsLoading, error: eventsError } = useOrchEvents(idRef)

function formatDate(iso: string): string {
  const d = new Date(iso)
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }) + ' ' +
    d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false })
}

const missionBriefHtml = computed(() => run.value?.missionBrief ? renderMarkdown(run.value.missionBrief) : '')
const acceptanceCriteriaHtml = computed(() => run.value?.acceptanceCriteria ? renderMarkdown(run.value.acceptanceCriteria) : '')
const evaluationFullHtml = computed(() => run.value?.evaluationFull ? renderMarkdown(run.value.evaluationFull) : '')

const sessions = ref<Array<{ id: string; promptCount: number }>>([])
const sessionsError = ref<string | null>(null)
const sessionsLoading = ref(false)

const loadSessions = async () => {
  sessionsLoading.value = true
  try {
    const controller = new AbortController()
    setTimeout(() => controller.abort(), 10000)
    const res = await fetch(`${API_BASE_URL}/api/runs/${props.id}/sessions`, { signal: controller.signal })
    if (!res.ok) throw new Error(`${res.status}`)
    sessions.value = await res.json()
  } catch (err) {
    sessionsError.value = err instanceof Error ? err.message : 'failed to load sessions'
  } finally {
    sessionsLoading.value = false
  }
}

const costs = ref<RunCosts | null>(null)

async function fetchCosts() {
  try {
    const res = await fetch(`${API_BASE_URL}/api/runs/${props.id}/costs`)
    if (res.ok) costs.value = await res.json()
  } catch { /* silent — cost data is optional */ }
}

onMounted(() => {
  loadSessions()
  fetchCosts()
})
</script>

<template>
  <div class="space-y-6 fade-in">
    <!-- Back navigation -->
    <button
      class="flex items-center gap-1.5 text-sm text-slate-500 dark:text-slate-400 hover:text-violet-600 dark:hover:text-violet-400 transition-colors duration-200 focus-visible:ring-2 focus-visible:ring-violet-500 focus-visible:ring-offset-2 rounded"
      @click="router.push('/')"
    >
      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
      </svg>
      Back to all runs
    </button>

    <!-- 404 state -->
    <div v-if="notFound">
      <EmptyState
        title="Run not found"
        description="This run ID doesn't exist or has been deleted."
        icon="search"
        cta-label="Back to all runs"
        @cta="router.push('/')"
      />
    </div>

    <!-- Error state -->
    <div v-else-if="error" class="glass-card p-8 text-center">
      <p class="text-sm text-red-600 dark:text-red-400 mb-3">{{ error }}</p>
      <button
        class="px-4 py-2 rounded-xl bg-violet-600 hover:bg-violet-700 text-white text-sm font-medium transition-colors duration-200"
        @click="router.push('/')"
      >
        Back to all runs
      </button>
    </div>

    <template v-else>
      <!-- Header card -->
      <div class="glass-card p-6">
        <div v-if="loading" class="flex items-center gap-4 animate-pulse">
          <div class="h-6 bg-slate-200 dark:bg-slate-700 rounded w-48"></div>
          <div class="h-6 bg-slate-200 dark:bg-slate-700 rounded-full w-16"></div>
        </div>
        <template v-else-if="run">
          <div class="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
            <div>
              <div class="flex items-center gap-3 mb-1">
                <h1 class="text-xl font-semibold text-slate-900 dark:text-white tracking-tight font-mono">{{ run.id }}</h1>
                <StatusBadge :status="run.status" />
              </div>
              <p class="text-xs text-slate-400 dark:text-slate-500 font-mono">
                Started {{ formatDate(run.startTime) }}
                <span v-if="run.project" class="ml-2 px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400">{{ run.project }}</span>
              </p>
            </div>
            <div class="flex items-center gap-4 text-sm">
              <div class="text-center">
                <div class="text-2xl font-bold text-slate-900 dark:text-white tabular-nums">{{ run.waveCount }}</div>
                <div class="text-xs text-slate-500 dark:text-slate-400 uppercase tracking-wide">Waves</div>
              </div>
              <div class="text-center">
                <div class="text-2xl font-bold text-slate-900 dark:text-white tabular-nums">{{ run.leadCount }}</div>
                <div class="text-xs text-slate-500 dark:text-slate-400 uppercase tracking-wide">Leads</div>
              </div>
              <div class="text-center">
                <div class="text-2xl font-bold text-slate-900 dark:text-white tabular-nums">{{ (run.tokenEstimate / 1000).toFixed(1) }}k</div>
                <div class="text-xs text-slate-500 dark:text-slate-400 uppercase tracking-wide">Tokens</div>
              </div>
            </div>
          </div>
        </template>
      </div>

      <!-- Tab strip -->
      <div class="flex gap-1 border-b border-slate-200 dark:border-slate-700">
        <button
          v-for="tab in ['overview', 'timeline'] as const"
          :key="tab"
          :class="[
            'px-4 py-2 text-sm font-medium capitalize transition-colors duration-200',
            activeTab === tab
              ? 'border-b-2 border-violet-600 text-violet-600 dark:text-violet-400'
              : 'text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200'
          ]"
          @click="activeTab = tab"
        >{{ tab }}</button>
      </div>

      <!-- Overview tab -->
      <template v-if="activeTab === 'overview'">
        <!-- Wave step-bar card -->
        <div class="glass-card px-2">
          <div v-if="loading" class="flex items-center gap-4 px-4 py-6 animate-pulse">
            <template v-for="i in 4" :key="i">
              <div class="flex flex-col items-center gap-1.5">
                <div class="w-8 h-8 rounded-full bg-slate-200 dark:bg-slate-700"></div>
                <div class="h-3 bg-slate-200 dark:bg-slate-700 rounded w-12"></div>
              </div>
              <div v-if="i < 4" class="flex-1 h-0.5 bg-slate-200 dark:bg-slate-700 mb-5"></div>
            </template>
          </div>
          <WaveStepBar v-else-if="run" :leads="run.leads" :wave-count="run.waveCount" />
        </div>

        <!-- Evaluation card (only if data exists) -->
        <EvaluationCard
          v-if="run && (run.evaluationScore !== null || run.evaluationVerdict !== null)"
          :score="run?.evaluationScore ?? null"
          :verdict="run?.evaluationVerdict ?? null"
        />

        <!-- Mission brief -->
        <div v-if="run?.missionBrief" class="glass-card p-6">
          <h2 class="text-base font-semibold text-slate-800 dark:text-slate-200 tracking-tight mb-4">Mission Brief</h2>
          <div
            class="prose-content text-sm text-slate-600 dark:text-slate-400 bg-slate-50 dark:bg-slate-900/50 rounded-xl p-4 overflow-auto max-h-64"
            v-html="missionBriefHtml"
          ></div>
        </div>

        <!-- Acceptance Criteria -->
        <div v-if="run?.acceptanceCriteria" class="glass-card p-6">
          <h2 class="text-base font-semibold text-slate-800 dark:text-slate-200 tracking-tight mb-4">Acceptance Criteria</h2>
          <div
            class="prose-content text-sm text-slate-600 dark:text-slate-400 bg-slate-50 dark:bg-slate-900/50 rounded-xl p-4 overflow-auto max-h-64"
            v-html="acceptanceCriteriaHtml"
          ></div>
        </div>

        <!-- Full Evaluation report -->
        <div v-if="run?.evaluationFull" class="glass-card p-6">
          <h2 class="text-base font-semibold text-slate-800 dark:text-slate-200 tracking-tight mb-4">Full Evaluation</h2>
          <div
            class="prose-content text-sm text-slate-600 dark:text-slate-400 bg-slate-50 dark:bg-slate-900/50 rounded-xl p-4 overflow-auto max-h-96"
            v-html="evaluationFullHtml"
          ></div>
        </div>

        <!-- Lead accordions -->
        <div v-if="run || loading">
          <h2 class="text-base font-semibold text-slate-800 dark:text-slate-200 tracking-tight mb-3">Leads</h2>
          <div v-if="loading" class="space-y-3">
            <div v-for="i in 4" :key="i" class="glass-card h-16 animate-pulse"></div>
          </div>
          <div v-else-if="run?.leads?.length" class="space-y-3">
            <LeadAccordion
              v-for="lead in run.leads"
              :key="lead.name"
              :lead="lead"
              :run-id="run.id"
            />
          </div>
          <EmptyState
            v-else-if="run"
            title="No leads"
            description="No lead data found for this run."
            icon="inbox"
          />
        </div>
      </template>

      <!-- Timeline tab -->
      <template v-else>
        <div class="glass-card p-5">
          <div v-if="eventsLoading" class="space-y-3">
            <div v-for="i in 5" :key="i" class="h-12 bg-slate-200 dark:bg-slate-700 rounded animate-pulse" />
          </div>
          <div v-else-if="eventsError" class="text-sm text-red-600 dark:text-red-400">{{ eventsError }}</div>
          <div v-else-if="orchEvents.length === 0" class="text-sm text-slate-500 dark:text-slate-400 py-4 text-center">No events recorded for this run.</div>
          <div v-else class="space-y-1 max-h-[600px] overflow-y-auto">
            <TimelineEvent v-for="event in orchEvents" :key="`${event.ts}-${event.agent}`" :event="event" />
          </div>
        </div>
      </template>

      <!-- Token & Cost Breakdown -->
      <div v-if="costs" class="cost-section mt-6">
        <h3 class="text-lg font-semibold mb-2">Token &amp; Cost Breakdown</h3>
        <div class="cost-summary flex gap-4 mb-3 text-sm text-gray-600">
          <span>Total: <strong>${{ costs.totalCostUsd.toFixed(4) }}</strong></span>
          <span>Input: {{ costs.totalInputTokens.toLocaleString() }}t</span>
          <span>Output: {{ costs.totalOutputTokens.toLocaleString() }}t</span>
          <span>Cache: {{ costs.totalCacheReadTokens.toLocaleString() }}t</span>
        </div>
        <table class="w-full text-sm border-collapse">
          <thead>
            <tr class="border-b">
              <th class="text-left py-1 pr-4">Agent</th>
              <th class="text-left py-1 pr-4">Model</th>
              <th class="text-right py-1 pr-4">Input</th>
              <th class="text-right py-1 pr-4">Output</th>
              <th class="text-right py-1 pr-4">Cache</th>
              <th class="text-right py-1">Cost</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="a in costs.agents" :key="a.agentName" class="border-b border-gray-100">
              <td class="py-1 pr-4 font-mono text-xs">{{ a.agentName }}</td>
              <td class="py-1 pr-4 text-gray-500">{{ a.tier }}</td>
              <td class="text-right py-1 pr-4">{{ a.inputTokens.toLocaleString() }}</td>
              <td class="text-right py-1 pr-4">{{ a.outputTokens.toLocaleString() }}</td>
              <td class="text-right py-1 pr-4">{{ a.cacheReadTokens.toLocaleString() }}</td>
              <td class="text-right py-1">${{ a.costUsd.toFixed(4) }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Spawned Sessions -->
      <div class="mt-6">
        <h2 class="text-lg font-semibold text-gray-900 dark:text-white mb-3">Spawned Sessions</h2>
        <div v-if="sessionsLoading" class="text-sm text-gray-400">Loading...</div>
        <div v-else-if="sessionsError" class="text-sm text-red-500">{{ sessionsError }}</div>
        <div v-else-if="sessions.length === 0" class="text-sm text-gray-400">No sessions recorded for this run.</div>
        <div v-else class="space-y-2">
          <RouterLink
            v-for="s in sessions"
            :key="s.id"
            :to="`/sessions/${s.id}`"
            class="block p-3 bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-700 rounded hover:border-gray-300 dark:hover:border-slate-600"
          >
            <span class="font-mono text-sm text-gray-700 dark:text-slate-300">{{ s.id }}</span>
            <span class="ml-3 text-xs text-gray-400 dark:text-slate-500">{{ s.promptCount }} prompts</span>
          </RouterLink>
        </div>
      </div>
    </template>
  </div>
</template>
