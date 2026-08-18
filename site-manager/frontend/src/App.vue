<script setup lang="ts">
import { mdiAccount, mdiArrowLeft, mdiThemeLightDark } from '@mdi/js'
import { useDark, useToggle } from '@vueuse/core'

import SvgIcon from '@jamescoyle/vue-icon'
import router from './router'

const isDark = useDark()
const toggleDark = useToggle(isDark)

import { useRoute } from 'vue-router'
import { logoutAuthLogoutPost } from './sdk'
import { site_manager_client } from './client'
import { ElNotification } from 'element-plus'
import { onMounted, ref, type Ref } from 'vue'
import UserDrawerComponent from './components/UserDrawerComponent.vue'
import { logout } from './utils.ts'

const route = useRoute()

const openUserDrawer = ref(false)
let drawerWidth: Ref<string>

const toggleShowUserDrawer = () => {
  openUserDrawer.value = !openUserDrawer.value
}

onMounted(() => {
  drawerWidth = ref(window.screen.width < 500 ? '100%' : '30%')
})
</script>

<template>
  <el-container>
    <el-header>
      <h1>
        <span style="float: left"><el-button :disabled="['/', '/login'].includes(route.path)" @click="router.back()">
            <svg-icon type="mdi" :path="mdiArrowLeft" :size="24" />
          </el-button>
        </span>
        <el-button class="header-title" text disabled><img src="/openwrt.svg" height="24" /></el-button>
        <span class="header-title hidden-sm-and-down">Site Manager</span>
        <span style="float: right">
          <el-button @click="toggleDark()">
            <svg-icon type="mdi" :path="mdiThemeLightDark" :size="24" />
          </el-button>
          <el-button @click="toggleShowUserDrawer" :disabled="!route.meta.requiresAuth">
            <svg-icon type="mdi" :path="mdiAccount" :size="24" />
          </el-button>
          <el-button @click="logout" :disabled="!route.meta.requiresAuth">
            Logout
          </el-button>
        </span>
      </h1>
    </el-header>
    <el-main>
      <router-view />
    </el-main>
  </el-container>
  <UserDrawerComponent v-model="openUserDrawer" :size="drawerWidth">
    <UserDrawerComponent />
  </UserDrawerComponent>
</template>

<style scoped>
.header-title {
  margin-left: 16px;
  /* Creates the gap between left button and title */
}
</style>
