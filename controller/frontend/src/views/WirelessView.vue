<script setup lang="ts">
import {
  getAllWirelessNetworksConfigurationWirelessGet,
  type Wireless,
  type Status,
} from '@controller/sdk'
import { ref, type Ref } from 'vue'

import WirelessDrawerComponent from '@controller/components/settings/wireless/WirelessDrawerComponent.vue'

import { useStatusStore } from '@controller/stores/status'

const statusStore = useStatusStore()

const networks: Ref<Array<Wireless> | undefined> = ref([])
getAllWirelessNetworksConfigurationWirelessGet().then((res) => {
  networks.value = res.data
})

const selectedNetwork: Ref<Wireless | null> = ref(null)
const openDrawer = ref(false)
const drawerWidth = ref(window.screen.width < 500 ? '100%' : '30%')

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
  <el-drawer v-model="openDrawer" :size="drawerWidth">
    <WirelessDrawerComponent :network="selectedNetwork" />
  </el-drawer>
</template>
