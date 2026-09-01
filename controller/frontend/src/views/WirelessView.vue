<script setup lang="ts">
import {
  getAllWirelessNetworksConfigurationWirelessGet,
  type Wireless,
  type Status,
} from '@controller/sdk'
import { ref, type Ref } from 'vue'

import WirelessDrawerComponent from '@controller/components/settings/wireless/WirelessDrawerComponent.vue'
import { isMobile } from '@controller/utils'
import { useStatusStore } from '@controller/stores/status'

const statusStore = useStatusStore()

const networks: Ref<Array<Wireless> | undefined> = ref([])
getAllWirelessNetworksConfigurationWirelessGet().then((res) => {
  networks.value = res.data
})

const selectedNetwork: Ref<Wireless | null> = ref(null)
const openDrawer = ref(false)
const drawerWidth = ref(window.screen.width < 500 ? '100%' : '30%')

const closeDrawer = () => {
  openDrawer.value = false
}

function selectNetwork(row: Wireless) {
  selectedNetwork.value = row
  openDrawer.value = true
}
function addNetwork() {
  selectedNetwork.value = null
  openDrawer.value = true
}
</script>

<template>
  <div v-if="!isMobile">
    <el-table
      v-if="statusStore.status"
      :data="networks"
      table-layout="auto"
      @row-click="selectNetwork"
    >
      <el-table-column prop="ssid" label="SSID" />
      <el-table-column prop="network_id" label="Network" />
    </el-table>
    <el-button type="primary" @click="addNetwork">Add Network</el-button>
  </div>
  <div v-else>
    <el-card body-style="padding: 0 !important">
      <div v-for="wifi in networks" class="list-item" @click="selectNetwork(wifi)">
        <span style="float: left">
          {{ wifi.ssid }}
        </span>
        <span style="float: right">
          {{ wifi.network_id }}
        </span>
      </div>
    </el-card>
  </div>
  <el-drawer v-model="openDrawer" :size="drawerWidth" :withHeader="false">
    <WirelessDrawerComponent :network="selectedNetwork" @cancel="closeDrawer" />
  </el-drawer>
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
