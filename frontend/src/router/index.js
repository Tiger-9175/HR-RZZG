import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    name: 'home',
    component: () => import('@/views/Home.vue'),
  },
  {
    path: '/evaluate',
    name: 'evaluate',
    component: () => import('@/views/Evaluate.vue'),
  },
  {
    path: '/result/:id?',
    name: 'result',
    component: () => import('@/views/Result.vue'),
  },
  {
    path: '/settings',
    name: 'settings',
    component: () => import('@/views/Settings.vue'),
  },
  {
    path: '/demo',
    name: 'demo',
    component: () => import('@/views/Demo.vue'),
  },
  {
    path: '/history',
    name: 'history',
    component: () => import('@/views/History.vue'),
  },
  {
    path: '/batch',
    name: 'batch',
    component: () => import('@/views/Batch.vue'),
  },
  {
    path: '/compare',
    name: 'compare',
    component: () => import('@/views/Compare.vue'),
  },
  {
    path: '/prompts',
    name: 'prompts',
    component: () => import('@/views/Prompts.vue'),
  },
  {
    path: '/regression',
    name: 'regression',
    component: () => import('@/views/Regression.vue'),
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
