<script setup lang="ts">
import { site_manager_client } from '@/client'
import SiteTile from '@/components/SiteTile.vue'
import { setIntervalImmediate } from '@/controller_src/utils'
import { getAllMySitesSitesGet, type Site } from '@/sdk'
import router from '@/router'
import { onMounted, onUnmounted, ref, type Ref } from 'vue'

const sites: Ref<Site[]> = ref([])
let timer: number

onMounted(() => {
  timer = setIntervalImmediate(() => {
    getAllMySitesSitesGet({ client: site_manager_client }).then((res) => {
      if (res.data) sites.value = res.data
    })
  }, 3000)
})

onUnmounted(() => {
  clearInterval(timer)
})
</script>

<template>
  <div v-if="sites.length > 0" v-for="site in sites" :key="site.site_id">
    <el-row>
      <el-col :xs="24" :sm="12" :md="6" :lg="4" :xl="3">
        <SiteTile :site="site" @click="
          () => {
            if (site.up) router.push(`/sites/${site.site_id}`)
          }
        " :shadow="site.up ? 'hover' : 'never'" />
      </el-col>
    </el-row>
  </div>
  <div v-else>
    <h3>
      You do not have access to any sites, setup a new site or ask the site owner to invite you.
    </h3>
  </div>
</template>
