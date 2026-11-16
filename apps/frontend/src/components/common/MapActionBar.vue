<script setup lang="ts">
import { Check, Pentagon, LocateFixed, Trash2, Globe2, X } from '@lucide/vue'
import { useI18n } from 'vue-i18n'
import BaseTooltip from '@/components/ui/BaseTooltip.vue'

const { t } = useI18n()
defineProps<{ hasArea: boolean; isDrawing?: boolean }>()
const emit = defineEmits<{ draw: []; confirm: []; cancel: []; locate: []; clear: []; globe: [] }>()

const actionClass =
  'inline-flex min-h-10 min-w-10 items-center justify-center gap-2 rounded-[7px] px-2.5 py-2 text-xs font-medium whitespace-nowrap text-ink-muted hover:bg-white/[0.04] hover:text-ink-primary focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-focus disabled:cursor-not-allowed disabled:opacity-30 cursor-pointer'
</script>

<template>
  <div class="flex shrink-0 items-center gap-1" role="group" :aria-label="t('map.actions.toolsAria')">
    <template v-if="isDrawing">
      <BaseTooltip :text="t('map.actions.confirmArea')">
        <button
          type="button"
          class="inline-flex min-h-10 min-w-10 items-center justify-center gap-2 rounded-[7px] border border-emerald-400/40 bg-emerald-500/15 px-2.5 py-2 text-xs font-medium whitespace-nowrap text-emerald-300 hover:bg-emerald-500/25 hover:text-ink-primary focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-focus cursor-pointer"
          :aria-label="t('map.actions.confirmArea')"
          @click="emit('confirm')"
        >
          <Check aria-hidden="true" class="h-4 w-4" />
          <span>{{ t('map.actions.confirm') }}</span>
        </button>
      </BaseTooltip>
      <BaseTooltip :text="t('map.actions.cancelDraw')">
        <button
          type="button"
          class="inline-flex min-h-10 min-w-10 items-center justify-center gap-2 rounded-[7px] border border-red-400/40 bg-red-500/10 px-2.5 py-2 text-xs font-medium whitespace-nowrap text-red-300 hover:bg-red-500/20 hover:text-ink-primary focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-focus cursor-pointer"
          :aria-label="t('map.actions.cancelDraw')"
          @click="emit('cancel')"
        >
          <X aria-hidden="true" class="h-4 w-4" />
          <span>{{ t('common.cancel') }}</span>
        </button>
      </BaseTooltip>
    </template>

    <BaseTooltip v-else-if="hasArea" :text="t('map.actions.clearArea')">
      <button
        type="button"
        class="inline-flex min-h-10 min-w-10 items-center justify-center gap-2 rounded-[7px] border border-accent/35 bg-accent/10 px-2.5 py-2 text-xs font-medium whitespace-nowrap text-accent-bright hover:bg-accent/20 hover:text-ink-primary focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-focus cursor-pointer"
        :aria-label="t('map.actions.clearArea')"
        @click="emit('clear')"
      >
        <Trash2 aria-hidden="true" class="h-4 w-4" />
        <span class="sm:hidden">{{ t('map.actions.clearShort') }}</span
        ><span class="hidden sm:inline">{{ t('map.actions.clearFull') }}</span>
      </button>
    </BaseTooltip>

    <BaseTooltip v-else :text="t('map.actions.drawArea')">
      <button
        type="button"
        class="inline-flex min-h-10 min-w-10 items-center justify-center gap-2 rounded-[7px] border border-accent/35 bg-accent/10 px-2.5 py-2 text-xs font-medium whitespace-nowrap text-accent-bright hover:bg-accent/20 hover:text-ink-primary focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-focus cursor-pointer"
        :aria-label="t('map.actions.drawArea')"
        @click="emit('draw')"
      >
        <Pentagon aria-hidden="true" class="h-4 w-4" />
        <span class="sm:hidden">{{ t('map.actions.drawShort') }}</span
        ><span class="hidden sm:inline">{{ t('map.actions.drawFull') }}</span>
      </button>
    </BaseTooltip>

    <BaseTooltip :text="t('map.actions.locate')">
      <button
        type="button"
        :class="actionClass"
        :aria-label="t('map.actions.locateAria')"
        @click="emit('locate')"
      >
        <LocateFixed aria-hidden="true" class="h-4 w-4" />
        <span class="hidden xl:inline">{{ t('map.actions.myLocation') }}</span>
      </button>
    </BaseTooltip>
    <BaseTooltip :text="t('map.actions.globe')">
      <button
        type="button"
        :class="actionClass"
        :aria-label="t('map.actions.globeAria')"
        @click="emit('globe')"
      >
        <Globe2 aria-hidden="true" class="h-4 w-4" />
        <span class="hidden xl:inline">{{ t('map.actions.globeShort') }}</span>
      </button>
    </BaseTooltip>
  </div>
</template>
