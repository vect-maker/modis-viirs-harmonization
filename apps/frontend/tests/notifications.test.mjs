import { test, before, after } from 'node:test'
import assert from 'node:assert/strict'
import { createServer } from 'vite'
import { createPinia, setActivePinia } from 'pinia'
import { createSSRApp, h } from 'vue'
import { renderToString } from 'vue/server-renderer'

let server, useNotificationStore, NotificationToasts

before(async () => {
  server = await createServer({
    cacheDir: 'node_modules/.vite-notifications-tests',
    server: { middlewareMode: true, hmr: false },
    appType: 'custom',
  })
  ;({ useNotificationStore } = await server.ssrLoadModule('/src/stores/notifications.ts'))
  ;({ default: NotificationToasts } = await server.ssrLoadModule(
    '/src/components/common/NotificationToasts.vue',
  ))
})

after(async () => {
  await server?.close()
})

test('notification store ingests SSE envelopes, deduplicates, ignores heartbeats, and tracks time', async () => {
  setActivePinia(createPinia())
  const store = useNotificationStore()

  const hbResult = store.ingestSSEEvent(
    'heartbeat',
    JSON.stringify({ event_id: 'hb-1', event_type: 'heartbeat', timestamp: '2026-11-15T00:00:00Z' }),
  )
  assert.equal(hbResult, null)
  assert.equal(store.items.length, 0)
  assert.equal(store.lastHeartbeatAt, '2026-11-15T00:00:00Z')

  const envelopePayload = JSON.stringify({
    event_id: 'notif-abc123',
    emitter_service: 'firms-api',
    target_scope: 'all',
    target_id: null,
    event_type: 'notification',
    payload: {
      title: 'Nuevo lote FIRMS',
      message: 'Se ingirieron 24 detecciones.',
      severity: 'success',
      duration_ms: 400,
    },
    timestamp: '2026-11-15T00:01:00Z',
  })

  const id1 = store.ingestSSEEvent('notification', envelopePayload)
  assert.ok(id1)
  assert.equal(store.items.length, 1)
  assert.equal(store.items[0].title, 'Nuevo lote FIRMS')
  assert.equal(store.items[0].severity, 'success')
  assert.equal(store.items[0].emitterService, 'firms-api')

  // Duplicate event_id is ignored
  const dup = store.ingestSSEEvent('notification', envelopePayload)
  assert.equal(dup, null)
  assert.equal(store.items.length, 1)

  // Arbitrary payload structure still works
  const customId = store.ingestSSEEvent(
    'worker.sync',
    JSON.stringify({
      event_id: 'notif-custom1',
      emitter_service: 'worker',
      target_scope: 'all',
      event_type: 'worker.sync',
      payload: { processed: 10 },
      timestamp: '2026-11-15T00:02:00Z',
    }),
  )
  assert.ok(customId)
  assert.equal(store.items.length, 2)
  assert.equal(store.items[1].title, 'worker.sync')

  // Pause keeps second toast, while first toast expires when time advances
  store.pause(customId)
  store.tick(450)
  assert.equal(store.items.length, 1)
  assert.equal(store.items[0].id, customId)

  store.dismiss(customId)
  assert.equal(store.items.length, 0)
})

test('NotificationToasts renders active notifications', async () => {
  const pinia = createPinia()
  setActivePinia(pinia)
  const store = useNotificationStore()
  store.notify({
    title: 'Alerta de prueba',
    message: 'Stream SSE conectado',
    severity: 'warning',
    emitterService: 'firms-api',
    durationMs: 0,
  })

  const app = createSSRApp({ render: () => h(NotificationToasts) })
  app.use(pinia)
  const ssrContext = {}
  await renderToString(app, ssrContext)
  const teleportedHtml = ssrContext.teleports?.body ?? ''
  assert.match(teleportedHtml, /Alerta de prueba/)
  assert.match(teleportedHtml, /Stream SSE conectado/)
  assert.match(teleportedHtml, /firms-api/)
})

test('NotificationToasts shows disconnect popup and badge when SSE stream is lost and clears on reconnect', async () => {
  const pinia = createPinia()
  setActivePinia(pinia)
  const store = useNotificationStore()

  // Initial connecting state should not show disconnect indicators
  store.setConnectionStatus('CLOSED')
  store.setConnectionStatus('CONNECTING')
  assert.equal(store.isStreamDisconnected, false)
  assert.equal(store.items.length, 0)

  // Connected, then lost -> persistent popup + badge
  store.setConnectionStatus('OPEN')
  assert.equal(store.isStreamDisconnected, false)
  store.setConnectionStatus('CLOSED')
  assert.equal(store.isStreamDisconnected, true)
  assert.equal(store.items.length, 1)
  assert.equal(store.items[0].title, 'Backend connection lost')

  // Retry cycles stay disconnected without duplicating the popup
  store.setConnectionStatus('CONNECTING')
  store.setConnectionStatus('CLOSED')
  assert.equal(store.isStreamDisconnected, true)
  assert.equal(store.items.length, 1)

  const app = createSSRApp({ render: () => h(NotificationToasts) })
  app.use(pinia)
  const ssrContext = {}
  await renderToString(app, ssrContext)
  const teleportedHtml = ssrContext.teleports?.body ?? ''
  assert.match(teleportedHtml, /Backend connection lost/)
  assert.match(teleportedHtml, /Backend offline · Reconnecting…/)

  // Reconnect clears disconnected state and replaces popup with restored toast
  store.setConnectionStatus('OPEN')
  assert.equal(store.isStreamDisconnected, false)
  assert.equal(store.items.length, 1)
  assert.equal(store.items[0].title, 'Backend connection restored')
})
