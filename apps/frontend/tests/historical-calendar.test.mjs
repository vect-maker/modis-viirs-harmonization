import { test, before, after } from 'node:test'
import assert from 'node:assert/strict'
import { calendarCount, buildCalendarRows, calendarColor } from '../src/utils/historicalCalendar.ts'
import { createServer } from 'vite'
import { createPinia, setActivePinia } from 'pinia'
import { createSSRApp, h } from 'vue'
import { renderToString } from 'vue/server-renderer'

const sampleArchive = {
  country: 'All Regions',
  timezone: 'UTC',
  harmonized: false,
  coverageVerified: false,
  source: 'Backend API',
  totalRecords: 1000,
  firstDetection: '2000-11-01',
  lastDetection: '2025-12-31',
  months: [
    {
      year: 2000,
      month: 11,
      total: 10,
      modisCount: 10,
      viirsCount: null,
      observedDays: 6,
      avgFrp: 0,
      firstDetection: '',
      lastDetection: '',
    },
    {
      year: 2012,
      month: 1,
      total: 304,
      modisCount: 159,
      viirsCount: 145,
      observedDays: 26,
      avgFrp: 0,
      firstDetection: '',
      lastDetection: '',
    },
    {
      year: 2020,
      month: 3,
      total: 686,
      modisCount: 86,
      viirsCount: 600,
      observedDays: 31,
      avgFrp: 0,
      firstDetection: '',
      lastDetection: '',
    },
  ],
}

let server, useCalendarStore, useHotspotsStore
before(async () => {
  server = await createServer({
    cacheDir: 'node_modules/.vite-history-tests',
    server: { middlewareMode: true, hmr: false },
    appType: 'custom',
  })
  ;({ useCalendarStore } = await server.ssrLoadModule('/src/stores/calendar.ts'))
  ;({ useHotspotsStore } = await server.ssrLoadModule('/src/stores/hotspots.ts'))
})
after(async () => {
  await server?.close()
})

test('matrix covers all 26 years and 12 months without inventing zeros', () => {
  const rows = buildCalendarRows(sampleArchive.months, 2000, 2025, 'ALL')
  assert.equal(rows.length, 26)
  assert.equal(rows[0].year, 2025)
  assert.equal(rows.at(-1).year, 2000)
  assert(rows.every((row) => row.cells.length === 12))
  assert.equal(rows.at(-1).cells[0].count, null)
  assert.equal(rows.at(-1).cells[10].count, 10)
  const viirs = buildCalendarRows(sampleArchive.months, 2000, 2025, 'VIIRS')
  assert(viirs.find((row) => row.year === 2011).cells.every((cell) => cell.count === null))
  assert.equal(viirs.find((row) => row.year === 2012).cells[0].count, 145)
})

test('missing records and an explicit zero remain distinct in counts and color', () => {
  assert.equal(calendarCount(undefined, 'ALL'), null)
  assert.equal(calendarCount({ total: 0, modisCount: 0, viirsCount: null }, 'ALL'), 0)
  assert.notEqual(calendarColor(null, 100), calendarColor(0, 100))
  assert.notEqual(calendarColor(0, 100), calendarColor(100, 100))
})

test('historical month and sensor selections are independent of map queries', () => {
  setActivePinia(createPinia())
  const map = useHotspotsStore()
  const history = useCalendarStore()
  history.archive = sampleArchive
  map.setDateRange({ start: '2024-05-28', end: '2024-05-28' })
  map.setSensor('MODIS')
  const points = map.filteredHotspots
  history.selectMonth(2020, 3)
  history.setSensor('VIIRS')
  assert.equal(history.selectedMonth.year, 2020)
  assert.equal(history.selectedCount, 600)
  assert.equal(history.total, 745)
  assert.equal(map.selectedSensor, 'MODIS')
  assert.deepEqual(map.dateRange, { start: '2024-05-28', end: '2024-05-28' })
  assert.equal(map.filteredHotspots, points)
  history.selectMonth(2012, 1)
  assert.equal(history.selectedCount, 145)
  const selected = history.selectedPeriod
  history.selectMonth(2020, 13)
  history.selectMonth(1999, 12)
  assert.equal(history.selectedPeriod, selected)
})

test('calendar renders accessible ECharts heatmap region', async () => {
  const { default: Calendar } = await server.ssrLoadModule(
    '/src/components/common/BurningCalendar.vue',
  )
  const rows = buildCalendarRows(sampleArchive.months, 2000, 2000, 'ALL')
  const html = await renderToString(
    createSSRApp({
      render: () =>
        h(Calendar, { rows, maxCount: 10000, selectedPeriod: { year: 2000, month: 11 } }),
    }),
  )
  assert(html.includes('role="region"'))
  assert(html.includes('Historical monthly detections heatmap'))
})

test('historical details explicitly identify archive scope and unchanged daily map', async () => {
  const { default: Calendar } = await server.ssrLoadModule(
    '/src/components/features/HistoricalCalendar.vue',
  )
  const pinia = createPinia()
  const store = useCalendarStore(pinia)
  store.archive = sampleArchive
  store.selectMonth(2000, 1)
  const app = createSSRApp({ render: () => h(Calendar) })
  app.use(pinia)
  const html = await renderToString(app)
  assert(html.includes('Historical Archive'))
  assert(html.includes('1,000'))
  assert(html.includes('Map area and date filters do not apply'))
  assert(html.includes('Fire absence cannot be inferred'))
  assert(html.includes('Historical point loading is not connected yet'))
})

test('Reka activity tabs render the historical view separately from the daily view', async () => {
  const { default: Tabs } = await server.ssrLoadModule('/src/components/ui/BaseActivityTabs.vue')
  const app = createSSRApp({
    render: () =>
      h(
        Tabs,
        { modelValue: 'history' },
        {
          daily: () => h('p', 'DAILY_VIEW_CONTENT'),
          history: () => h('p', 'HISTORICAL_VIEW_CONTENT'),
        },
      ),
  })
  const html = await renderToString(app)
  assert.equal((html.match(/role="tab"/g) ?? []).length, 2)
  assert(html.includes('aria-selected="true"'))
  assert(html.includes('HISTORICAL_VIEW_CONTENT'))
  assert(!html.includes('DAILY_VIEW_CONTENT'))
})
