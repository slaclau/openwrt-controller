<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue'
import SvgIcon from '@jamescoyle/vue-icon'
import { useStatusStore } from '@controller/stores/status'
import { mdiArrowLeft } from '@mdi/js'
import { isMobile } from '@controller/utils'

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
  <div v-if="!isMobile || $route.name == 'Settings'">
    <el-card body-style="padding: 0 !important">
      <div v-for="tab in tabs" class="list-item" @click="$router.push(tab.route)">
        {{ tab.name }}
      </div>
    </el-card>
  </div>
  <div v-if="!isMobile || $route.name != 'Settings'">
    <el-button v-if="isMobile" @click="$router.push({ name: 'Settings' })">
      <svg-icon type="mdi" :path="mdiArrowLeft" :size="24" />
    </el-button>
    <router-view />
  </div>
</template>

<style scoped lang="css">
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
