<script setup lang="ts">
import { computed } from 'vue'
import { Loader2 } from '@lucide/vue'
import { useI18n } from 'vue-i18n'
import { useLocaleFormatters } from '@/i18n'

const { t } = useI18n()
const { formatInt } = useLocaleFormatters()

const props = defineProps<{
  visible: boolean
  progress?: { loaded: number; total: number } | null
}>()

const percent = computed(() => {
  if (!props.progress || props.progress.total <= 0) return null
  return Math.min(100, Math.round((props.progress.loaded / props.progress.total) * 100))
})
</script>

<template>
  <Transition
    enter-active-class="transition-opacity duration-200"
    enter-from-class="opacity-0"
    leave-active-class="transition-opacity duration-200"
    leave-to-class="opacity-0"
  >
    <div
      v-if="visible"
      role="status"
      aria-live="polite"
      :aria-label="t('dashboard.loading.aria')"
      class="fixed inset-0 z-50 flex items-center justify-center bg-surface-base/65 px-4 backdrop-blur-md"
    >
      <div
        class="w-full max-w-sm rounded-2xl border border-border-strong bg-surface-panel/95 p-6 text-ink-primary shadow-[0_16px_48px_#0008]"
      >
        <div class="flex items-center gap-3">
          <Loader2 aria-hidden="true" class="h-5 w-5 shrink-0 animate-spin text-accent" />
          <div class="min-w-0 flex-1">
            <p class="text-sm font-semibold">{{ t('dashboard.loading.title') }}</p>
            <p class="mt-0.5 text-xs text-ink-muted">
              <template v-if="progress && percent !== null">
                {{
                  t('dashboard.loading.progress', {
                    loaded: formatInt(progress.loaded),
                    total: formatInt(progress.total),
                    percent,
                  })
                }}
              </template>
              <template v-else>{{ t('dashboard.loading.fetching') }}</template>
            </p>
          </div>
        </div>

        <div class="mt-4 h-1.5 w-full overflow-hidden rounded-full bg-white/10">
          <div
            v-if="percent !== null"
            class="h-full rounded-full bg-accent transition-[width] duration-200"
            :style="{ width: `${percent}%` }"
          />
          <div
            v-else
            class="h-full w-1/2 animate-pulse rounded-full bg-accent/80"
          />
        </div>
      </div>
    </div>
  </Transition>
</template>
