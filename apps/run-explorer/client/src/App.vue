<script setup lang="ts">
import { RouterView, RouterLink, useRoute } from 'vue-router'
import { computed, ref, onMounted } from 'vue'

const route = useRoute()

const navLinks = [
  { to: '/', label: 'Runs' },
  { to: '/compare', label: 'Compare' },
  { to: '/health', label: 'Health' },
  { to: '/live', label: 'Live' },
]

function isActive(path: string): boolean {
  if (path === '/') return route.path === '/'
  return route.path.startsWith(path)
}

// Dark mode
const isDark = ref(false)

onMounted(() => {
  const stored = localStorage.getItem('theme')
  isDark.value = stored === 'dark' || (!stored && window.matchMedia('(prefers-color-scheme: dark)').matches)
  applyDark(isDark.value)
})

function applyDark(dark: boolean) {
  document.documentElement.classList.toggle('dark', dark)
}

function toggleDark() {
  isDark.value = !isDark.value
  localStorage.setItem('theme', isDark.value ? 'dark' : 'light')
  applyDark(isDark.value)
}
</script>

<template>
  <div class="min-h-screen bg-gradient-to-br from-slate-50 via-white to-slate-100 dark:from-slate-900 dark:via-slate-800 dark:to-slate-900">
    <!-- Sticky Header -->
    <header class="backdrop-blur-xl bg-white/70 dark:bg-slate-900/70 border-b border-slate-200 dark:border-slate-700 sticky top-0 z-50">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="flex items-center justify-between h-14">
          <!-- Logo / Identity -->
          <RouterLink to="/" class="flex items-center gap-2.5 group">
            <div class="w-7 h-7 rounded-lg bg-gradient-to-br from-violet-500 to-fuchsia-600 flex items-center justify-center shadow-md shadow-violet-500/30 group-hover:scale-105 transition-transform duration-200">
              <svg class="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
              </svg>
            </div>
            <div>
              <div class="text-sm font-semibold text-slate-900 dark:text-white tracking-tight">Run Explorer</div>
              <div class="text-xs text-slate-500 dark:text-slate-400 -mt-0.5">CAF Orchestration</div>
            </div>
          </RouterLink>

          <!-- Nav Links + Dark Mode Toggle -->
          <nav class="flex items-center gap-1">
            <RouterLink
              v-for="link in navLinks"
              :key="link.to"
              :to="link.to"
              :class="[
                'px-3 py-1.5 rounded-lg text-sm font-medium transition-all duration-200',
                isActive(link.to)
                  ? 'bg-violet-100 dark:bg-violet-900/30 text-violet-700 dark:text-violet-300'
                  : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-800'
              ]"
            >
              {{ link.label }}
            </RouterLink>

            <!-- Dark mode toggle -->
            <button
              @click="toggleDark"
              class="ml-1 p-1.5 rounded-lg text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-800 transition-all duration-200 focus-visible:ring-2 focus-visible:ring-violet-500 focus-visible:ring-offset-2"
              :aria-label="isDark ? 'Switch to light mode' : 'Switch to dark mode'"
            >
              <!-- Sun icon (shown in dark mode) -->
              <svg v-if="isDark" class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364-6.364l-.707.707M6.343 17.657l-.707.707M17.657 17.657l-.707-.707M6.343 6.343l-.707-.707M12 8a4 4 0 100 8 4 4 0 000-8z" />
              </svg>
              <!-- Moon icon (shown in light mode) -->
              <svg v-else class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12.79A9 9 0 1111.21 3a7 7 0 009.79 9.79z" />
              </svg>
            </button>
          </nav>
        </div>
      </div>
    </header>

    <!-- Main Content -->
    <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <RouterView />
    </main>
  </div>
</template>
