<script setup lang="ts">
import type { OutageWithoutSite } from '@/sdk'
import { onUpdated, ref, watch, type Ref } from 'vue'

const props = defineProps<{ outages: OutageWithoutSite[]; lastHeartbeat: number }>()

import { computed } from 'vue'

// 1. Define sample raw outage data (Timestamps in milliseconds)
const now = Date.now() / 1000

const TWENTY_FOUR_HOURS = 24 * 60 * 60
const startTimeWindow = now - TWENTY_FOUR_HOURS
const MIN_WIDTH_PERCENT = 1.5 // Enforce a 1.5% minimum width (~9px on a 600px wide bar)

const rawBlocks = computed(() => {
  // Filter, map to standard keys, and clamp outages strictly inside our 24h window
  const activeOutages = props.outages
    .map((o) => {
      return {
        start: o.outage_start ? Math.max(o.outage_start, startTimeWindow) : startTimeWindow,
        end: Math.min(o.outage_end, now),
      }
    })
    .filter((o) => o.start < o.end)
    .sort((a, b) => a.start - b.start)

  if (props.lastHeartbeat + 30 < now) activeOutages.push({ start: props.lastHeartbeat, end: now })

  const events = []
  let currentPos = startTimeWindow

  activeOutages.forEach((outage) => {
    if (outage.start > currentPos) {
      events.push({ isDown: false, start: currentPos, end: outage.start })
    }
    events.push({ isDown: true, start: outage.start, end: outage.end })
    currentPos = outage.end
  })

  if (currentPos < now) {
    events.push({ isDown: false, start: currentPos, end: now })
  }

  return events.map((event) => {
    const duration = event.end - event.start
    const widthPercentage = (duration / TWENTY_FOUR_HOURS) * 100

    return {
      isDown: event.isDown,
      widthPercentage,
    }
  })
})

const adjustedBlocks = computed(() => {
  console.log(rawBlocks.value)
  let blocks = rawBlocks.value.map((b) => ({ ...b, displayWidth: b.widthPercentage }))
  // Calculate how much width we need to manufacture to satisfy our minimum floor requirement
  let addedWidth = 0
  blocks.forEach((block) => {
    if (block.displayWidth < MIN_WIDTH_PERCENT) {
      addedWidth += MIN_WIDTH_PERCENT - block.displayWidth
      block.displayWidth = MIN_WIDTH_PERCENT
    }
  })

  // Distribute the width deficit by shrinking down large green segments proportionally
  if (addedWidth > 0) {
    const reductionEligibleTotal = blocks
      .filter((b) => !b.isDown && b.displayWidth > MIN_WIDTH_PERCENT)
      .reduce((sum, b) => sum + b.displayWidth, 0)

    if (reductionEligibleTotal > 0) {
      blocks.forEach((block) => {
        if (!block.isDown && block.displayWidth > MIN_WIDTH_PERCENT) {
          const reductionShare = (block.displayWidth / reductionEligibleTotal) * addedWidth
          block.displayWidth = Math.max(MIN_WIDTH_PERCENT, block.displayWidth - reductionShare)
        }
      })
    }
  }

  return blocks
})
</script>

<template>
  <div class="merged-bar">
    <div
      v-for="(block, index) in adjustedBlocks"
      :key="index"
      class="bar-segment"
      :class="block.isDown ? 'red' : 'green'"
      :style="{ width: block.displayWidth + '%' }"
    ></div>
  </div>

  <div class="footer-labels">
    <span>24h ago</span>
    <span>Now</span>
  </div>
</template>

<style scoped>
.merged-bar {
  display: flex;
  height: 12px;
  width: 100%;
  border-radius: 6px;
  overflow: hidden;
}

.bar-segment {
  height: 100%;
  position: relative;
  cursor: pointer;
}

/* Status Colours */
.green {
  background-color: #22c55e;
  /* Emerald green */
}

.red {
  background-color: #ef4444;
  /* Rose red */
}

.footer-labels {
  display: flex;
  justify-content: space-between;
  margin-top: 8px;
  font-size: 11px;
  color: #64748b;
}
</style>
