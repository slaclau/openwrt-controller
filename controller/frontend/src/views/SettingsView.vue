<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue'
import type { Status } from '@controller/sdk'
import NetworksView from '@controller/views/NetworksView.vue'
import WirelessView from '@controller/views/WirelessView.vue'

import { useStatusStore } from '@controller/stores/status'

const statusStore = useStatusStore()

onMounted(() => {
  statusStore.startAutoRefresh(3000)
})

onUnmounted(() => {
  statusStore.stopAutoRefresh()
})
</script>

<template>
  <el-tabs tab-position="left" :stretch="true">
    <el-tab-pane label="Networks" name="networks">
      <NetworksView :status="statusStore.status" />
    </el-tab-pane>
    <el-tab-pane label="WiFi" name="wireless">
      <WirelessView :status="statusStore.status" />
    </el-tab-pane>
  </el-tabs>
</template>
