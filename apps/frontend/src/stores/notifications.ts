import { useIntervalFn } from "@vueuse/core";
import { defineStore } from "pinia";
import { computed, ref } from "vue";
import {
  type CreateToastInput,
  type NotificationSeverity,
  type SSEConnectionStatus,
  SSEEventEnvelopeSchema,
  type ToastNotification,
} from "@/types/notifications";

const DEFAULT_DURATION_MS = 5000;
const TICK_INTERVAL_MS = 100;
const MAX_VISIBLE_TOASTS = 5;
const MAX_SEEN_EVENT_IDS = 200;

function normalizeSeverity(raw: unknown): NotificationSeverity {
  if (typeof raw !== "string") return "info";
  switch (raw.trim().toLowerCase()) {
    case "success":
    case "resolved":
      return "success";
    case "warning":
    case "warn":
    case "medium":
    case "high":
      return "warning";
    case "error":
    case "critical":
    case "danger":
      return "error";
    default:
      return "info";
  }
}

function createLocalId(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  return `toast-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

function extractToastFromRecord(
  eventType: string,
  record: Record<string, unknown>,
  emitterService: string,
  timestamp: string,
  eventId?: string,
): CreateToastInput {
  const title =
    typeof record.title === "string" && record.title.trim().length > 0
      ? record.title.trim()
      : eventType;

  const message =
    typeof record.message === "string" && record.message.trim().length > 0
      ? record.message.trim()
      : typeof record.description === "string" && record.description.trim().length > 0
        ? record.description.trim()
        : JSON.stringify(record);

  const durationMs =
    typeof record.duration_ms === "number" && Number.isFinite(record.duration_ms) && record.duration_ms >= 0
      ? record.duration_ms
      : DEFAULT_DURATION_MS;

  return {
    eventId,
    title,
    message,
    severity: normalizeSeverity(record.severity),
    emitterService,
    eventType,
    timestamp,
    durationMs,
    payload: record,
  };
}

export const useNotificationStore = defineStore("notifications", () => {
  const items = ref<ToastNotification[]>([]);
  const connectionStatus = ref<SSEConnectionStatus>("CLOSED");
  const lastEventId = ref<string | null>(null);
  const lastHeartbeatAt = ref<string | null>(null);
  const seenEventIds: string[] = [];

  const hasTimedToasts = computed(() =>
    items.value.some((item) => item.durationMs > 0 && !item.paused),
  );

  function tick(elapsedMs = TICK_INTERVAL_MS): void {
    let hasExpired = false;
    for (const item of items.value) {
      if (item.durationMs <= 0 || item.paused) continue;
      item.remainingMs = Math.max(0, item.remainingMs - elapsedMs);
      if (item.remainingMs === 0) {
        hasExpired = true;
      }
    }

    if (hasExpired) {
      items.value = items.value.filter((item) => item.durationMs <= 0 || item.remainingMs > 0);
    }

    if (!hasTimedToasts.value) {
      pauseTicker();
    }
  }

  const { pause: pauseTicker, resume: resumeTicker } = useIntervalFn(
    () => tick(TICK_INTERVAL_MS),
    TICK_INTERVAL_MS,
    { immediate: false },
  );

  function syncTicker(): void {
    if (hasTimedToasts.value) {
      resumeTicker();
    } else {
      pauseTicker();
    }
  }

  function rememberEventId(eventId: string): boolean {
    if (seenEventIds.includes(eventId)) {
      return false;
    }
    seenEventIds.push(eventId);
    if (seenEventIds.length > MAX_SEEN_EVENT_IDS) {
      seenEventIds.shift();
    }
    lastEventId.value = eventId;
    return true;
  }

  function notify(input: CreateToastInput): string {
    const durationMs =
      typeof input.durationMs === "number" && Number.isFinite(input.durationMs) && input.durationMs >= 0
        ? input.durationMs
        : DEFAULT_DURATION_MS;

    const toast: ToastNotification = {
      id: input.id ?? createLocalId(),
      eventId: input.eventId,
      title: input.title,
      message: input.message,
      severity: input.severity ?? "info",
      emitterService: input.emitterService ?? "frontend",
      eventType: input.eventType ?? "notification",
      timestamp: input.timestamp ?? new Date().toISOString(),
      createdAtMs: Date.now(),
      durationMs,
      remainingMs: durationMs,
      paused: false,
      payload: input.payload ?? {},
    };

    items.value.push(toast);
    if (items.value.length > MAX_VISIBLE_TOASTS) {
      items.value.splice(0, items.value.length - MAX_VISIBLE_TOASTS);
    }

    syncTicker();
    return toast.id;
  }

  function ingestSSEEvent(eventType: string, rawData: string): string | null {
    if (!rawData) return null;

    let parsedJson: unknown;
    try {
      parsedJson = JSON.parse(rawData);
    } catch {
      return notify({
        title: eventType || "Notification",
        message: rawData,
        eventType: eventType || "notification",
        emitterService: "firms-api",
      });
    }

    if (typeof parsedJson !== "object" || parsedJson === null || Array.isArray(parsedJson)) {
      return notify({
        title: eventType || "Notification",
        message: String(parsedJson),
        eventType: eventType || "notification",
        emitterService: "firms-api",
      });
    }

    const envelopeResult = SSEEventEnvelopeSchema.safeParse(parsedJson);
    if (envelopeResult.success) {
      const env = envelopeResult.data;
      const eventIdStr = String(env.event_id);
      if (!rememberEventId(eventIdStr)) {
        return null;
      }

      if (env.event_type === "heartbeat") {
        lastHeartbeatAt.value = env.timestamp;
        return null;
      }

      return notify(
        extractToastFromRecord(
          env.event_type,
          env.payload,
          env.emitter_service,
          env.timestamp,
          eventIdStr,
        ),
      );
    }

    const record = parsedJson as Record<string, unknown>;
    const resolvedType =
      typeof record.event_type === "string" ? record.event_type : eventType || "notification";

    if (resolvedType === "heartbeat") {
      lastHeartbeatAt.value =
        typeof record.timestamp === "string" ? record.timestamp : new Date().toISOString();
      return null;
    }

    const rawEventId = record.event_id;
    const eventIdStr =
      typeof rawEventId === "string" || typeof rawEventId === "number"
        ? String(rawEventId)
        : undefined;
    if (eventIdStr && !rememberEventId(eventIdStr)) {
      return null;
    }

    const timestamp =
      typeof record.created_at === "string"
        ? record.created_at
        : typeof record.timestamp === "string"
          ? record.timestamp
          : new Date().toISOString();

    return notify(
      extractToastFromRecord(resolvedType, record, "firms-api", timestamp, eventIdStr),
    );
  }

  function dismiss(id: string): void {
    items.value = items.value.filter((item) => item.id !== id);
    syncTicker();
  }

  function pause(id: string): void {
    const target = items.value.find((item) => item.id === id);
    if (target) {
      target.paused = true;
      syncTicker();
    }
  }

  function resume(id: string): void {
    const target = items.value.find((item) => item.id === id);
    if (target) {
      target.paused = false;
      syncTicker();
    }
  }

  function clearAll(): void {
    items.value = [];
    syncTicker();
  }

  function setConnectionStatus(status: SSEConnectionStatus): void {
    connectionStatus.value = status;
  }

  return {
    items,
    connectionStatus,
    lastEventId,
    lastHeartbeatAt,
    notify,
    ingestSSEEvent,
    dismiss,
    pause,
    resume,
    tick,
    clearAll,
    setConnectionStatus,
  };
});
