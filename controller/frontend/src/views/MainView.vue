<script setup lang="ts">
import TabBar from '../components/TabBar.vue'
</script>

<template>
  <el-main style="padding-bottom: 110px">
    <router-view />
  </el-main>
  <TabBar />
</template>
