<script setup lang="ts">
import SiteTile from '@/components/SiteTile.vue'
import { getAllMySitesSitesGet, type SiteWithOutages } from '@/sdk'
import router from '@/router'
import { onMounted, onUnmounted, ref, type Ref } from 'vue'

const sites: Ref<SiteWithOutages[]> = ref([])

let timer: number

/* eslint-disable @typescript-eslint/no-unsafe-function-type */
function setIntervalImmediate(func: Function, interval: number): number {
  func()
  return setInterval(func, interval)
}

onMounted(() => {
  timer = setIntervalImmediate(() => {
    getAllMySitesSitesGet().then((res) => {
      if (res.data) sites.value = res.data
    })
  }, 3000)
})

onUnmounted(() => {
  clearInterval(timer)
})
</script>

<template>
  <div v-for="site in sites" :key="site.site_id">
    <el-row>
      <el-col :xs="24" :sm="12" :md="6" :lg="4" :xl="3">
        <SiteTile
          :site="site"
          @click="
            () => {
              if (site.up) router.push(`/sites/${site.site_id}/overview`)
            }
          "
          :shadow="site.up ? 'hover' : 'never'"
        />
      </el-col>
    </el-row>
  </div>
  <div v-if="sites.length == 0">
    <h3>
      You do not have access to any sites, setup a new site or ask the site owner to invite you.
    </h3>
  </div>
</template>
