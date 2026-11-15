import { useEventSource } from "@vueuse/core";
import { watch } from "vue";
import { useNotificationStore } from "@/stores/notifications";

const SSE_EVENTS = [
  "notification",
  "hotspot_alert",
  "hotspot_updated",
  "hotspot_resolved",
  "hotspot_dismissed",
  "heartbeat",
] as const;

function buildStreamUrl(): string {
  const baseUrl = (import.meta.env.VITE_API_BASE_URL || "/api").replace(/\/+$/, "");
  const streamPath = `${baseUrl}/alerts/stream`;
  const token = import.meta.env.VITE_ALERT_STREAM_TOKEN;
  if (typeof token === "string" && token.trim().length > 0) {
    const separator = streamPath.includes("?") ? "&" : "?";
    return `${streamPath}${separator}token=${encodeURIComponent(token.trim())}`;
  }
  return streamPath;
}

export function useNotificationStream() {
  const notificationStore = useNotificationStore();

  if (typeof window === "undefined" || typeof EventSource === "undefined") {
    return {
      status: notificationStore.connectionStatus,
      close: () => {},
      open: () => {},
    };
  }

  const { status, event, data, close, open } = useEventSource(
    buildStreamUrl(),
    [...SSE_EVENTS],
    {
      autoReconnect: {
        retries: -1,
        delay: 3000,
      },
    },
  );

  watch(
    status,
    (nextStatus) => {
      notificationStore.setConnectionStatus(nextStatus);
    },
    { immediate: true },
  );

  watch(data, (rawData) => {
    if (!rawData) return;
    notificationStore.ingestSSEEvent(event.value ?? "notification", rawData);
  });

  return {
    status,
    close,
    open,
  };
}
