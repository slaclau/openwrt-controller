<script setup lang="ts">
import { adoptControlAdoptDeviceIdPost, type DeviceStatusWithDevice } from '@controller/sdk'
import DeviceDetails from '@controller/components/devices/overview/DeviceDetails.vue'
import DeviceSummary from '@controller/components/devices/overview/DeviceSummary.vue'

const props = defineProps<{
  device: DeviceStatusWithDevice | undefined
}>()

function adopt() {
  if (props.device) {
    adoptControlAdoptDeviceIdPost({ path: { device_id: props.device.device_id } }).then(() => {
      console.log(`adopted ${props.device?.device_id}`)
    })
  }
}

const origin = window.location.origin
</script>

<template>
  <DeviceSummary :device="device" />
  <DeviceDetails :device="device" />
  <el-button
    ><a download :href="`${origin}/api/configuration/raw/${device?.device_id}`"
      >Download Configuration</a
    ></el-button
  >
  <el-button v-if="!device?.device.adopted" @click="adopt">Adopt</el-button>
</template>
