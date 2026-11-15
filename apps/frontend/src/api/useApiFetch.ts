import { createFetch } from "@vueuse/core";
import { ApiErrorPayloadSchema } from "@/api/modules/shared/schemas";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "/api";

function normalizeHeaders(headersInit: HeadersInit | undefined): Record<string, string> {
  if (!headersInit) return {};
  if (headersInit instanceof Headers) {
    return Object.fromEntries(headersInit.entries());
  }
  if (Array.isArray(headersInit)) {
    return Object.fromEntries(headersInit);
  }
  return { ...headersInit };
}

export function buildPaginationQueryString(params?: { limit?: number; offset?: number }): string {
  const queryParams = new URLSearchParams();
  if (params?.limit !== undefined) {
    queryParams.append("limit", params.limit.toString());
  }
  if (params?.offset !== undefined) {
    queryParams.append("offset", params.offset.toString());
  }
  const qs = queryParams.toString();
  return qs ? `?${qs}` : "";
}

export const useApiFetch = createFetch({
  baseUrl: API_BASE_URL,
  options: {
    updateDataOnError: true,

    beforeFetch({ options }) {
      const headers = normalizeHeaders(options.headers);
      if (!headers["Content-Type"]) {
        headers["Content-Type"] = "application/json";
      }
      options.headers = headers;
      return { options };
    },

    onFetchError(ctx) {
      if (ctx.data) {
        const parsed = ApiErrorPayloadSchema.safeParse(ctx.data);
        if (parsed.success) {
          if ("message" in parsed.data) {
            ctx.error = new Error(parsed.data.message);
          } else if (typeof parsed.data.detail === "string") {
            ctx.error = new Error(parsed.data.detail);
          } else {
            const messages = parsed.data.detail.map((item) => item.msg).join("; ");
            if (messages) {
              ctx.error = new Error(messages);
            }
          }
        }
      }

      return ctx;
    },
  },
  fetchOptions: {
    mode: "cors",
    credentials: "include",
  },
});
