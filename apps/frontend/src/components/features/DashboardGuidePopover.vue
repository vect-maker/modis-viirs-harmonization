<script setup lang="ts">
import { computed } from 'vue'
import { BookOpen } from '@lucide/vue'
import { PopoverContent, PopoverPortal, PopoverRoot, PopoverTrigger } from 'reka-ui'
import { useI18n } from 'vue-i18n'
import DashboardGuideDiagram, {
  type GuideDiagramVariant,
} from '@/components/common/DashboardGuideDiagram.vue'

const { t } = useI18n()

const variants: GuideDiagramVariant[] = ['layers', 'aoi', 'timeline', 'stats']
const GUIDE_CARDS = computed(() =>
  variants.map((variant, i) => ({
    variant,
    title: t(`dashboard.guide.cards.${i}.title`),
    description: t(`dashboard.guide.cards.${i}.description`),
  })),
)
</script>

<template>
  <PopoverRoot>
    <PopoverTrigger as-child>
      <button
        type="button"
        :aria-label="t('dashboard.guide.openAria')"
        class="inline-flex min-h-10 cursor-pointer items-center gap-2 rounded-lg border border-border-subtle bg-surface-raised px-3 py-2 text-[13px] font-medium text-ink-secondary transition hover:border-border-strong hover:text-ink-primary focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus"
      >
        <BookOpen aria-hidden="true" class="h-3.5 w-3.5 text-accent-bright" />
        <span class="hidden sm:inline">{{ t('dashboard.guide.button') }}</span>
      </button>
    </PopoverTrigger>

    <PopoverPortal>
      <PopoverContent
        side="bottom"
        align="end"
        :side-offset="10"
        :collision-padding="16"
        class="z-50 w-[min(36rem,calc(100vw-2rem))] rounded-2xl border border-border-strong bg-surface-panel/95 p-4 text-xs text-ink-primary shadow-2xl backdrop-blur-md"
      >
        <div class="mb-3 flex items-center justify-between gap-2">
          <div>
            <h2 class="text-sm font-semibold text-ink-primary">{{ t('dashboard.guide.title') }}</h2>
            <p class="text-[11px] text-ink-muted">
              {{ t('dashboard.guide.subtitle') }}
            </p>
          </div>
        </div>

        <div class="grid grid-cols-1 gap-2.5 sm:grid-cols-2">
          <div
            v-for="card in GUIDE_CARDS"
            :key="card.variant"
            class="rounded-xl border border-border-subtle bg-surface-base/75 p-2.5"
          >
            <DashboardGuideDiagram :variant="card.variant" />
            <p class="mt-2 text-xs font-semibold text-ink-primary">{{ card.title }}</p>
            <p class="mt-0.5 text-[11px] leading-snug text-ink-secondary">{{ card.description }}</p>
          </div>
        </div>
      </PopoverContent>
    </PopoverPortal>
  </PopoverRoot>
</template>
