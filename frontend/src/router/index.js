import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    name: 'Home',
    redirect: '/traffic',
  },
  {
    path: '/traffic',
    name: 'Traffic',
    component: () => import('../views/TrafficMonitor.vue'),
  },
  {
    path: '/firewall',
    name: 'Firewall',
    component: () => import('../views/FirewallConfig.vue'),
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router