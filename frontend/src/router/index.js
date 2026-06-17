import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/', redirect: '/planner' },
  { path: '/planner', name: 'planner', component: () => import('@/views/PlannerView.vue') },
  { path: '/transport', name: 'transport', component: () => import('@/views/TransportView.vue') },
  { path: '/archive', name: 'archive', component: () => import('@/views/ArchiveView.vue') },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
