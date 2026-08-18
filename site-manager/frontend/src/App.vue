<script setup lang="ts">
import { mdiAccount, mdiArrowLeft, mdiBrightness7, mdiThemeLightDark, mdiWeatherNight } from '@mdi/js'
import { useColorMode } from '@vueuse/core'

import SvgIcon from '@jamescoyle/vue-icon'
import router from './router'

const colorMode = useColorMode()
const toggleDark = () => {
  switch (colorMode.store.value) {
    case "dark":
      colorMode.value = "light"
      break
    case "light":
      colorMode.value = "auto"
      break
    case "auto":
      colorMode.value = "dark"
      break
  }
}

const getColorModeIcon = () => {
  switch (colorMode.store.value) {
    case "dark":
      return mdiWeatherNight
    case "light":
      return mdiBrightness7
    case "auto":
      return mdiThemeLightDark
  }
}

import { useRoute } from 'vue-router'
import { onMounted, ref, type Ref } from 'vue'
import UserDrawerComponent from './components/UserDrawerComponent.vue'

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
          <el-button @click="toggleDark">
            <svg-icon type="mdi" :path="getColorModeIcon()" :size="24" />
          </el-button>
          <el-button @click="toggleShowUserDrawer" :disabled="!route.meta.requiresAuth">
            <svg-icon type="mdi" :path="mdiAccount" :size="24" />
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
