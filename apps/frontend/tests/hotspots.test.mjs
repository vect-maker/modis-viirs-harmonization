import { test, before, after } from 'node:test'
import assert from 'node:assert/strict'
import { createPinia, setActivePinia } from 'pinia'
import { createServer } from 'vite'
import { effectScope, createSSRApp, h } from 'vue'
import { renderToString } from 'vue/server-renderer'
import { aggregateDailyActivity } from '../src/utils/hotspotActivity.ts'
import { hotspotsToCsv, hotspotCsvFilename } from '../src/utils/hotspotCsv.ts'

const detection = (date, instrument = 'MODIS', satellite = 'Aqua') => ({
  latitude: 12.5,
  longitude: -85.5,
  acq_datetime: date,
  instrument,
  satellite,
  confidence_class: 'n',
  confidence: 50,
  frp: 10,
  bright_mir: 300,
  daynight: 'D',
})
let server
let useHotspotsStore
let useHotspotCsvDownload
before(async () => {
  server = await createServer({ server: { middlewareMode: true, hmr: false }, appType: 'custom' })
  ;({ useHotspotsStore } = await server.ssrLoadModule('/src/stores/hotspots.ts'))
  ;({ useHotspotCsvDownload } = await server.ssrLoadModule(
    '/src/composables/useHotspotCsvDownload.ts',
  ))
})
after(async () => {
  await server?.close()
})
function createStore() {
  setActivePinia(createPinia())
  return useHotspotsStore()
}

test('UTC daily aggregation includes leap day, orders buckets and retains days without records', () => {
  const rows = [
    detection('2024-03-01 00:00:00'),
    detection('2024-02-28 23:59:59'),
    detection('2024-03-01 23:59:59'),
  ]
  assert.deepEqual(aggregateDailyActivity(rows, { start: '2024-02-28', end: '2024-03-01' }), [
    { date: '2024-02-28', count: 1 },
    { date: '2024-02-29', count: 0 },
    { date: '2024-03-01', count: 2 },
  ])
  assert.deepEqual(aggregateDailyActivity([], null), [])
})

test('selecting a day changes map results but preserves timeline context', () => {
  const store = createStore()
  store.hotspots = [
    detection('2024-05-23 23:59:59'),
    detection('2024-05-24 00:00:00'),
    detection('2024-05-24 23:59:59', 'VIIRS', 'Suomi-NPP'),
    detection('2024-05-25 00:00:00'),
  ]
  store.setDateRange({ start: '2024-05-24', end: '2024-05-24' })
  assert.equal(store.filteredHotspots.length, 2)
  assert.equal(store.stats.total, 2)
  assert.deepEqual(
    store.dailyActivity.map((day) => day.count),
    [1, 2, 1],
  )
  assert.equal(
    store.dailyActivity.reduce((total, day) => total + day.count, 0),
    4,
  )
  store.setSensor('VIIRS')
  assert.equal(store.stats.total, 1)
  assert.deepEqual(
    store.dailyActivity.map((day) => day.count),
    [0, 1, 0],
  )
  store.setAreaHotspots([])
  assert.equal(store.stats.total, 0)
  assert.deepEqual(
    store.dailyActivity.map((day) => day.count),
    [0, 0, 0],
  )
  store.setDateRange(null)
  assert.equal(store.selectedSensor, 'VIIRS')
  assert.equal(store.stats.total, 0)
  store.setAreaHotspots(null)
  assert.equal(store.stats.total, 1)
})

test('date ranges include both complete UTC boundary days and reject invalid ranges', () => {
  const store = createStore()
  store.hotspots = [
    detection('2024-05-22 23:59:59'),
    detection('2024-05-23 00:00:00'),
    detection('2024-05-31 23:59:59'),
    detection('2024-06-01 00:00:00'),
  ]
  store.setDateRange({ start: '2024-05-23', end: '2024-05-31' })
  assert.deepEqual(
    store.filteredHotspots.map((row) => row.acq_datetime),
    ['2024-05-23 00:00:00', '2024-05-31 23:59:59'],
  )
  const range = store.dateRange
  store.setDateRange({ start: '2024-06-01', end: '2024-05-23' })
  assert.equal(store.dateRange, range)
  store.setDateRange({ start: '2024-02-30', end: '2024-05-23' })
  assert.equal(store.dateRange, range)
})

test('CSV exports only the filtered records, with a UTC heading and CRLF rows', () => {
  const store = createStore()
  store.hotspots = [
    detection('2024-05-23 10:00:00'),
    detection('2024-05-24 23:59:59'),
    detection('2024-05-24 11:00:00', 'VIIRS'),
  ]
  store.setSensor('MODIS')
  store.setDateRange({ start: '2024-05-24', end: '2024-05-24' })
  const csv = hotspotsToCsv(store.filteredHotspots)
  const lines = csv.trimEnd().split('\r\n')
  assert.equal(lines.length - 1, store.stats.total)
  assert(lines[0].includes('acq_datetime_utc'))
  assert(lines[1].includes('2024-05-24 23:59:59'))
  assert(!csv.includes('2024-05-23'))
  assert(!csv.includes('VIIRS'))
  assert(csv.endsWith('\r\n'))
})

test('CSV correctly escapes commas, quotes and embedded newlines', () => {
  const csv = hotspotsToCsv([
    detection('2024-05-24 12:00:00', 'MODIS', 'Aqua, "test"\nsecond line'),
  ])
  assert(csv.includes('"Aqua, ""test""\nsecond line"'))
  assert.equal(hotspotsToCsv([]).trim().split('\n').length, 1)
})

test('export filenames identify the query period, area and sensor', () => {
  assert.equal(
    hotspotCsvFilename({ start: '2024-05-23', end: '2024-05-31' }, 'VIIRS', true),
    'nicaragua-hotspots_selected-area_viirs_2024-05-23_2024-05-31.csv',
  )
  assert.equal(
    hotspotCsvFilename(null, 'ALL', false),
    'nicaragua-hotspots_country_all_all-dates.csv',
  )
})

test('download prepares UTF-8 CSV bytes, uses the requested filename and skips empty results', async () => {
  const scope = effectScope()
  const previousDocument = globalThis.document
  const clicks = []
  let removed = false
  globalThis.document = {
    createElement: () => ({
      href: '',
      download: '',
      click() {
        clicks.push({ href: this.href, filename: this.download })
      },
      remove() {
        removed = true
      },
    }),
    body: { appendChild() {} },
  }
  try {
    const exporter = scope.run(() => useHotspotCsvDownload())
    assert.equal(await exporter.download([], 'empty.csv'), false)
    assert.equal(clicks.length, 0)
    assert.equal(await exporter.download([detection('2024-05-24 23:59:59')], 'query.csv'), true)
    assert.equal(clicks.length, 1)
    assert.equal(clicks[0].filename, 'query.csv')
    assert.equal(removed, true)
    const response = await fetch(clicks[0].href)
    const bytes = new Uint8Array(await response.arrayBuffer())
    assert.deepEqual(Array.from(bytes.subarray(0, 3)), [239, 187, 191])
    const csv = new TextDecoder().decode(bytes)
    assert(csv.includes('2024-05-24 23:59:59'))
    assert.equal(csv.split('\r\n').length, 3)
    assert.equal(exporter.isPreparing.value, false)
  } finally {
    scope.stop()
    if (previousDocument === undefined) delete globalThis.document
    else globalThis.document = previousDocument
  }
})

test('chart exposes every day as a labelled button and highlights only the selected UTC day', async () => {
  const { default: Chart } = await server.ssrLoadModule(
    '/src/components/common/DailyActivityChart.vue',
  )
  const app = createSSRApp({
    render: () =>
      h(Chart, {
        days: [
          { date: '2024-05-23', count: 10 },
          { date: '2024-05-24', count: 0 },
          { date: '2024-05-25', count: 5 },
        ],
        selectedRange: { start: '2024-05-24', end: '2024-05-24' },
      }),
  })
  const html = await renderToString(app)
  assert.equal((html.match(/<button /g) ?? []).length, 3)
  assert.equal((html.match(/aria-pressed="true"/g) ?? []).length, 1)
  assert(html.includes('2024-05-24: 0 detections. Select this day.'))
  assert(html.includes('2024-05-23: 10 detections. Select this day.'))
})

test('CSV control disables export when the active query has no results', async () => {
  const { default: CsvExport } = await server.ssrLoadModule(
    '/src/components/features/HotspotCsvExport.vue',
  )
  const pinia = createPinia()
  const store = useHotspotsStore(pinia)
  store.setAreaHotspots([])
  const app = createSSRApp({ render: () => h(CsvExport) })
  app.use(pinia)
  const html = await renderToString(app)
  assert(html.includes('disabled'))
  assert(html.includes('Download 0 filtered hotspots as CSV'))
})

test('space backdrop is decorative and exposes no keyboard interaction', async () => {
  const { default: Background } = await server.ssrLoadModule(
    '/src/components/common/SpaceBackground.vue',
  )
  const html = await renderToString(
    createSSRApp({ render: () => h(Background, { visible: true }) }),
  )
  assert(html.includes('<canvas'))
  assert(html.includes('aria-hidden="true"'))
  assert(!html.includes('tabindex'))
})

test('fetchHotspots loads hotspots and resolves platform metadata from the API', async () => {
  const previousFetch = globalThis.fetch
  const platformId = '11111111-1111-4111-8111-111111111111'
  const countryId = '22222222-2222-4222-8222-222222222222'
  const hotspotId = '33333333-3333-4333-8333-333333333333'

  globalThis.fetch = async (url) => {
    const href = String(url)
    if (href.includes('/platforms')) {
      return new Response(
        JSON.stringify({
          data: [{ id: platformId, satellite: 'NOAA-20', instrument: 'VIIRS' }],
          total: 1,
          limit: 100,
          offset: 0,
        }),
        { status: 200, headers: { 'Content-Type': 'application/json' } },
      )
    }
    if (href.includes('/hotspots')) {
      return new Response(
        JSON.stringify({
          data: [
            {
              id: hotspotId,
              country_id: countryId,
              platform_id: platformId,
              latitude: 12.5,
              longitude: -85.5,
              acq_datetime: '2024-05-31T18:44:00',
              bright_mir: null,
              confidence: null,
              confidence_class: null,
              frp: 4.5,
              daynight: 'N',
            },
          ],
          total: 1,
          limit: 100,
          offset: 0,
        }),
        { status: 200, headers: { 'Content-Type': 'application/json' } },
      )
    }
    return new Response('Not Found', { status: 404 })
  }

  try {
    const store = createStore()
    await store.fetchHotspots({ limit: 100 })
    assert.equal(store.isLoading, false)
    assert.equal(store.error, null)
    assert.deepEqual(store.hotspots, [
      {
        latitude: 12.5,
        longitude: -85.5,
        acq_datetime: '2024-05-31 18:44:00',
        instrument: 'VIIRS',
        satellite: 'NOAA-20',
        confidence_class: '',
        confidence: 0,
        frp: 4.5,
        bright_mir: 0,
        daynight: 'N',
      },
    ])
  } finally {
    globalThis.fetch = previousFetch
  }
})
