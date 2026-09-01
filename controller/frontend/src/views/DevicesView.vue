<script setup lang="ts">
import { onMounted, onUnmounted, ref, type Ref } from 'vue'

import DeviceComponent from '@controller/components/devices/DeviceDrawerComponent.vue'
import type { DeviceStatusWithDevice } from '@controller/sdk'
import DeviceIcon from '@controller/components/devices/DeviceIcon.vue'
import { formatTime, isMobile } from '@controller/utils'
import { useStatusStore } from '@controller/stores/status'

const selectedDevice: Ref<DeviceStatusWithDevice | undefined> = ref(undefined)
const openDrawer = ref(false)
let drawerWidth: Ref<string>

const statusStore = useStatusStore()

onMounted(() => {
  drawerWidth = ref(window.screen.width < 500 ? '100%' : '30%')
  statusStore.startAutoRefresh(3000)
})

onUnmounted(() => {
  statusStore.stopAutoRefresh()
})

function selectDevice(row: DeviceStatusWithDevice) {
  selectedDevice.value = row
  openDrawer.value = true
}
</script>

<template>
  <div v-if="!isMobile">
    <el-table
      :data="statusStore.status?.device_status"
      style="width: 100%"
      table-layout="auto"
      @row-click="selectDevice"
    >
      <el-table-column width="100">
        <template #default="scope">
          <DeviceIcon :device="scope.row.device" />
        </template>
      </el-table-column>
      <el-table-column prop="device.hostname" label="Hostname" />
      <el-table-column prop="last_ip" label="IP Address" />
      <el-table-column>
        <template #default="scope">
          {{
            scope.row.device.adopted
              ? scope.row.up
                ? '✔ for ' + formatTime(scope.row.uptime)
                : scope.row.time_since_inform
                  ? '✗ for ' + formatTime(scope.row.time_since_inform)
                  : '✗'
              : 'Awaiting adoption'
          }}
        </template>
      </el-table-column>
    </el-table>
  </div>
  <div v-else>
    <el-card body-style="padding: 0 !important">
      <div
        v-for="device in statusStore.status?.device_status"
        class="list-item"
        @click="selectDevice(device)"
      >
        <span style="width: 50%">
          <DeviceIcon :device="device.device" />
          {{ device.device.hostname }}
          <br />
          <small> {{ device.device.model }} </small>
        </span>
        <span>
          {{ device.last_ip }}
          <br />
          <small>
            {{
              device.device.adopted
                ? device.up
                  ? '✔ for ' + formatTime(device.uptime)
                  : device.time_since_inform
                    ? '✗ for ' + formatTime(device.time_since_inform)
                    : '✗'
                : 'Awaiting adoption'
            }}
          </small>
        </span>
      </div>
    </el-card>
  </div>
  <el-drawer v-model="openDrawer" :size="drawerWidth">
    <DeviceComponent :device="selectedDevice" />
  </el-drawer>
</template>

<style scoped lang="css">
.list-item {
  padding: 10px;
  display: flex;
  justify-content: space-between;
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
