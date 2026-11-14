import { test, before, after } from 'node:test'
import assert from 'node:assert/strict'
import archive from '../src/data/historical_monthly.json' with { type: 'json' }
import { calendarCount, buildCalendarRows, calendarColor } from '../src/utils/historicalCalendar.ts'
import { createServer } from 'vite'
import { createPinia, setActivePinia } from 'pinia'
import { createSSRApp, h } from 'vue'
import { renderToString } from 'vue/server-renderer'
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

test('historical export reconciles with the Nicaragua source Parquet', () => {
  assert.equal(archive.country, 'Nicaragua')
  assert.equal(archive.timezone, 'UTC')
  assert.equal(archive.harmonized, false)
  assert.equal(archive.coverageVerified, false)
  assert.equal(archive.totalRecords, 800480)
  assert.equal(
    archive.months.reduce((sum, month) => sum + month.total, 0),
    archive.totalRecords,
  )
  assert.equal(
    archive.months.reduce((sum, month) => sum + (month.modisCount ?? 0), 0),
    119418,
  )
  assert.equal(
    archive.months.reduce((sum, month) => sum + (month.viirsCount ?? 0), 0),
    681062,
  )
  assert.equal(
    new Set(archive.months.map((month) => `${month.year}-${month.month}`)).size,
    archive.months.length,
  )
  for (const month of archive.months) {
    assert.equal(month.total, (month.modisCount ?? 0) + (month.viirsCount ?? 0))
    assert(month.observedDays > 0 && month.observedDays <= 31)
    assert(month.firstDetection.startsWith(`${month.year}-${String(month.month).padStart(2, '0')}`))
    assert(month.lastDetection.startsWith(`${month.year}-${String(month.month).padStart(2, '0')}`))
  }
})

test('matrix covers all 26 years and 12 months without inventing zeros', () => {
  const rows = buildCalendarRows(archive.months, 2000, 2025, 'ALL')
  assert.equal(rows.length, 26)
  assert.equal(rows[0].year, 2025)
  assert.equal(rows.at(-1).year, 2000)
  assert(rows.every((row) => row.cells.length === 12))
  assert.equal(rows.at(-1).cells[0].count, null)
  assert(rows.at(-1).cells[10].count > 0)
  const viirs = buildCalendarRows(archive.months, 2000, 2025, 'VIIRS')
  assert(viirs.find((row) => row.year === 2011).cells.every((cell) => cell.count === null))
  assert(viirs.find((row) => row.year === 2012).cells[0].count > 0)
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
  map.setDateRange({ start: '2024-05-28', end: '2024-05-28' })
  map.setSensor('MODIS')
  const points = map.filteredHotspots
  history.selectMonth(2020, 3)
  history.setSensor('VIIRS')
  assert.equal(history.selectedMonth.year, 2020)
  assert.equal(history.selectedCount, history.selectedMonth.viirsCount)
  assert.equal(history.total, 681062)
  assert.equal(map.selectedSensor, 'MODIS')
  assert.deepEqual(map.dateRange, { start: '2024-05-28', end: '2024-05-28' })
  assert.equal(map.filteredHotspots, points)
  history.selectMonth(2010, 1)
  assert.equal(history.selectedCount, null)
  const selected = history.selectedPeriod
  history.selectMonth(2020, 13)
  history.selectMonth(1999, 12)
  assert.equal(history.selectedPeriod, selected)
})

test('calendar renders month labels, unknown coverage and inspectable cell buttons', async () => {
  const { default: Calendar } = await server.ssrLoadModule(
    '/src/components/common/BurningCalendar.vue',
  )
  const rows = buildCalendarRows(archive.months, 2000, 2000, 'ALL')
  const html = await renderToString(
    createSSRApp({
      render: () =>
        h(Calendar, { rows, maxCount: 10000, selectedPeriod: { year: 2000, month: 11 } }),
    }),
  )
  assert.equal((html.match(/<button /g) ?? []).length, 12)
  assert.equal((html.match(/aria-pressed="true"/g) ?? []).length, 1)
  assert(html.includes('Jan 2000: no records; coverage unverified'))
  assert(html.includes('observed detections'))
})

test('historical details explicitly identify national scope and unchanged daily map', async () => {
  const { default: Calendar } = await server.ssrLoadModule(
    '/src/components/features/HistoricalCalendar.vue',
  )
  const pinia = createPinia()
  useCalendarStore(pinia).selectMonth(2000, 1)
  const app = createSSRApp({ render: () => h(Calendar) })
  app.use(pinia)
  const html = await renderToString(app)
  assert(html.includes('800,480'))
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
