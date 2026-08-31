// src/router/index.ts
import { createRouter, createWebHistory } from 'vue-router'
import { ElNotification } from 'element-plus'
import { exchangeCodeForTokenAuthOidcTokenPost } from '@/sdk'
import { jwtDecode, type JwtPayload } from 'jwt-decode'

import { routes as siteRoutes } from 'openwrt-controller/src/router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login/:provider?',
      name: 'Login',
      component: () => import('@/views/LoginView.vue'),
    },
    {
      path: '/mfa',
      name: 'MFA',
      component: () => import('@/views/MFAView.vue'),
    },
    {
      path: '/setup-mfa',
      name: 'SetupMFA',
      component: () => import('@/views/MFASetupView.vue'),
    },
    {
      path: '/register',
      name: 'Register',
      component: () => import('@/views/RegistrationView.vue'),
    },
    {
      path: '/link-account',
      name: 'LinkAccount',
      component: () => import('@/views/LinkAccountView.vue'),
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
      children: siteRoutes,
    },
  ],
})

// Global route guard to check auth status before changing pages
router.beforeEach(async (to, from, next) => {
  if (to.query.code) {
    const auth_code = to.query.code.toString()

    if (!(to.name == 'LinkAccount')) {
      const auth_token = (
        await exchangeCodeForTokenAuthOidcTokenPost({
          body: { code: auth_code },
        })
      ).data?.access_token
      if (auth_token) localStorage.setItem('auth_token', auth_token)
      ElNotification.success({ title: 'Logged In', message: 'You have successfully logged in.' })

      return next({ path: to.path, query: {} })
    }
  }

  const token = localStorage.getItem('auth_token')

  interface Token extends JwtPayload {
    type: string
  }

  if (token) {
    const decodedToken: Token = jwtDecode(token)
    if (decodedToken.type.startsWith('limited:')) {
      const limitedScope = decodedToken.type.replace('limited:', '')
      if (limitedScope == 'setup_mfa' && !(to.name == 'SetupMFA'))
        next({ name: 'SetupMFA', query: { redirect: to.query.redirect } })
      if (limitedScope == 'mfa' && !(to.name == 'MFA'))
        next({ name: 'MFA', query: { redirect: to.query.redirect } })
    }
  }

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
