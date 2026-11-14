import { createMemoryHistory, createRouter, createWebHistory } from 'vue-router'
import LandingView from '@/views/LandingView.vue'

const router = createRouter({
  history:
    typeof window !== 'undefined'
      ? createWebHistory(import.meta.env.BASE_URL)
      : createMemoryHistory(),
  routes: [
    { path: '/', name: 'landing', component: LandingView },
    {
      path: '/dashboard',
      name: 'dashboard',
      component: () => import('@/views/ExplorerView.vue'),
    },
  ],
  scrollBehavior(to) {
    if (to.hash) return { el: to.hash, behavior: 'smooth' }
    return { top: 0 }
  },
})

export default router
