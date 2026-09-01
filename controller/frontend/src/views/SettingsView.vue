<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue'
import type { Status } from '@controller/sdk'
import NetworksView from '@controller/views/NetworksView.vue'
import WirelessView from '@controller/views/WirelessView.vue'

import { useStatusStore } from '@controller/stores/status'

const statusStore = useStatusStore()

const tabs = [
  { name: 'Networks', route: { name: 'Networks' } },
  { name: 'WiFi', route: { name: 'WiFi' } },
]

onMounted(() => {
  statusStore.startAutoRefresh(3000)
})

onUnmounted(() => {
  statusStore.stopAutoRefresh()
})
</script>

<template>
  <el-card v-if="$route.name == 'Settings'">
    <div v-for="tab in tabs" class="list-item" @click="$router.push(tab.route)">
      {{ tab.name }}
    </div>
  </el-card>
  <router-view v-else />
</template>

<style scoped lang="css">
:deep(.el-card__body) {
  padding: 0 !important;
}

.list-item {
  padding: 10px;
}
.list-item.active {
  color: var(--el-color-primary);
}

.list-item:hover {
  color: var(--el-color-primary);
}

.list-item:not(:last-child) {
  border-bottom: var(--el-border);
}
</style>
