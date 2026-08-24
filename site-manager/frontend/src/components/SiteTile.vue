<script setup lang="ts">
import type { SiteWithOutages } from '@/sdk'
import StatusDot from './StatusDot.vue'
import StatusBar from './StatusBar.vue'
defineProps<{ site: SiteWithOutages }>()
</script>

<template>
  <el-card>
    <template #header>
      <div class="card-header">
        {{ site.name }}
      </div>
    </template>
    <div>
      <span style="float: left; width: 80%">
        <StatusBar :outages="site.outages" :time-since-heartbeat="site.time_since_heartbeat" />
      </span>
      <StatusDot :online="site.up" style="float: right" />
    </div>
  </el-card>
</template>
