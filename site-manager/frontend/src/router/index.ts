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
            alias: ['/login/:provider']
        },
        {
            path: '/',
            name: 'Dashboard',
            component: () => import('@/views/DashboardView.vue'),
            meta: { requiresAuth: true }
        },
        {
            path: '/sites/:site_id',
            name: 'Site',
            component: () => import('@/views/SiteView.vue'),
            meta: { requiresAuth: true }
        }
    ]
})

// Global route guard to check auth status before changing pages
router.beforeEach(async (to, from, next) => {
    if (to.query.code) {
        // 2. Extract the JWT value from the hash
        const auth_code = to.query.code.toString()

        const auth_token = (await exchangeCodeForTokenAuthTokenPost({ client: site_manager_client, body: { code: auth_code } })).data?.access_token
        if (auth_token)
            localStorage.setItem("auth_token", auth_token)

        return next({ path: to.path, query: {} })
    }

    const token = localStorage.getItem('auth_token') // Or use a Pinia store

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
