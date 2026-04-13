<script setup lang="ts">
defineProps<{
  title: string
  description: string
  ctaLabel?: string
  icon?: 'inbox' | 'search' | 'compare'
}>()

defineEmits<{
  cta: []
}>()
</script>

<template>
  <div class="flex flex-col items-center justify-center py-20 px-6 text-center">
    <!-- Icon container -->
    <div class="w-16 h-16 rounded-2xl bg-slate-100 dark:bg-slate-700/50 flex items-center justify-center mb-4">
      <!-- Inbox icon (default) -->
      <svg v-if="!icon || icon === 'inbox'" class="w-8 h-8 text-slate-400 dark:text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M2.25 13.5h3.86a2.25 2.25 0 012.012 1.244l.256.512a2.25 2.25 0 002.013 1.244h3.218a2.25 2.25 0 002.013-1.244l.256-.512a2.25 2.25 0 012.013-1.244h3.859m-19.5.338V18a2.25 2.25 0 002.25 2.25h15A2.25 2.25 0 0021.75 18v-4.162c0-.224-.034-.447-.1-.661L19.24 5.338a2.25 2.25 0 00-2.15-1.588H6.911a2.25 2.25 0 00-2.15 1.588L2.35 13.177a2.25 2.25 0 00-.1.661z" />
      </svg>
      <!-- Search icon -->
      <svg v-else-if="icon === 'search'" class="w-8 h-8 text-slate-400 dark:text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 15.803 7.5 7.5 0 0015.803 15.803z" />
      </svg>
      <!-- Compare / table-cells icon -->
      <svg v-else-if="icon === 'compare'" class="w-8 h-8 text-slate-400 dark:text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M3.375 19.5h17.25m-17.25 0a1.125 1.125 0 01-1.125-1.125M3.375 19.5h7.5c.621 0 1.125-.504 1.125-1.125m-9.75 0V5.625m0 12.75v-1.5c0-.621.504-1.125 1.125-1.125m18.375 2.625V5.625m0 12.75c0 .621-.504 1.125-1.125 1.125m1.125-1.125v-1.5c0-.621-.504-1.125-1.125-1.125m0 3.75h-7.5A1.125 1.125 0 0112 18.375m9.75-12.75c0-.621-.504-1.125-1.125-1.125H3.375c-.621 0-1.125.504-1.125 1.125m19.5 0v1.5c0 .621-.504 1.125-1.125 1.125M2.25 5.625v1.5c0 .621.504 1.125 1.125 1.125m0 0h17.25m-17.25 0h7.5c.621 0 1.125.504 1.125 1.125M3.375 8.25c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125m17.25-3.75h-7.5c-.621 0-1.125.504-1.125 1.125m8.625-1.125c.621 0 1.125.504 1.125 1.125v1.5c0 .621-.504 1.125-1.125 1.125m-17.25 0h7.5m-7.5 0c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125M12 10.875v-1.5m0 1.5c0 .621-.504 1.125-1.125 1.125M12 10.875c0 .621.504 1.125 1.125 1.125m-2.25 0c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125m2.25-2.25h.008v.008H12v-.008zm0 2.625h.008v.008H12v-.008zm0-5.25h.008v.008H12V8.25z" />
      </svg>
    </div>

    <h3 class="text-base font-semibold text-slate-700 dark:text-slate-300 mb-1">{{ title }}</h3>
    <p class="text-sm text-slate-500 dark:text-slate-400 max-w-xs mb-6">{{ description }}</p>

    <button
      v-if="ctaLabel"
      class="px-4 py-2 rounded-xl bg-violet-600 hover:bg-violet-700 text-white text-sm font-medium transition-colors duration-200 shadow-md shadow-violet-500/20 focus-visible:ring-2 focus-visible:ring-violet-500 focus-visible:ring-offset-2"
      @click="$emit('cta')"
    >
      {{ ctaLabel }}
    </button>
  </div>
</template>
