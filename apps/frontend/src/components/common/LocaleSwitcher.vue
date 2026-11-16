<script setup lang="ts">
import { Globe } from '@lucide/vue'
import { useI18n } from 'vue-i18n'
import { SUPPORTED_LOCALES, useAppLocale, type AppLocale } from '@/i18n'

withDefaults(
  defineProps<{
    variant?: 'landing' | 'dashboard'
  }>(),
  {
    variant: 'dashboard',
  },
)

const { t } = useI18n()
const { locale, isLoadingLocale, setLocale } = useAppLocale()

function selectLocale(next: AppLocale) {
  if (next === locale.value) return
  void setLocale(next)
}
</script>

<template>
  <div
    role="group"
    :aria-label="t('nav.languageLabel')"
    :class="
      variant === 'landing'
        ? 'inline-flex items-center gap-1 rounded-lg border border-white/10 bg-white/[0.04] p-0.5 text-[12px] font-semibold'
        : 'inline-flex min-h-10 items-center gap-1 rounded-lg border border-border-subtle bg-surface-raised p-1 text-[12px] font-semibold'
    "
  >
    <Globe
      :size="14"
      aria-hidden="true"
      :class="variant === 'landing' ? 'ml-1.5 mr-0.5 text-white/60' : 'ml-1.5 mr-0.5 text-ink-muted'"
    />
    <button
      v-for="lang in SUPPORTED_LOCALES"
      :key="lang"
      type="button"
      :disabled="isLoadingLocale"
      :aria-pressed="locale === lang"
      :aria-label="lang === 'en' ? t('nav.switchToEnglish') : t('nav.switchToSpanish')"
      :class="[
        'cursor-pointer rounded-md px-2 py-1 uppercase tracking-wider transition focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-focus',
        locale === lang
          ? variant === 'landing'
            ? 'bg-amber-400 text-[#0b0f14]'
            : 'bg-accent text-surface-base'
          : variant === 'landing'
            ? 'text-white/70 hover:text-white'
            : 'text-ink-muted hover:text-ink-primary',
      ]"
      @click="selectLocale(lang)"
    >
      {{ lang }}
    </button>
  </div>
</template>
