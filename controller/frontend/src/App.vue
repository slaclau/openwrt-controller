<script setup lang="ts">
import SvgIcon from '@jamescoyle/vue-icon'
import { mdiThemeLightDark } from '@mdi/js'

import { useDark, useToggle } from '@vueuse/core'
import MainView from './views/MainView.vue'

const isDark = useDark()
const toggleDark = useToggle(isDark)
</script>

<template>
  <el-container style="height: 100%">
    <el-header>
      <h1>
        {{ $route.name }}
        <span style="float: right"
          ><el-button @click="toggleDark()"
            ><svg-icon type="mdi" :path="mdiThemeLightDark" :size="24" /></el-button
        ></span>
      </h1>
    </el-header>
    <MainView />
  </el-container>
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
