import { defineStore } from 'pinia'
import { ref, type Ref } from 'vue'

import { getStatusStatusGet, type Status } from '@controller/sdk'

export const useStatusStore = defineStore('status', () => {
  const status: Ref<Status | null> = ref(null)
  const loading = ref(false)
  let timer = null

  async function refreshData() {
    loading.value = true
    const response = await getStatusStatusGet()
    if (response.data) status.value = response.data
    else console.error('Failed to fetch data', response.error)
    loading.value = false
  }

  function startAutoRefresh(intervalMs = 5000) {
    if (timer) return // prevent multiple timers
    refreshData() // fetch immediately on start
    timer = setInterval(refreshData, intervalMs)
  }

  function stopAutoRefresh() {
    if (timer) {
      clearInterval(timer)
      timer = null
    }
  }

  return { status, loading, refreshData, startAutoRefresh, stopAutoRefresh }
})
