import { computed, shallowRef } from 'vue'
import { createI18n } from 'vue-i18n'
import { usePreferredLanguages, useStorage } from '@vueuse/core'
import en from './locales/en.json'

export type AppLocale = 'en' | 'es'

export const SUPPORTED_LOCALES: readonly AppLocale[] = ['en', 'es'] as const
const STORAGE_KEY = 'pyrotrace-locale'

const loadedLocales = new Set<AppLocale>(['en'])
const isLoadingLocale = shallowRef(false)

function detectPreferredLocale(): AppLocale {
  if (typeof navigator === 'undefined') return 'en'
  const preferred = usePreferredLanguages()
  const match = preferred.value.find((lang) => {
    const base = lang.toLowerCase().split('-')[0]
    return base === 'es' || base === 'en'
  })
  return match?.toLowerCase().startsWith('es') ? 'es' : 'en'
}

function getStoredLocale(): AppLocale {
  const stored = useStorage<string>(STORAGE_KEY, detectPreferredLocale())
  return stored.value === 'es' ? 'es' : 'en'
}

export const i18n = createI18n({
  legacy: false,
  locale: 'en',
  fallbackLocale: 'en',
  messages: { en } as Record<string, typeof en>,
})

function syncDocumentMetadata(locale: AppLocale) {
  if (typeof document === 'undefined') return
  document.documentElement.lang = locale
  const title = i18n.global.t('meta.title')
  if (title && title !== 'meta.title') {
    document.title = title
  }
  const desc = i18n.global.t('meta.description')
  const metaDesc = document.querySelector('meta[name="description"]')
  if (metaDesc && desc && desc !== 'meta.description') {
    metaDesc.setAttribute('content', desc)
  }
}

async function ensureLocaleLoaded(locale: AppLocale): Promise<void> {
  if (loadedLocales.has(locale)) return
  isLoadingLocale.value = true
  try {
    if (locale === 'es') {
      const mod = await import('./locales/es.json')
      i18n.global.setLocaleMessage('es', mod.default)
      loadedLocales.add('es')
    }
  } finally {
    isLoadingLocale.value = false
  }
}

export async function setAppLocale(next: AppLocale): Promise<void> {
  await ensureLocaleLoaded(next)
  i18n.global.locale.value = next
  const stored = useStorage<AppLocale>(STORAGE_KEY, next)
  stored.value = next
  syncDocumentMetadata(next)
}

export async function initI18nLocale(): Promise<void> {
  const initial = getStoredLocale()
  await setAppLocale(initial)
}

export function useAppLocale() {
  const locale = computed<AppLocale>({
    get: () => (i18n.global.locale.value === 'es' ? 'es' : 'en'),
    set: (next) => {
      void setAppLocale(next)
    },
  })

  return {
    locale,
    isSpanish: computed(() => locale.value === 'es'),
    isLoadingLocale,
    setLocale: setAppLocale,
  }
}

export function useLocaleFormatters() {
  const { locale } = useAppLocale()

  const bcp47Locale = computed(() => (locale.value === 'es' ? 'es-NI' : 'en-US'))

  const intFormatter = computed(
    () => new Intl.NumberFormat(bcp47Locale.value, { maximumFractionDigits: 0 }),
  )
  const decimalFormatter = computed(
    () => new Intl.NumberFormat(bcp47Locale.value, { maximumFractionDigits: 1 }),
  )
  const compactFormatter = computed(
    () =>
      new Intl.NumberFormat(bcp47Locale.value, {
        notation: 'compact',
        maximumFractionDigits: 1,
      }),
  )

  return {
    locale,
    bcp47Locale,
    formatInt: (value: number) => intFormatter.value.format(value),
    formatDecimal: (value: number) => decimalFormatter.value.format(value),
    formatCompact: (value: number) => compactFormatter.value.format(value),
  }
}
