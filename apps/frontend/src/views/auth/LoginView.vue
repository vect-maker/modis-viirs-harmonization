<script setup lang="ts">
import { ArrowLeft, LogIn } from "@lucide/vue";
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import PyroTraceLogo from "@/components/common/PyroTraceLogo.vue";
import { useAuthStore } from "@/stores/auth";

const route = useRoute();
const router = useRouter();
const authStore = useAuthStore();

const email = ref("");
const password = ref("");
const localError = ref<string | null>(null);

const justRegistered = computed(() => route.query.registered === "1");

onMounted(() => {
  authStore.clearError();
  if (typeof route.query.email === "string" && route.query.email.trim()) {
    email.value = route.query.email.trim();
  }
});

async function handleSubmit() {
  localError.value = null;
  try {
    await authStore.login({
      email: email.value.trim(),
      password: password.value,
    });
    const redirectTarget =
      typeof route.query.redirect === "string" && route.query.redirect.startsWith("/")
        ? route.query.redirect
        : { name: "dashboard" };
    await router.push(redirectTarget);
  } catch (err) {
    localError.value = err instanceof Error ? err.message : "Unable to sign in";
  }
}
</script>

<template>
  <div class="flex min-h-screen flex-col bg-surface-base text-ink-primary">
    <header class="border-b border-border-subtle bg-surface-base/90 px-6 py-4">
      <div class="mx-auto flex max-w-5xl items-center justify-between">
        <RouterLink :to="{ name: 'landing' }" class="inline-flex items-center">
          <PyroTraceLogo class="h-8 w-auto" />
        </RouterLink>
        <RouterLink
          :to="{ name: 'dashboard' }"
          class="inline-flex items-center gap-1.5 text-xs font-medium text-ink-muted transition hover:text-ink-primary"
        >
          <ArrowLeft aria-hidden="true" class="h-3.5 w-3.5" />
          <span>Back to Dashboard</span>
        </RouterLink>
      </div>
    </header>

    <main class="flex flex-1 items-center justify-center px-4 py-12">
      <div
        class="w-full max-w-md rounded-2xl border border-border-subtle bg-surface-raised p-8 shadow-2xl"
      >
        <div class="mb-6">
          <h1 class="text-xl font-bold tracking-tight text-ink-primary">Sign in to PyroTrace</h1>
          <p class="mt-1 text-xs text-ink-muted">
            Access your analyst profile and submit ground-truth feedback on satellite hotspots.
          </p>
        </div>

        <div
          v-if="justRegistered"
          role="status"
          class="mb-4 rounded-lg border border-emerald-500/30 bg-emerald-950/40 px-3.5 py-2.5 text-xs text-emerald-200"
        >
          Account created successfully. Sign in with your credentials to continue.
        </div>

        <div
          v-if="localError || authStore.error"
          role="alert"
          class="mb-4 rounded-lg border border-red-500/30 bg-red-950/40 px-3.5 py-2.5 text-xs text-red-200"
        >
          {{ localError || authStore.error }}
        </div>

        <form class="space-y-4" @submit.prevent="handleSubmit">
          <div>
            <label for="login-email" class="mb-1.5 block text-xs font-medium text-ink-secondary">
              Email address
            </label>
            <input
              id="login-email"
              v-model="email"
              type="email"
              autocomplete="email"
              required
              placeholder="analyst@example.org"
              class="w-full rounded-lg border border-border-subtle bg-surface-base px-3.5 py-2.5 text-sm text-ink-primary placeholder:text-ink-muted/60 focus:border-accent focus:outline-none"
            />
          </div>

          <div>
            <label for="login-password" class="mb-1.5 block text-xs font-medium text-ink-secondary">
              Password
            </label>
            <input
              id="login-password"
              v-model="password"
              type="password"
              autocomplete="current-password"
              required
              placeholder="••••••••"
              class="w-full rounded-lg border border-border-subtle bg-surface-base px-3.5 py-2.5 text-sm text-ink-primary placeholder:text-ink-muted/60 focus:border-accent focus:outline-none"
            />
          </div>

          <button
            type="submit"
            :disabled="authStore.isSubmitting"
            class="inline-flex min-h-11 w-full cursor-pointer items-center justify-center gap-2 rounded-lg bg-accent px-4 py-2.5 text-sm font-semibold text-surface-base transition hover:bg-accent-bright disabled:cursor-not-allowed disabled:opacity-60"
          >
            <LogIn aria-hidden="true" class="h-4 w-4" />
            <span>{{ authStore.isSubmitting ? "Signing in..." : "Sign In" }}</span>
          </button>
        </form>

        <p class="mt-6 text-center text-xs text-ink-muted">
          Need an account?
          <RouterLink :to="{ name: 'register' }" class="font-semibold text-accent hover:underline">
            Create one
          </RouterLink>
        </p>
      </div>
    </main>
  </div>
</template>
