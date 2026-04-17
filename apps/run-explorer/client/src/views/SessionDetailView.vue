<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter, RouterLink } from 'vue-router'
import type { SessionDetail } from '@shared/types'
import { API_BASE_URL } from '@/config'

const props = defineProps<{ id: string }>()
const router = useRouter()

const session = ref<SessionDetail | null>(null)
const loading = ref(false)
const error = ref<string | null>(null)
const notFound = ref(false)

async function fetchSession() {
  loading.value = true
  error.value = null
  notFound.value = false
  try {
    const res = await fetch(`${API_BASE_URL}/api/sessions/${props.id}`)
    if (res.status === 404) {
      notFound.value = true
      return
    }
    if (!res.ok) {
      const body = await res.json().catch(() => ({ error: 'Unknown error' }))
      throw new Error(body.error ?? `HTTP ${res.status}`)
    }
    session.value = await res.json() as SessionDetail
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Failed to load session'
  } finally {
    loading.value = false
  }
}

onMounted(fetchSession)

function formatDate(iso: string): string {
  const d = new Date(iso)
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }) + ' ' +
    d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false })
}

function formatDuration(seconds: number | undefined): string {
  if (seconds === undefined) return '—'
  if (seconds < 60) return `${seconds}s`
  const m = Math.floor(seconds / 60)
  const s = seconds % 60
  return `${m}m ${s}s`
}

function eventLabel(type: string): string {
  if (type === 'SessionStart') return 'Session started'
  if (type === 'UserPromptSubmit') return 'User prompt'
  if (type === 'Stop') return 'Session ended'
  return type
}

function eventPayloadText(content: string): string {
  try {
    const p = JSON.parse(content) as Record<string, unknown>
    if (typeof p['prompt'] === 'string') return p['prompt']
    if (typeof p['cwd'] === 'string') return p['cwd']
  } catch {
    // ignore
  }
  return content
}

function eventColor(type: string): string {
  if (type === 'SessionStart') return 'bg-violet-500'
  if (type === 'UserPromptSubmit') return 'bg-blue-500'
  if (type === 'Stop') return 'bg-slate-400'
  return 'bg-slate-300'
}
</script>

<template>
  <div class="space-y-6 fade-in">
    <!-- Back navigation -->
    <button
      class="flex items-center gap-1.5 text-sm text-slate-500 dark:text-slate-400 hover:text-violet-600 dark:hover:text-violet-400 transition-colors duration-200 focus-visible:ring-2 focus-visible:ring-violet-500 focus-visible:ring-offset-2 rounded"
      @click="router.push('/sessions')"
    >
      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
      </svg>
      Back to all sessions
    </button>

    <!-- 404 state -->
    <div v-if="notFound" class="glass-card p-12 text-center">
      <p class="text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Session not found</p>
      <p class="text-xs text-slate-500 dark:text-slate-400">ID: {{ id }}</p>
    </div>

    <!-- Error state -->
    <div v-else-if="error" class="glass-card p-6 text-center">
      <p class="text-sm text-red-600 dark:text-red-400 mb-3">{{ error }}</p>
      <button
        class="px-4 py-2 rounded-xl bg-violet-600 hover:bg-violet-700 text-white text-sm font-medium transition-colors duration-200"
        @click="fetchSession"
      >
        Retry
      </button>
    </div>

    <!-- Loading skeleton -->
    <template v-else-if="loading">
      <div class="glass-card p-6 animate-pulse space-y-3">
        <div class="h-5 bg-slate-200 dark:bg-slate-700 rounded w-48"></div>
        <div class="h-3 bg-slate-200 dark:bg-slate-700 rounded w-64"></div>
      </div>
      <div class="glass-card p-6 animate-pulse space-y-4">
        <div v-for="i in 4" :key="i" class="flex gap-3">
          <div class="w-2.5 h-2.5 rounded-full bg-slate-200 dark:bg-slate-700 mt-1 shrink-0"></div>
          <div class="flex-1 space-y-1.5">
            <div class="h-3 bg-slate-200 dark:bg-slate-700 rounded w-24"></div>
            <div class="h-3 bg-slate-200 dark:bg-slate-700 rounded w-full"></div>
          </div>
        </div>
      </div>
    </template>

    <!-- Session content -->
    <template v-else-if="session">
      <!-- Summary card -->
      <div class="glass-card p-6">
        <div class="flex items-start justify-between gap-4">
          <div>
            <h1 class="text-lg font-semibold text-slate-900 dark:text-white tracking-tight font-mono">{{ session.id }}</h1>
            <p v-if="session.project" class="text-sm text-slate-500 dark:text-slate-400 mt-0.5">{{ session.project }}</p>
            <div v-if="session.orchRunId" class="mt-2">
              <span class="text-xs text-slate-500 dark:text-slate-400">Spawned by orch run: </span>
              <RouterLink
                :to="`/runs/${session.orchRunId}`"
                class="text-xs font-mono text-violet-600 dark:text-violet-400 hover:underline"
              >
                {{ session.orchRunId }}
              </RouterLink>
            </div>
          </div>
          <span
            :class="[
              'inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold shrink-0',
              session.status === 'active'
                ? 'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-400'
                : 'bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-400'
            ]"
          >
            {{ session.status === 'active' ? 'Active' : 'Ended' }}
          </span>
        </div>

        <!-- Metadata grid -->
        <div class="mt-4 grid grid-cols-2 sm:grid-cols-4 gap-4">
          <div>
            <p class="text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wide">Started</p>
            <p class="text-sm text-slate-700 dark:text-slate-300 mt-0.5 tabular-nums">{{ formatDate(session.startTime) }}</p>
          </div>
          <div v-if="session.endTime">
            <p class="text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wide">Ended</p>
            <p class="text-sm text-slate-700 dark:text-slate-300 mt-0.5 tabular-nums">{{ formatDate(session.endTime) }}</p>
          </div>
          <div>
            <p class="text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wide">Prompts</p>
            <p class="text-sm text-slate-700 dark:text-slate-300 mt-0.5 tabular-nums">{{ session.promptCount }}</p>
          </div>
          <div>
            <p class="text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wide">Duration</p>
            <p class="text-sm text-slate-700 dark:text-slate-300 mt-0.5 tabular-nums">{{ formatDuration(session.durationSeconds) }}</p>
          </div>
        </div>
      </div>

      <!-- Timeline -->
      <div class="glass-card p-6">
        <h2 class="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-5 uppercase tracking-wide">Event Timeline</h2>

        <div v-if="session.messages.length === 0" class="text-center py-8">
          <p class="text-sm text-slate-500 dark:text-slate-400">No events recorded for this session.</p>
        </div>

        <ol v-else class="relative border-l border-slate-200 dark:border-slate-700 space-y-6 ml-2">
          <li
            v-for="msg in session.messages"
            :key="msg.id"
            class="ml-6"
          >
            <!-- Dot -->
            <span
              :class="[
                'absolute -left-1.5 flex w-3 h-3 rounded-full ring-2 ring-white dark:ring-slate-900',
                eventColor(msg.type)
              ]"
            ></span>

            <div class="flex items-baseline gap-2 mb-0.5">
              <span class="text-xs font-semibold text-slate-700 dark:text-slate-300">{{ eventLabel(msg.type) }}</span>
              <span class="text-xs text-slate-400 dark:text-slate-500 tabular-nums">{{ formatDate(msg.timestamp) }}</span>
            </div>

            <p class="text-xs text-slate-500 dark:text-slate-400 break-words">{{ eventPayloadText(msg.content) }}</p>
          </li>
        </ol>
      </div>
    </template>
  </div>
</template>
