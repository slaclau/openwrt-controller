<script setup lang="ts">
import SvgIcon from '@jamescoyle/vue-icon'
import { mdiThemeLightDark } from '@mdi/js'

import { useDark, useToggle } from '@vueuse/core'
import MainView from './views/MainView.vue'

const isDark = useDark()
const toggleDark = useToggle(isDark)
</script>

<template>
  <el-container>
    <el-header>
      <h1>
        OpenWrt Controller
        <span style="float: right"><el-button @click="toggleDark()"><svg-icon type="mdi" :path="mdiThemeLightDark"
              :size="24" /></el-button></span>
      </h1>
    </el-header>
    <el-main>
      <MainView />
    </el-main>
  </el-container>
</template>
