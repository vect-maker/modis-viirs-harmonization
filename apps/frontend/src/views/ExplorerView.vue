<script setup lang="ts">
import { computed, onMounted, shallowRef, watch, useTemplateRef } from 'vue'
import { useMediaQuery, useElementSize, useGeolocation, usePermission } from '@vueuse/core'
import { storeToRefs } from 'pinia'
import FireMap from '@/components/map/FireMap.vue'
import HotspotDetails from '@/components/map/HotspotDetails.vue'
import HotspotControlPanel from '@/components/features/HotspotControlPanel.vue'
import HotspotTimeline from '@/components/features/HotspotTimeline.vue'
import DatePromptDialog from '@/components/features/DatePromptDialog.vue'
import LocationPromptDialog from '@/components/features/LocationPromptDialog.vue'
import MapActionBar from '@/components/common/MapActionBar.vue'
import type { HotspotResponse } from '@/api'
import { useHotspotsStore } from '@/stores/hotspots'

const hotspotsStore = useHotspotsStore()
const { filteredHotspots, availableDates, availableDateSet } = storeToRefs(hotspotsStore)
const todayUtc = new Date().toISOString().slice(0, 10)
const datePromptOpen = shallowRef(false)
const datePromptPending = shallowRef(false)
const locationPromptOpen = shallowRef(false)

const locationPermission = usePermission('geolocation')
const {
  coords,
  error: geolocationError,
  resume: resumeGeolocation,
} = useGeolocation({ immediate: false })

const userLocation = computed(() => {
  const { latitude, longitude } = coords.value
  if (!Number.isFinite(latitude) || !Number.isFinite(longitude)) return null
  return { latitude, longitude }
})

const locationErrorMessage = computed(() => {
  if (!geolocationError.value) return null
  if (geolocationError.value.code === 1) {
    return 'Location permission is blocked. Allow location access in your browser settings and try again.'
  }
  return geolocationError.value.message || 'Unable to retrieve your current location.'
})

watch(
  locationPermission,
  (state) => {
    if (state === 'granted') {
      resumeGeolocation()
      locationPromptOpen.value = false
    }
  },
  { immediate: true },
)

watch(userLocation, (loc) => {
  if (!loc) return
  locationPromptOpen.value = false
  if (datePromptPending.value) {
    datePromptPending.value = false
    datePromptOpen.value = true
  }
})

watch(locationPromptOpen, (isOpen) => {
  if (!isOpen && datePromptPending.value) {
    datePromptPending.value = false
    datePromptOpen.value = true
  }
})

function onEnableLocation() {
  resumeGeolocation()
}

function onRequestLocation() {
  if (locationPermission.value === 'granted') {
    resumeGeolocation()
    return
  }
  locationPromptOpen.value = true
}

onMounted(async () => {
  if (locationPermission.value !== 'granted' && !userLocation.value) {
    locationPromptOpen.value = true
  }

  await hotspotsStore.fetchAvailableDates()
  if (hotspotsStore.availableDateSet.has(todayUtc)) {
    await hotspotsStore.selectDateRange({ start: todayUtc, end: todayUtc })
    return
  }
  if (hotspotsStore.availableDateSet.size > 0) {
    if (locationPromptOpen.value) {
      datePromptPending.value = true
    } else {
      datePromptOpen.value = true
    }
    return
  }
  await hotspotsStore.fetchHotspots({ limit: 100 })
})

function onPromptSelectDate(date: string) {
  void hotspotsStore.selectDateRange({ start: date, end: date })
}
const isDesktop = useMediaQuery('(min-width: 768px)')
const panelOpen = shallowRef(isDesktop.value)
const timelineOpen = shallowRef(false)
const timelineElement = useTemplateRef<HTMLDivElement>('timelineElement')
const { height: timelineHeight } = useElementSize(timelineElement)
const mapBottomInset = computed(() => timelineHeight.value + 24)
const selectedHotspot = shallowRef<HotspotResponse | null>(null)
const areaKm2 = shallowRef<number | null>(null)

watch(filteredHotspots, () => {
  selectedHotspot.value = null
})

function onRoiChange(payload: { areaKm2: number | null }) {
  areaKm2.value = payload.areaKm2
}
</script>

<template>
  <div
    class="flex h-dvh min-h-0 flex-col overflow-hidden bg-surface-base font-sans text-ink-primary selection:bg-accent selection:text-surface-base"
  >
    <main class="relative min-h-0 flex-1" aria-label="PyroTrace Nicaragua hotspot map">
      <h1 class="sr-only">PyroTrace — Nicaragua Fire Activity</h1>
      <div class="absolute inset-0">
        <FireMap
          :side-panel-open="panelOpen"
          :bottom-inset="mapBottomInset"
          :user-location="userLocation"
          @hotspot-select="selectedHotspot = $event"
          @roi-change="onRoiChange"
          @request-location="onRequestLocation"
        >
          <template #dock="{ drawArea, clearArea, locateUser, showGlobe }">
            <div
              ref="timelineElement"
              class="absolute bottom-3 left-3 right-3 z-20 md:bottom-5 md:left-5"
              :class="panelOpen ? 'md:right-[22.5rem]' : 'md:right-5'"
            >
              <HotspotTimeline v-model:open="timelineOpen">
                <template #tools>
                  <MapActionBar
                    :has-area="areaKm2 !== null"
                    @draw="drawArea"
                    @locate="locateUser"
                    @globe="showGlobe"
                    @clear="clearArea"
                  />
                </template>
              </HotspotTimeline>
            </div>
          </template>
        </FireMap>
      </div>
      <aside
        class="pointer-events-none absolute right-3 top-3 z-20 w-[min(20rem,calc(100%_-_4.5rem))] md:right-5 md:top-5"
        aria-label="Map filters and results"
      >
        <HotspotControlPanel
          v-model:open="panelOpen"
          :area-km2="areaKm2"
          class="pointer-events-auto"
        />
      </aside>
      <HotspotDetails
        v-if="selectedHotspot"
        :hotspot="selectedHotspot"
        :platform="hotspotsStore.getPlatform(selectedHotspot.platform_id)"
        :country="hotspotsStore.getCountry(selectedHotspot.country_id)"
        class="absolute left-3 right-3 z-20 md:left-5 md:right-auto md:w-80"
        :style="{ bottom: `${mapBottomInset + 64}px` }"
        @close="selectedHotspot = null"
      />
      <LocationPromptDialog
        v-model:open="locationPromptOpen"
        :error-message="locationErrorMessage"
        @enable="onEnableLocation"
      />
      <DatePromptDialog
        v-if="availableDates"
        v-model:open="datePromptOpen"
        :today-date="todayUtc"
        :available-dates="availableDates"
        :available-date-set="availableDateSet"
        @select-date="onPromptSelectDate"
      />
    </main>
  </div>
</template>
