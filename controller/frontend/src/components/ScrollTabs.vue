<template>
  <el-tabs v-bind="$attrs">
    <!-- Loop through all child nodes passed to the default slot -->
    <template v-for="(node, index) in paneNodes" :key="index">
      <el-tab-pane v-bind="node.props">
        <template v-if="node.children && node.children.label" #label>
          <component :is="node.children.label" />
        </template>

        <el-scrollbar height="100%" view-style="max-width: 100%; overflow-x: hidden;">
          <!-- Render the inner contents/slots of the original el-tab-pane -->
          <component :is="node.children?.default" v-if="node.children?.default" />
          <component :is="node.children" v-else />
        </el-scrollbar>
      </el-tab-pane>
    </template>
  </el-tabs>
</template>

<script setup>
import { useSlots, computed } from 'vue'

const slots = useSlots()

// Safely extract and filter el-tab-pane elements
const paneNodes = computed(() => {
  const children = slots.default ? slots.default() : []
  
  return children.flatMap(node => {
    // Unroll Fragment wrappers (e.g. if you happen to use v-for outside)
    if (node.type?.toString() === 'Symbol(Fragment)' || node.type?.toString() === 'Symbol(v-fgt)') {
      return node.children || []
    }
    return node
  }).filter(node => {
    // Ensure it's a valid Vue component node with props
    return node && node.props
  })
})
</script>

<style scoped lang="css">
:deep(.el-tabs__content) {
  flex-grow: 1;
  min-height: 0; /* CRITICAL: Prevents the content panel from expanding indefinitely */
}

:deep(.el-tab-pane) {
  height: 100%;
}
</style>
