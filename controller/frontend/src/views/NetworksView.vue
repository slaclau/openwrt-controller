<script setup lang="ts">
import {
  getAllNetworksConfigurationNetworksGet,
  type NetworkStatus,
  type NetworkWithDevices,
  type Status,
} from '@controller/sdk'
import { isMobile } from '@controller/utils'
import { ref, type Ref } from 'vue'

import NetworkDrawerComponent from '@controller/components/settings/networks/NetworkDrawerComponent.vue'

import { useStatusStore } from '@controller/stores/status'

const statusStore = useStatusStore()

const networks: Ref<Array<NetworkWithDevices> | undefined> = ref([])
getAllNetworksConfigurationNetworksGet().then((res) => {
  networks.value = res.data
})

const selectedNetwork: Ref<NetworkWithDevices | null> = ref(null)
const openDrawer = ref(false)
const drawerWidth = ref(window.screen.width < 500 ? '100%' : '30%')

const closeDrawer = () => {
  openDrawer.value = false
}

function selectNetwork(row: NetworkStatus) {
  selectedNetwork.value = row.network
  openDrawer.value = true
}
function addNetwork() {
  selectedNetwork.value = null
  openDrawer.value = true
}
// function getIPLeases(network_id: string, dhcp_server_id: string) {
//   return props.status?.network_status?.filter(
//     (network) => network.network.dhcp_server_id == dhcp_server_id,
//   )[0].dhcp_leases
// }
</script>

<template>
  <div v-if="!isMobile">
    <el-table
      v-if="statusStore.status"
      :data="statusStore.status.network_status"
      table-layout="auto"
      @row-click="selectNetwork"
    >
      <el-table-column prop="network.name" label="Name" />
      <el-table-column prop="network.vlan_id" label="VLAN ID" />
      <el-table-column prop="network.router.hostname" label="Router" />
      <el-table-column prop="network.network_address" label="Subnet" />
      <el-table-column prop="network.dhcp_server.hostname" label="DHCP" />
      <el-table-column label="IP Leases">
        <template #default="scope">
          {{ scope.row.dhcp_leases.length }}
        </template>
      </el-table-column>
      <el-table-column prop="network.dhcp_pool_size" label="Pool Size" />
      <el-table-column label="Available">
        <template #default="scope">
          {{ scope.row.network.dhcp_pool_size - scope.row.dhcp_leases.length }}
        </template>
      </el-table-column>
      <el-table-column label="Range">
        <template #default="scope">
          {{ scope.row.network.dhcp_start_ip }} - {{ scope.row.network.dhcp_end_ip }}
        </template>
      </el-table-column>
    </el-table>
    <el-button type="primary" @click="addNetwork">Add Network</el-button>
  </div>
  <div v-else>
    <el-card v-if="statusStore.status" body-style="padding: 0 !important">
      <div
        v-for="network in statusStore.status.network_status"
        class="list-item"
        @click="selectNetwork(network)"
      >
        <span style="float: left">
          {{ network.network.name }}
          <br />
          <small>
            {{ network.network.router.hostname }}
          </small>
        </span>
        <span style="float: right">
          {{ network.network.network_address }}
          <br />
          <small> VLAN ID: {{ network.network.vlan_id }} </small>
        </span>
      </div>
    </el-card>
  </div>
  <el-drawer v-model="openDrawer" :size="drawerWidth" :with-header="false">
    <NetworkDrawerComponent :network="selectedNetwork" @cancel="closeDrawer" />
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
