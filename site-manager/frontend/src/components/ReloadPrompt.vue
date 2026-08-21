<!-- components/PwaUpdateDialog.vue -->
<script setup lang="ts">
import { watch } from 'vue'
import { useRegisterSW } from 'virtual:pwa-register/vue'
import { ElMessageBox, ElMessage } from 'element-plus'

const { offlineReady, needRefresh, updateServiceWorker } = useRegisterSW()

// Trigger modal when an update is available
watch(needRefresh, (needsUpdate) => {
  if (needsUpdate) {
    showUpdateDialog()
  }
})

// Optional background toast for successful caching
watch(offlineReady, (isReady) => {
  if (isReady) {
    ElMessage.success('App is cached and ready to work offline!')
  }
})

console.log("RP", offlineReady.value)

function showUpdateDialog() {
  ElMessageBox.confirm(
    'A new version of the app is available. Please reload to apply the updates.',
    'Update Available',
    {
      confirmButtonText: 'Reload Now',
      cancelButtonText: 'Later',
      type: 'info',
      closeOnClickModal: false,  // Prevents closing by clicking outside
      closeOnPressEscape: false, // Prevents closing via ESC key
      showClose: false,          // Removes the 'X' button to encourage an explicit action
    }
  )
    .then(() => {
      updateServiceWorker(true) // Triggers skipWaiting and reloads the page
    })
    .catch(() => {
      // User clicked 'Later'
      console.log('Update postponed by user.')
    })
}
</script>

<template>
  <!-- Renderless logic component -->
</template>
