import { createRouter, createWebHistory } from 'vue-router'
import RunListView from '@/views/RunListView.vue'
import RunDetailView from '@/views/RunDetailView.vue'
import ComparisonView from '@/views/ComparisonView.vue'
import HealthView from '@/views/HealthView.vue'
import LiveView from '@/views/LiveView.vue'
import SessionListView from '@/views/SessionListView.vue'
import SessionDetailView from '@/views/SessionDetailView.vue'

const routes = [
  { path: '/', component: RunListView },
  { path: '/runs/:id', component: RunDetailView, props: true },
  { path: '/compare', component: ComparisonView },
  { path: '/health', component: HealthView },
  { path: '/live', component: LiveView },
  { path: '/sessions', component: SessionListView },
  { path: '/sessions/:id', component: SessionDetailView, props: true },
]

export const router = createRouter({
  history: createWebHistory(),
  routes,
})
