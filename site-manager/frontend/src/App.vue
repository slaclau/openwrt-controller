<script setup lang="ts">
import {
  mdiAccount,
  mdiArrowLeft,
  mdiBrightness7,
  mdiThemeLightDark,
  mdiWeatherNight,
} from '@mdi/js'
import { useColorMode } from '@vueuse/core'

import SvgIcon from '@jamescoyle/vue-icon'

import ReloadPrompt from './components/ReloadPrompt.vue'

import router from './router'

const colorMode = useColorMode()
const toggleDark = () => {
  switch (colorMode.store.value) {
    case 'dark':
      colorMode.value = 'light'
      break
    case 'light':
      colorMode.value = 'auto'
      break
    case 'auto':
      colorMode.value = 'dark'
      break
  }
}

const getColorModeIcon = () => {
  switch (colorMode.store.value) {
    case 'dark':
      return mdiWeatherNight
    case 'light':
      return mdiBrightness7
    case 'auto':
      return mdiThemeLightDark
  }
}

import { useRoute } from 'vue-router'
import { onMounted, ref, type Ref } from 'vue'
import UserDrawerComponent from './components/UserDrawerComponent.vue'
import VersionInfo from './components/VersionInfo.vue'

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
  <el-container style="height: 100%">
    <el-header class="fixed-header">
      <h1>
        <span style="float: left"
          ><el-button
            :disabled="['/', '/login', '/mfa', '/setup-mfa'].includes(route.path)"
            @click="router.back()"
          >
            <svg-icon type="mdi" :path="mdiArrowLeft" :size="24" />
          </el-button>
        </span>
        <el-button class="header-title" text disabled
          ><img src="/openwrt.svg" height="24"
        /></el-button>
        <span class="header-title hidden-sm-and-down">Site Manager</span>
        <span style="float: right">
          <el-button @click="toggleDark">
            <svg-icon type="mdi" :path="getColorModeIcon()" :size="24" />
          </el-button>
          <el-button @click="toggleShowUserDrawer" :disabled="!route.meta.requiresAuth">
            <svg-icon type="mdi" :path="mdiAccount" :size="24" />
          </el-button>
        </span>
      </h1>
    </el-header>
    <el-main style="flex-grow: 1">
      <router-view />
    </el-main>
    <el-footer class="fixed-footer">
      <VersionInfo />
    </el-footer>
  </el-container>
  <UserDrawerComponent v-model="openUserDrawer" :size="drawerWidth" />
  <ReloadPrompt />
</template>

<style>
html,
body {
  overscroll-behavior: none;
  margin: 0;
  height: 100%;
}

#app {
  height: 100%;
}
</style>

<style scoped>
.header-title {
  margin-left: 16px;
  /* Creates the gap between left button and title */
}

.fixed-header {
  position: sticky;
  top: 0;
  left: 0;
  width: 100%;
  height: auto !important;

  /* Match el-card colors and backgrounds */
  background-color: var(--el-bg-color-overlay);

  /* Top border only (matches el-card border style) */
  border-bottom: 1px solid var(--el-border-color-light);
  border-top: none;
  border-left: none;
  border-right: none;

  /* Replicates el-card shadow (directed downwards, adjusted upwards) */
  box-shadow: 0 4px 12px 0 rgba(0, 0, 0, 0.05);
}

.fixed-footer {
  position: sticky;
  bottom: 0;
  left: 0;
  width: 100%;
  /* Match el-card colors and backgrounds */
  background-color: var(--el-bg-color-overlay);

  /* Top border only (matches el-card border style) */
  border-top: 1px solid var(--el-border-color-light);
  border-bottom: none;
  border-left: none;
  border-right: none;

  /* Replicates el-card shadow (directed downwards, adjusted upwards) */
  box-shadow: 0 -4px 12px 0 rgba(0, 0, 0, 0.05);

  /* Layout alignment */
  display: flex;
  align-items: center;
  padding: 0 var(--el-card-padding, 20px);

  font-size: small;
}
</style>
