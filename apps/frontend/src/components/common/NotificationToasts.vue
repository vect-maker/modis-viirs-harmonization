<script setup lang="ts">
import { AlertCircle, AlertTriangle, CheckCircle2, Info, X } from "@lucide/vue";
import { storeToRefs } from "pinia";
import { useNotificationStore } from "@/stores/notifications";
import type { NotificationSeverity, ToastNotification } from "@/types/notifications";

const notificationStore = useNotificationStore();
const { items } = storeToRefs(notificationStore);

const SEVERITY_META: Record<
  NotificationSeverity,
  {
    icon: typeof Info;
    borderClass: string;
    iconClass: string;
    progressClass: string;
  }
> = {
  info: {
    icon: Info,
    borderClass: "border-telemetry/40",
    iconClass: "text-telemetry",
    progressClass: "bg-telemetry",
  },
  success: {
    icon: CheckCircle2,
    borderClass: "border-emerald-400/40",
    iconClass: "text-emerald-400",
    progressClass: "bg-emerald-400",
  },
  warning: {
    icon: AlertTriangle,
    borderClass: "border-accent/50",
    iconClass: "text-accent-bright",
    progressClass: "bg-accent",
  },
  error: {
    icon: AlertCircle,
    borderClass: "border-accent-muted/60",
    iconClass: "text-red-400",
    progressClass: "bg-red-400",
  },
};

function progressPercent(item: ToastNotification): number {
  if (item.durationMs <= 0) return 100;
  return Math.max(0, Math.min(100, (item.remainingMs / item.durationMs) * 100));
}

function formatTimestamp(isoString: string): string {
  const parsed = new Date(isoString);
  if (Number.isNaN(parsed.getTime())) return "";
  return parsed.toISOString().slice(11, 19) + " UTC";
}
</script>

<template>
  <Teleport to="body">
    <div
      class="pointer-events-none fixed right-4 bottom-4 z-50 flex w-full max-w-sm flex-col gap-2.5 sm:right-6 sm:bottom-6"
      aria-live="polite"
      aria-atomic="false"
    >
      <TransitionGroup name="toast-slide">
        <article
          v-for="item in items"
          :key="item.id"
          role="status"
          :class="[
            'pointer-events-auto relative overflow-hidden rounded-xl border bg-surface-panel/95 p-3.5 shadow-2xl backdrop-blur-md transition-colors',
            SEVERITY_META[item.severity].borderClass,
          ]"
          @mouseenter="notificationStore.pause(item.id)"
          @mouseleave="notificationStore.resume(item.id)"
        >
          <div class="flex items-start gap-3">
            <component
              :is="SEVERITY_META[item.severity].icon"
              :class="['mt-0.5 size-5 shrink-0', SEVERITY_META[item.severity].iconClass]"
              aria-hidden="true"
            />

            <div class="min-w-0 flex-1">
              <div class="flex items-center justify-between gap-2">
                <h4 class="truncate text-sm font-semibold text-ink-primary">
                  {{ item.title }}
                </h4>
                <button
                  type="button"
                  class="rounded-md p-0.5 text-ink-muted transition hover:bg-surface-elevated hover:text-ink-primary"
                  aria-label="Dismiss notification"
                  @click="notificationStore.dismiss(item.id)"
                >
                  <X class="size-4" aria-hidden="true" />
                </button>
              </div>

              <p class="mt-1 text-xs leading-relaxed text-ink-secondary">
                {{ item.message }}
              </p>

              <div class="mt-2 flex items-center justify-between text-[11px] text-ink-muted">
                <span class="truncate">{{ item.emitterService }}</span>
                <span class="shrink-0 tabular-nums">{{ formatTimestamp(item.timestamp) }}</span>
              </div>
            </div>
          </div>

          <div
            v-if="item.durationMs > 0"
            class="absolute inset-x-0 bottom-0 h-0.5 bg-surface-elevated"
          >
            <div
              :class="['h-full transition-[width] duration-100 ease-linear', SEVERITY_META[item.severity].progressClass]"
              :style="{ width: `${progressPercent(item)}%` }"
            />
          </div>
        </article>
      </TransitionGroup>
    </div>
  </Teleport>
</template>

<style scoped>
.toast-slide-enter-active,
.toast-slide-leave-active {
  transition:
    opacity 0.2s ease,
    transform 0.2s ease;
}

.toast-slide-enter-from,
.toast-slide-leave-to {
  opacity: 0;
  transform: translateY(10px) scale(0.98);
}
</style>
