import { test, before, after } from 'node:test'
import assert from 'node:assert/strict'
import { createServer } from 'vite'
import { createPinia } from 'pinia'
import { createSSRApp, h } from 'vue'
import { renderToString } from 'vue/server-renderer'

let server, router, LandingView

before(async () => {
  server = await createServer({
    cacheDir: 'node_modules/.vite-landing-tests',
    server: { middlewareMode: true, hmr: false },
    appType: 'custom',
  })
  ;({ default: router } = await server.ssrLoadModule('/src/router/index.ts'))
  ;({ default: LandingView } = await server.ssrLoadModule('/src/views/LandingView.vue'))
})

after(async () => {
  await server?.close()
})

test('router exposes landing page at / and map explorer at /dashboard', () => {
  const routes = router.getRoutes()
  const landing = routes.find((r) => r.path === '/')
  const dashboard = routes.find((r) => r.path === '/dashboard')
  assert.ok(landing, 'Expected / route to exist')
  assert.equal(landing.name, 'landing')
  assert.ok(dashboard, 'Expected /dashboard route to exist')
  assert.equal(dashboard.name, 'dashboard')
})

test('LandingView renders PyroTrace headline and /dashboard links', async () => {
  await router.push('/')
  await router.isReady()
  const app = createSSRApp({ render: () => h(LandingView) })
  app.use(createPinia())
  app.use(router)
  const html = await renderToString(app)
  assert.match(html, /PyroTrace/)
  assert.match(html, /Datos satelitales/)
  assert.match(html, /lang="es"/)
  assert.match(html, /conteos originales, aún sin armonizar/)
  assert.match(html, /AFICIONADOS Y ESTUDIANTES/)
  assert.match(html, /href="\/dashboard"/)
})
