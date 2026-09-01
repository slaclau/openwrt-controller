<script setup lang="ts">
import SvgIcon from '@jamescoyle/vue-icon'
import { useRoute, useRouter } from 'vue-router'
import {
  mdiMonitorDashboard,
  mdiServerOutline,
  mdiMonitorCellphone,
  mdiCog,
  mdiChartLine,
} from '@mdi/js'
import { nextTick, computed, ref, watch, onMounted, onUnmounted } from 'vue'

const route = useRoute()
const router = useRouter()

const tabs = ref([
  { id: 'overview', icon: mdiMonitorDashboard, route: { name: 'Overview' } },
  { id: 'devices', icon: mdiServerOutline, route: { name: 'Devices' } },
  { id: 'clients', icon: mdiMonitorCellphone, route: { name: 'Clients' } },
  { id: 'dpi', icon: mdiChartLine, route: { name: 'DPI' } },
  { id: 'settings', icon: mdiCog, route: { name: 'Settings' } },
])

const hoverIndex = ref<number | null>(null)
const isDragging = ref(false)
const dragActiveIndex = ref<number | null>(null)

// NEW VISUAL STATES: Handles the click routing locks and growth scale triggers
const isTransitioning = ref(false)
const isGrowing = ref(false)

const tabBarRef = ref<HTMLElement | null>(null)
const tabRefs = ref<HTMLElement[]>([])

const pillWidth = ref(0)
const pillLeft = ref(0)

const startX = ref(0)
const startPillLeft = ref(0)
const dynamicDragLeft = ref(0)

const preloadedPaths = ref<Set<string>>(new Set())

const preloadRouteAsset = (newRoute) => {
  if (preloadedPaths.value.has(newRoute) || newRoute === route) return
  const matchedRoute = router.resolve(newRoute)
  if (matchedRoute && matchedRoute.matched.length > 0) {
    matchedRoute.matched.forEach((record) => {
      const components = record.components
      if (!components) return
      Object.values(components).forEach((component) => {
        if (typeof component === 'function') {
          try {
            ;(component as () => Promise<any>)()
            preloadedPaths.value.add(newRoute)
          } catch (e) {
            console.error('Failed to preload chunk asset path:', newRoute, e)
          }
        }
      })
    })
  }
}

const routeActiveIndex = computed(() => {
  const index = tabs.value.findIndex((tab) =>
    route.matched.some((r) => r.path === tab.route || r.name === tab.route.name),
  )
  return index !== -1 ? index : 0
})

const activeIndex = ref(routeActiveIndex.value)

watch(routeActiveIndex, (newIdx) => {
  if (!isDragging.value && !isTransitioning.value) {
    activeIndex.value = newIdx
    updatePillPosition()
  }
})

const targetIndex = computed(() => {
  return hoverIndex.value !== null ? hoverIndex.value : activeIndex.value
})

const pillStyle = computed(() => {
  const currentLeft = isDragging.value ? dynamicDragLeft.value : pillLeft.value
  return {
    width: `${pillWidth.value}px`,
    transform: `translate3d(${currentLeft}px, 0, 0)`,
    // Moving growth properties to a nested layer allows the position track to stay smooth and jitter-free
    transition: isDragging.value
      ? 'none'
      : 'transform 0.35s cubic-bezier(0.25, 1, 0.5, 1), width 0.35s cubic-bezier(0.25, 1, 0.5, 1)',
  }
})

const getClosestIndex = (clientX: number) => {
  let closestIdx = activeIndex.value
  let smallestDistance = Infinity

  tabRefs.value.forEach((tabEl, idx) => {
    if (!tabEl) return
    const rect = tabEl.getBoundingClientRect()
    const centerPoint = rect.left + rect.width / 2
    const currentDistance = Math.abs(clientX - centerPoint)

    if (currentDistance < smallestDistance) {
      smallestDistance = currentDistance
      closestIdx = idx
    }
  })
  return closestIdx
}

const updatePillPosition = () => {
  if (isDragging.value) return

  const targetTab = tabRefs.value[targetIndex.value]
  if (targetTab && tabBarRef.value) {
    const parentRect = tabBarRef.value.getBoundingClientRect()
    const tabRect = targetTab.getBoundingClientRect()

    pillLeft.value = tabRect.left - parentRect.left - 6
    pillWidth.value = tabRect.width
  }
}

// Global Event Handler: Option Touched
const handlePointerDown = (event: PointerEvent) => {
  if (!tabBarRef.value || isTransitioning.value) return
  tabBarRef.value.setPointerCapture(event.pointerId)

  const initialTargetIdx = getClosestIndex(event.clientX)

  // CLICK ANIMATION INTERACTION LOOP:
  // Fired if clicking a different tab option instead of starting a dragging motion
  if (initialTargetIdx !== activeIndex.value) {
    isTransitioning.value = true
    isGrowing.value = true // Instantly triggers expansion scale frame changes

    // Shift position values to let CSS execute the slide tracking animation smoothly
    activeIndex.value = initialTargetIdx
    preloadRouteAsset(tabs.value[initialTargetIdx].route)
    updatePillPosition()

    // De-escalate size scaling right as the capsule snaps onto its final target zone
    setTimeout(() => {
      isGrowing.value = false
    }, 240)

    // Complete router transitions seamlessly when the slide finishes
    setTimeout(() => {
      router.push(tabs.value[initialTargetIdx].route).then(() => {
        isTransitioning.value = false
      })
    }, 350)
    return
  }

  // Fallback tracking sequence handles manual dragging gestures
  isDragging.value = true
  isGrowing.value = true
  startX.value = event.clientX
  dragActiveIndex.value = initialTargetIdx
  preloadRouteAsset(tabs.value[initialTargetIdx].route)

  const parentRect = tabBarRef.value.getBoundingClientRect()
  const activeTabRect = tabRefs.value[activeIndex.value].getBoundingClientRect()

  startPillLeft.value = activeTabRect.left - parentRect.left - 6
  dynamicDragLeft.value = startPillLeft.value
  pillWidth.value = activeTabRect.width
}

const handlePointerMove = (event: PointerEvent) => {
  if (isTransitioning.value) return

  if (!isDragging.value) {
    const currentHoverIdx = getClosestIndex(event.clientX)
    if (hoverIndex.value !== currentHoverIdx) {
      hoverIndex.value = currentHoverIdx
      updatePillPosition()
      preloadRouteAsset(tabs.value[currentHoverIdx].route)
    }
    return
  }

  const deltaX = event.clientX - startX.value
  dynamicDragLeft.value = startPillLeft.value + deltaX

  const currentClosestIdx = getClosestIndex(event.clientX)
  if (currentClosestIdx !== dragActiveIndex.value) {
    dragActiveIndex.value = currentClosestIdx
    activeIndex.value = currentClosestIdx
    preloadRouteAsset(tabs.value[currentClosestIdx].route)

    const targetTab = tabRefs.value[currentClosestIdx]
    if (targetTab) pillWidth.value = targetTab.getBoundingClientRect().width
  }
}

const handlePointerUp = () => {
  if (isTransitioning.value || !isDragging.value) return
  isDragging.value = false
  isGrowing.value = false // Shrinks the capsule back to its resting state on release
  hoverIndex.value = null

  if (dragActiveIndex.value !== null) {
    router.push(tabs.value[dragActiveIndex.value].route)
  }

  dragActiveIndex.value = null
  updatePillPosition()
}

const handleMouseLeave = () => {
  if (isDragging.value || isTransitioning.value) return
  hoverIndex.value = null
  updatePillPosition()
}

watch(
  () => route,
  () => {
    activeIndex.value = routeActiveIndex.value
    nextTick(updatePillPosition)
  },
  { immediate: true },
)

onMounted(() => {
  nextTick(updatePillPosition)
  window.addEventListener('resize', updatePillPosition)
})

onUnmounted(() => {
  window.removeEventListener('resize', updatePillPosition)
})
</script>

<template>
  <div class="tab-bar-wrapper">
    <div
      class="tab-bar"
      ref="tabBarRef"
      @pointerdown="handlePointerDown"
      @pointermove="handlePointerMove"
      @pointerup="handlePointerUp"
      @pointercancel="handlePointerUp"
      @mouseleave="handleMouseLeave"
      :class="{ dragging: isDragging, transitioning: isTransitioning, growing: isGrowing }"
    >
      <!-- ADDED: Nested layout layer separates horizontal movement from vertical growth -->
      <div class="tab-bar-pill" :style="pillStyle">
        <div class="tab-bar-pill-inner" />
      </div>

      <button
        v-for="(tab, index) in tabs"
        :key="tab.id"
        :ref="
          (el) => {
            if (el) tabRefs[index] = el as HTMLElement
          }
        "
        type="button"
        :class="['tab-item', { active: activeIndex === index }]"
      >
        <div class="icon-spring-wrapper">
          <svg-icon type="mdi" :path="tab.icon" :size="24" />
        </div>
      </button>
    </div>
  </div>
</template>

<style scoped lang="css">
/* --- CONTAINER WRAPPER --- */
.tab-bar-wrapper {
  position: fixed;
  bottom: 24px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 999;
  pointer-events: none;
}

/* --- THE MAIN NAVIGATION BAR --- */
.tab-bar {
  position: relative;
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 6px;
  border-radius: 9999px;
  pointer-events: auto;
  touch-action: none;
  user-select: none;
  overflow: visible;

  backdrop-filter: blur(20px) saturate(180%);
  -webkit-backdrop-filter: blur(20px) saturate(180%);
  box-shadow:
    0 1px 2px rgba(0, 0, 0, 0.02),
    0 12px 32px rgba(0, 0, 0, 0.06);
}

.tab-bar::after {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: 9999px;
  pointer-events: none;
  z-index: 3;
  transition: border-color 0.25s ease;
}

/* --- THE OUTER POSITIONING PILL --- */
.tab-bar-pill {
  position: absolute;
  top: 6px;
  bottom: 6px;
  left: 6px;
  z-index: 1;
  pointer-events: none;
  /* Transitions exclusively handle horizontal sliding tracks now */
}

/* --- THE NESTED VISUAL GLASS PILL LAYERS --- */
.tab-bar-pill-inner {
  position: absolute;
  inset: 0; /* Renders flush inside parent bounds when resting */
  border-radius: 9999px;

  /* Handles vertical breakout scaling animations safely on a separate thread */
  transition:
    top 0.25s cubic-bezier(0.25, 1, 0.5, 1),
    bottom 0.25s cubic-bezier(0.25, 1, 0.5, 1),
    transform 0.25s cubic-bezier(0.25, 1, 0.5, 1),
    background 0.25s ease,
    border-color 0.25s ease,
    box-shadow 0.25s ease;
}

/* 
  THE VISUAL BREAKOUT RE-FIX:
  The growth animation targets the inner layer exclusively. 
  The outer container coordinates stay perfectly steady, preventing any rendering jitters.
*/
.tab-bar.growing .tab-bar-pill-inner {
  top: -12px;
  bottom: -12px;
  left: -4px;
  right: -4px;
  transform: scaleX(1.02);
}

/* --- LIGHT MODE SPECIFIC COLORS --- */
:root:not(.dark) .tab-bar {
  background: rgba(255, 255, 255, 0.65);
}

:root:not(.dark) .tab-bar::after {
  border: 1px solid rgba(0, 0, 0, 0.08);
}

:root:not(.dark) .tab-bar-pill-inner {
  background: linear-gradient(
    to bottom,
    rgba(255, 255, 255, 1) 0%,
    rgba(255, 255, 255, 0.88) 45%,
    rgba(245, 246, 248, 0.7) 100%
  );
  border: 1px solid rgba(0, 0, 0, 0.08);
  box-shadow:
    0 1.5px 0px rgba(255, 255, 255, 1) inset,
    0 3px 8px rgba(0, 0, 0, 0.04);
}

:root:not(.dark) .tab-bar.growing .tab-bar-pill-inner {
  border-color: rgba(0, 0, 0, 0.12);
  box-shadow:
    0 1.5px 0px rgba(255, 255, 255, 1) inset,
    0 8px 18px rgba(0, 0, 0, 0.06);
}

/* --- DARK MODE SPECIFIC COLORS --- */
:root.dark .tab-bar {
  background: rgba(28, 28, 30, 0.7);
}

:root.dark .tab-bar::after {
  border: 1px solid rgba(255, 255, 255, 0.12);
}

:root.dark .tab-bar-pill-inner {
  background: linear-gradient(
    to bottom,
    rgba(50, 50, 54, 0.75) 0%,
    rgba(28, 28, 30, 0.55) 50%,
    rgba(14, 14, 16, 0.4) 100%
  );
  border: 1px solid rgba(255, 255, 255, 0.28);
  box-shadow:
    0 1px 0px rgba(255, 255, 255, 0.2) inset,
    0 4px 12px rgba(0, 0, 0, 0.4);
}

:root.dark .tab-bar.growing .tab-bar-pill-inner {
  background: linear-gradient(to bottom, rgba(60, 60, 66, 0.95) 0%, rgba(20, 20, 22, 0.85) 100%);
  border-color: rgba(255, 255, 255, 0.4);
  box-shadow:
    0 1.5px 0px rgba(255, 255, 255, 0.3) inset,
    0 10px 24px rgba(0, 0, 0, 0.55);
}

/* --- TAB ITEMS & SPRING WRAPPERS --- */
.tab-item {
  position: relative;
  z-index: 2;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  width: 64px;
  height: 48px;
  border: none;
  background: transparent;
  border-radius: 999px;
  cursor: pointer;
  color: var(--el-text-color-primary);
  outline: none;
  -webkit-tap-highlight-color: transparent;
  transition: color 0.25s ease;
}

.tab-item.active {
  color: var(--el-color-primary);
}

.icon-spring-wrapper {
  display: flex;
  align-items: center;
  justify-content: center;
  transition: transform 0.4s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.tab-item.active .icon-spring-wrapper {
  transform: scale(1.12);
}
</style>
