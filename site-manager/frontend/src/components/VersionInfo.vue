<script setup lang="ts">
import { useToggle } from '@vueuse/core'

import versionData from '../version.json'
import { info as sdkInfo } from '../sdk/source.json' with { type: 'json' }
import { info as controllerSdkInfo } from 'openwrt-controller/src/sdk/source.json' with { type: 'json' }
import { ElDialog } from 'element-plus'
import { ref } from 'vue'

const versionInfoVisible = ref(false)
const showVersionInfo = useToggle(versionInfoVisible)
</script>

<template>
  <div class="hidden-sm-and-down">
    Frontend Version: {{ versionData.frontend_version }}
    <el-divider direction="vertical" />
    Controller Frontend Version: {{ versionData.controller_frontend_version }}
    <el-divider direction="vertical" />
    Sdk Version: {{ sdkInfo.version }}
    <el-divider direction="vertical" />
    Controller Sdk Version: {{ controllerSdkInfo.version }}
  </div>
  <div class="visible-sm-and-down">
    <el-button link @click="showVersionInfo"> Version Info </el-button>
  </div>

  <el-dialog v-model="versionInfoVisible" width="80%">
    <template #header> Version Info </template>
    <div>Frontend Version: {{ versionData.frontend_version }}</div>
    <div>Controller Frontend Version: {{ versionData.controller_frontend_version }}</div>
    <div>Sdk Version: {{ sdkInfo.version }}</div>
    <div>Controller Sdk Version: {{ controllerSdkInfo.version }}</div>
  </el-dialog>
</template>
