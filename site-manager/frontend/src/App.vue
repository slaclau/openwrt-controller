<script setup lang="ts">
import { mdiArrowLeft, mdiThemeLightDark } from '@mdi/js'
import { useDark, useToggle } from '@vueuse/core'

import SvgIcon from '@jamescoyle/vue-icon'
import router from './router'

const isDark = useDark()
const toggleDark = useToggle(isDark)

import { useRoute } from 'vue-router'
import { logoutAuthLogoutPost } from './sdk'
import { site_manager_client } from './client'
import { ElNotification } from 'element-plus'

const route = useRoute()

const logout = async () => {
  const logoutUrl = await (
    await logoutAuthLogoutPost({ client: site_manager_client })
  ).data?.location
  localStorage.removeItem('auth_token')
  console.log('logged out')
  ElNotification.success({
    title: 'Logged Out',
    message: 'You have been successfully logged out.',
  })
  if (logoutUrl) {
    window.location.href = logoutUrl
  } else {
    router.push({
      name: 'Login',
      query: { redirect: '/' },
    })
  }
}
</script>

<template>
  <el-container>
    <el-header>
      <h1>
        <span style="float: left"><el-button
            :style="`visibility: ${['/', '/login'].includes(route.path) ? 'hidden' : 'visible'}`"
            @click="router.back()">
            <svg-icon type="mdi" :path="mdiArrowLeft" :size="24" />
          </el-button>
        </span>
        <span class="header-title">Site Manager</span>
        <span style="float: right">
          <el-button @click="toggleDark()">
            <svg-icon type="mdi" :path="mdiThemeLightDark" :size="24" />
          </el-button>
          <el-button @click="logout"
            :style="`visibility: ${['/link-account', '/login'].includes(route.path) ? 'hidden' : 'visible'}`">
            Logout
          </el-button>
        </span>
      </h1>
    </el-header>
    <el-main>
      <router-view />
    </el-main>
  </el-container>
</template>

<style scoped>
.header-title {
  margin-left: 16px;
  /* Creates the gap between left button and title */
}
</style>
