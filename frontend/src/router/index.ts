import { createRouter, createWebHistory, RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue'),
    meta: { requiresAuth: false }
  },
  {
    path: '/',
    component: () => import('@/layout/MainLayout.vue'),
    meta: { requiresAuth: true },
    children: [
      {
        path: '',
        name: 'Home',
        component: () => import('@/views/Home.vue')
      },
      {
        path: 'finscan',
        name: 'Finscan',
        component: () => import('@/views/Finscan.vue')
      },
      {
        path: 'announcements',
        name: 'AnnouncementCenter',
        component: () => import('@/views/Announcement.vue')
      },
      {
        path: 'compare',
        name: 'Compare',
        component: () => import('@/views/Compare.vue')
      },
      {
        path: 'analysis',
        name: 'AnalysisHome',
        component: () => import('@/views/AnalysisHome.vue')
      },
      {
        path: 'stock/:code',
        name: 'StockDetail',
        component: () => import('@/views/StockDetail.vue'),
        redirect: to => `/stock/${to.params.code}/main-indicators`,
        children: [
          {
            path: 'main-indicators',
            name: 'MainIndicators',
            component: () => import('@/views/finance/MainIndicators.vue')
          },
          {
            path: 'profile',
            name: 'CompanyProfile',
            component: () => import('@/views/finance/CompanyProfile.vue')
          },
          {
            path: 'dupont-analysis',
            name: 'DupontAnalysis',
            component: () => import('@/views/finance/DupontAnalysis.vue')
          },
          {
            path: 'balance-sheet',
            name: 'BalanceSheet',
            component: () => import('@/views/finance/BalanceSheet.vue')
          },
          {
            path: 'income-statement',
            name: 'IncomeStatement',
            component: () => import('@/views/finance/IncomeStatement.vue')
          },
          {
            path: 'cash-flow',
            name: 'CashFlow',
            component: () => import('@/views/finance/CashFlow.vue')
          },
          {
            path: 'announcements',
            name: 'Announcements',
            component: () => import('@/views/finance/Announcements.vue')
          },
        ]
      },
    ]
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: () => import('@/views/NotFound.vue')
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to, _from, next) => {
  const authStore = useAuthStore()
  const isCapacitor = (window as any).Capacitor !== undefined
  
  // 手机版（Capacitor）本地模式：免登录，直接进入
  if (isCapacitor) {
    next()
    return
  }
  
  // 网页版保留登录逻辑
  const requiresAuth = to.matched.some(record => record.meta.requiresAuth !== false)
  if (requiresAuth && !authStore.token) {
    next('/login')
  } else if (to.path === '/login' && authStore.token) {
    next('/')
  } else {
    next()
  }
})

export default router
