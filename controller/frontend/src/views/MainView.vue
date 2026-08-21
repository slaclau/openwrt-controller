<script setup lang="ts">
import { getStatusStatusGet, type Status } from '@controller/sdk'
import { client } from '@controller/sdk/client.gen.ts'
console.log('MV', client.getConfig())
import OverviewView from './OverviewView.vue'
import DevicesView from './DevicesView.vue'
import SettingsView from './SettingsView.vue'
import DPIView from './DPIView.vue'
import SvgIcon from '@jamescoyle/vue-icon'
import {
  mdiMonitorDashboard,
  mdiServerOutline,
  mdiMonitorCellphone,
  mdiCog,
  mdiChartLine,
} from '@mdi/js'
import { setIntervalImmediate } from '@controller/utils'
import { onMounted, onUnmounted, ref, type Ref } from 'vue'

const status: Ref<Status> = ref({})
let timer: number

onMounted(() => {
  timer = setIntervalImmediate(() => {
    getStatusStatusGet().then((res) => {
      if (res.data) {
        status.value = res.data
      }
    })
  }, 3000)
})

onUnmounted(() => {
  clearInterval(timer)
})
</script>

<template>
  <el-main>
    <el-tabs :stretch="true">
      <el-tab-pane name="overview">
        <template #label>
          <svg-icon type="mdi" :path="mdiMonitorDashboard" :size="24" />
        </template>
        <OverviewView />
      </el-tab-pane>
      <el-tab-pane name="devices">
        <template #label>
          <svg-icon type="mdi" :path="mdiServerOutline" :size="24" />
        </template>
        <DevicesView :devices="status.device_status" />
      </el-tab-pane>
      <el-tab-pane name="clients">
        <template #label>
          <svg-icon type="mdi" :path="mdiMonitorCellphone" :size="24" />
        </template>
      </el-tab-pane>
      <el-tab-pane label="DPI" name="dpi">
        <template #label>
          <svg-icon type="mdi" :path="mdiChartLine" :size="24" />
        </template>
        <DPIView />
      </el-tab-pane>
      <el-tab-pane name="settings">
        <template #label> <svg-icon type="mdi" :path="mdiCog" :size="24" /> </template>
        <SettingsView :status="status" />
      </el-tab-pane>
    </el-tabs>
  </el-main>
</template>
