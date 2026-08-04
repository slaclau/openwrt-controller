// src/router/index.ts
import { createRouter, createWebHistory } from 'vue-router'
import { ElNotification } from 'element-plus'
import { exchangeCodeForTokenAuthTokenPost } from '@/sdk'
import { site_manager_client } from '@/client'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'Login',
      component: () => import('@/views/LoginView.vue'),
      alias: ['/login/:provider'],
    },
    {
      path: '/link-account',
      name: 'LinkAccount',
      component: () => import('@/views/LinkAccountView.vue')
    },
    {
      path: '/',
      name: 'Dashboard',
      component: () => import('@/views/DashboardView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/sites/:site_id',
      name: 'Site',
      component: () => import('@/views/SiteView.vue'),
      meta: { requiresAuth: true },
    },
  ],
})

// Global route guard to check auth status before changing pages
router.beforeEach(async (to, from, next) => {
  if (to.query.code) {
    const auth_code = to.query.code.toString()

    if (!(to.name == "LinkAccount")) {
      const auth_token = (
        await exchangeCodeForTokenAuthTokenPost({
          client: site_manager_client,
          body: { code: auth_code },
        })
      ).data?.access_token
      if (auth_token) localStorage.setItem('auth_token', auth_token)
      ElNotification.success({ title: 'Logged In', message: 'You have successfully logged in.' })

      return next({ path: to.path, query: {} })
    }
  }

  const token = localStorage.getItem('auth_token')

  if (to.meta.requiresAuth && !token) {
    ElNotification.error({
      title: 'Access Denied',
      message: 'Please log in to access this page.',
    })
    next({ name: 'Login', query: { redirect: to.fullPath } })
  } else {
    next()
  }
})

export default router
