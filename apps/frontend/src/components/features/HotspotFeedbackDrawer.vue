<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { storeToRefs } from 'pinia'
import {
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogOverlay,
  DialogPortal,
  DialogRoot,
  DialogTitle,
  Label,
  RadioGroupIndicator,
  RadioGroupItem,
  RadioGroupRoot,
} from 'reka-ui'
import BaseSelect from '@/components/ui/BaseSelect.vue'
import {
  AlertCircle,
  CheckCircle2,
  Loader2,
  LogIn,
  MessageSquare,
  ShieldCheck,
  Trash2,
  X,
} from '@lucide/vue'
import type { FeedbackClassification, FeedbackSeverity, HotspotResponse } from '@/api'
import { useAuthStore } from '@/stores/auth'
import { useFeedbackStore } from '@/stores/feedback'
import {
  CLASSIFICATION_META_MAP,
  FEEDBACK_CLASSIFICATIONS,
  FEEDBACK_SEVERITIES,
} from '@/utils/feedbackMeta'

const props = defineProps<{
  open: boolean
  hotspot: HotspotResponse | null
}>()

const emit = defineEmits<{
  (e: 'update:open', value: boolean): void
}>()

const route = useRoute()
const authStore = useAuthStore()
const feedbackStore = useFeedbackStore()

const { isAuthenticated } = storeToRefs(authStore)
const { activeList, isLoadingList, isSubmitting, error, summariesByHotspotId } =
  storeToRefs(feedbackStore)

type SeverityOption = FeedbackSeverity | 'unspecified'

const SEVERITY_OPTIONS: Array<{ value: SeverityOption; label: string }> = [
  { value: 'unspecified', label: 'Unspecified' },
  ...FEEDBACK_SEVERITIES,
]

const classification = ref<FeedbackClassification>('confirmed_wildfire')
const severity = ref<SeverityOption>('unspecified')
const comment = ref('')
const statusMessage = ref<string | null>(null)

const summary = computed(() => {
  if (activeList.value?.summary) return activeList.value.summary
  if (props.hotspot) return summariesByHotspotId.value[props.hotspot.id] ?? null
  return null
})

const consensusMeta = computed(() => {
  const cls = summary.value?.consensus
  return cls ? CLASSIFICATION_META_MAP[cls] : null
})

const myFeedback = computed(() => activeList.value?.my_feedback ?? null)
const feedbackItems = computed(() => activeList.value?.items.data ?? [])

function syncFormFromMyFeedback() {
  if (myFeedback.value) {
    classification.value = myFeedback.value.classification
    severity.value = myFeedback.value.severity ?? 'unspecified'
    comment.value = myFeedback.value.comment ?? ''
  } else {
    classification.value = 'confirmed_wildfire'
    severity.value = 'unspecified'
    comment.value = ''
  }
}

watch(
  () => [props.hotspot?.id, myFeedback.value?.id, myFeedback.value?.updated_at],
  () => {
    syncFormFromMyFeedback()
  },
  { immediate: true },
)

watch(
  () => props.hotspot?.id,
  () => {
    statusMessage.value = null
  },
)

function handleOpenChange(nextOpen: boolean) {
  emit('update:open', nextOpen)
}

async function handleSubmit() {
  if (!props.hotspot) return
  statusMessage.value = null
  try {
    await feedbackStore.submitFeedback(props.hotspot.id, {
      classification: classification.value,
      severity: severity.value === 'unspecified' ? null : severity.value,
      comment: comment.value.trim() ? comment.value.trim() : null,
    })
    statusMessage.value = myFeedback.value
      ? 'Your ground-truth report was saved.'
      : 'Feedback submitted.'
  } catch {
    // Error state is populated on feedbackStore.error
  }
}

async function handleDelete() {
  if (!props.hotspot) return
  statusMessage.value = null
  try {
    await feedbackStore.deleteMyFeedback(props.hotspot.id)
    statusMessage.value = 'Your feedback report was removed.'
  } catch {
    // Error state is populated on feedbackStore.error
  }
}

function formatDateTime(iso: string): string {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  return d.toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}
</script>

<template>
  <DialogRoot :open="open" @update:open="handleOpenChange">
    <DialogPortal>
      <DialogOverlay
        class="fixed inset-0 z-50 bg-black/55 backdrop-blur-[2px] data-[state=open]:animate-in data-[state=closed]:animate-out"
      />
      <DialogContent
        class="fixed inset-y-0 right-0 z-50 flex w-full max-w-md flex-col border-l border-border-subtle bg-surface-base text-ink-primary shadow-2xl focus:outline-none"
      >
        <header class="flex items-start justify-between gap-3 border-b border-border-subtle px-5 py-4">
          <div class="min-w-0">
            <DialogTitle class="flex items-center gap-2 text-base font-semibold text-ink-primary">
              <ShieldCheck class="size-4 shrink-0 text-amber-400" aria-hidden="true" />
              Ground-Truth Feedback
            </DialogTitle>
            <DialogDescription v-if="hotspot" class="mt-1 font-mono text-xs text-ink-muted">
              {{ hotspot.latitude.toFixed(4) }}, {{ hotspot.longitude.toFixed(4) }} · FRP
              {{ hotspot.frp != null ? `${hotspot.frp.toFixed(1)} MW` : '—' }} ·
              {{ formatDateTime(hotspot.acq_datetime) }}
            </DialogDescription>
          </div>
          <DialogClose
            class="rounded-md p-1.5 text-ink-muted transition-colors hover:bg-surface-elevated hover:text-ink-primary"
            aria-label="Close feedback drawer"
          >
            <X class="size-4" />
          </DialogClose>
        </header>

        <div class="flex-1 space-y-5 overflow-y-auto px-5 py-4">
          <!-- Consensus & Summary Counts -->
          <section class="rounded-lg border border-border-subtle bg-surface-elevated/60 p-3.5">
            <div class="flex items-center justify-between gap-2">
              <span class="text-xs font-medium uppercase tracking-wider text-ink-muted">
                Consensus
              </span>
              <span class="font-mono text-xs text-ink-muted tabular-nums">
                {{ summary?.total_reports ?? 0 }}
                {{ (summary?.total_reports ?? 0) === 1 ? 'report' : 'reports' }}
              </span>
            </div>

            <div class="mt-2 flex flex-wrap items-center gap-2">
              <span
                v-if="consensusMeta"
                :class="[
                  'rounded-full border px-2.5 py-0.5 text-xs font-medium',
                  consensusMeta.badgeClass,
                ]"
              >
                {{ consensusMeta.label }}
              </span>
              <span
                v-else
                class="rounded-full border border-border-subtle bg-surface-base px-2.5 py-0.5 text-xs font-medium text-ink-muted"
              >
                Unverified
              </span>
            </div>

            <div v-if="summary && summary.total_reports > 0" class="mt-3 flex flex-wrap gap-1.5">
              <span
                v-for="item in FEEDBACK_CLASSIFICATIONS"
                :key="item.value"
                v-show="(summary.counts[item.value] ?? 0) > 0"
                class="inline-flex items-center gap-1 rounded-md border border-border-subtle bg-surface-base px-2 py-0.5 text-[11px] text-ink-secondary"
              >
                <span>{{ item.label }}</span>
                <span class="font-mono font-semibold text-ink-primary tabular-nums">
                  {{ summary.counts[item.value] ?? 0 }}
                </span>
              </span>
            </div>
          </section>

          <!-- Auth-gated Submission Form -->
          <section class="rounded-lg border border-border-subtle bg-surface-elevated/40 p-4">
            <h3 class="text-xs font-medium uppercase tracking-wider text-ink-muted">
              {{ myFeedback ? 'Your Report' : 'Submit Verification' }}
            </h3>

            <div v-if="!isAuthenticated" class="mt-3 space-y-3">
              <p class="text-xs leading-relaxed text-ink-secondary">
                Sign in to classify this hotspot, report severity, or add field observation notes.
              </p>
              <RouterLink
                :to="{ name: 'login', query: { redirect: route.fullPath } }"
                class="inline-flex w-full items-center justify-center gap-2 rounded-md bg-amber-500 px-3.5 py-2 text-xs font-semibold text-slate-950 transition-colors hover:bg-amber-400"
              >
                <LogIn class="size-3.5" aria-hidden="true" />
                Sign in to submit feedback
              </RouterLink>
            </div>

            <form v-else class="mt-3 space-y-4" @submit.prevent="handleSubmit">
              <div class="space-y-2">
                <Label class="block text-xs font-medium text-ink-secondary">
                  Classification
                </Label>
                <RadioGroupRoot
                  v-model="classification"
                  aria-label="Hotspot classification"
                  class="grid grid-cols-1 gap-2 sm:grid-cols-2"
                >
                  <RadioGroupItem
                    v-for="item in FEEDBACK_CLASSIFICATIONS"
                    :key="item.value"
                    :value="item.value"
                    :class="[
                      'group flex min-h-9 cursor-pointer items-center gap-2 rounded-lg border px-3 py-2 text-left text-xs font-medium transition-colors duration-150 focus-visible:outline-2 focus-visible:outline-focus',
                      classification === item.value
                        ? item.badgeClass
                        : 'border-border-subtle bg-surface-input text-ink-secondary hover:border-border-strong hover:text-ink-primary',
                    ]"
                  >
                    <span
                      class="flex size-3.5 shrink-0 items-center justify-center rounded-full border border-current/50"
                    >
                      <RadioGroupIndicator class="size-1.5 rounded-full bg-current" />
                    </span>
                    <span class="truncate">{{ item.label }}</span>
                  </RadioGroupItem>
                </RadioGroupRoot>
              </div>

              <div class="space-y-1.5">
                <Label for="feedback-severity" class="block text-xs font-medium text-ink-secondary">
                  Severity (optional)
                </Label>
                <BaseSelect
                  v-model="severity"
                  :options="SEVERITY_OPTIONS"
                  label="Severity"
                  class="w-full"
                />
              </div>

              <div class="space-y-1.5">
                <div class="flex items-center justify-between gap-2">
                  <Label for="feedback-comment" class="block text-xs font-medium text-ink-secondary">
                    Field Notes (optional)
                  </Label>
                  <span class="font-mono text-[10px] text-ink-muted tabular-nums">
                    {{ comment.length }} / 1000
                  </span>
                </div>
                <textarea
                  id="feedback-comment"
                  v-model="comment"
                  rows="3"
                  maxlength="1000"
                  placeholder="Describe visible smoke, containment status, or false-positive source..."
                  class="w-full resize-y rounded-lg border border-border-subtle bg-surface-input px-3 py-2 text-xs text-ink-primary placeholder:text-ink-muted transition-colors duration-150 hover:border-border-strong focus:border-border-strong focus-visible:outline-2 focus-visible:outline-focus"
                />
              </div>

              <div
                v-if="statusMessage"
                class="flex items-center gap-2 rounded-md border border-emerald-500/30 bg-emerald-500/10 px-3 py-2 text-xs text-emerald-300"
              >
                <CheckCircle2 class="size-3.5 shrink-0" aria-hidden="true" />
                <span>{{ statusMessage }}</span>
              </div>

              <div
                v-if="error"
                class="flex items-center gap-2 rounded-md border border-red-500/30 bg-red-500/10 px-3 py-2 text-xs text-red-300"
              >
                <AlertCircle class="size-3.5 shrink-0" aria-hidden="true" />
                <span>{{ error }}</span>
              </div>

              <div class="flex items-center gap-2 pt-1">
                <button
                  type="submit"
                  :disabled="isSubmitting || !hotspot"
                  class="inline-flex flex-1 items-center justify-center gap-1.5 rounded-md bg-amber-500 px-3 py-2 text-xs font-semibold text-slate-950 transition-colors hover:bg-amber-400 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  <Loader2 v-if="isSubmitting" class="size-3.5 animate-spin" aria-hidden="true" />
                  {{ myFeedback ? 'Update Feedback' : 'Submit Feedback' }}
                </button>

                <button
                  v-if="myFeedback"
                  type="button"
                  :disabled="isSubmitting || !hotspot"
                  class="inline-flex items-center justify-center gap-1 rounded-md border border-red-500/40 bg-red-500/10 px-2.5 py-2 text-xs font-medium text-red-300 transition-colors hover:bg-red-500/20 disabled:cursor-not-allowed disabled:opacity-50"
                  title="Delete your feedback"
                  @click="handleDelete"
                >
                  <Trash2 class="size-3.5" aria-hidden="true" />
                  Delete
                </button>
              </div>
            </form>
          </section>

          <!-- Community Reports Feed -->
          <section class="space-y-2.5">
            <div class="flex items-center justify-between">
              <h3 class="flex items-center gap-1.5 text-xs font-medium uppercase tracking-wider text-ink-muted">
                <MessageSquare class="size-3.5" aria-hidden="true" />
                Recent Reports
              </h3>
            </div>

            <div
              v-if="isLoadingList && !activeList"
              class="flex items-center justify-center gap-2 py-6 text-xs text-ink-muted"
            >
              <Loader2 class="size-4 animate-spin" aria-hidden="true" />
              Loading reports...
            </div>

            <p
              v-else-if="feedbackItems.length === 0"
              class="rounded-lg border border-dashed border-border-subtle px-4 py-5 text-center text-xs text-ink-muted"
            >
              No ground-truth reports yet for this hotspot.
            </p>

            <ul v-else class="space-y-2">
              <li
                v-for="entry in feedbackItems"
                :key="entry.id"
                class="rounded-lg border border-border-subtle bg-surface-elevated/40 p-3"
              >
                <div class="flex items-center justify-between gap-2">
                  <div class="flex min-w-0 items-center gap-1.5">
                    <span class="truncate text-xs font-semibold text-ink-primary">
                      {{ entry.username }}
                    </span>
                    <span
                      class="rounded bg-surface-base px-1.5 py-0.5 font-mono text-[10px] text-ink-muted"
                    >
                      {{ entry.user_role }}
                    </span>
                  </div>
                  <span class="shrink-0 font-mono text-[10px] text-ink-muted">
                    {{ formatDateTime(entry.updated_at) }}
                  </span>
                </div>

                <div class="mt-2 flex flex-wrap items-center gap-1.5">
                  <span
                    :class="[
                      'rounded-full border px-2 py-0.5 text-[10px] font-medium',
                      CLASSIFICATION_META_MAP[entry.classification].badgeClass,
                    ]"
                  >
                    {{ CLASSIFICATION_META_MAP[entry.classification].label }}
                  </span>
                  <span
                    v-if="entry.severity"
                    class="rounded-full border border-border-subtle bg-surface-base px-2 py-0.5 text-[10px] font-medium capitalize text-ink-secondary"
                  >
                    {{ entry.severity }}
                  </span>
                </div>

                <p v-if="entry.comment" class="mt-2 text-xs leading-relaxed text-ink-secondary">
                  {{ entry.comment }}
                </p>
              </li>
            </ul>
          </section>
        </div>
      </DialogContent>
    </DialogPortal>
  </DialogRoot>
</template>
