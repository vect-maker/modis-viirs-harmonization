<script setup lang="ts">
import { ArrowLeft, UserPlus } from "@lucide/vue";
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import PyroTraceLogo from "@/components/common/PyroTraceLogo.vue";
import { useAuthStore } from "@/stores/auth";

const router = useRouter();
const authStore = useAuthStore();

const username = ref("");
const email = ref("");
const password = ref("");
const confirmPassword = ref("");
const localError = ref<string | null>(null);

onMounted(() => {
  authStore.clearError();
});

async function handleSubmit() {
  localError.value = null;
  if (password.value !== confirmPassword.value) {
    localError.value = "Passwords do not match";
    return;
  }

  try {
    await authStore.register({
      username: username.value.trim(),
      email: email.value.trim(),
      password: password.value,
    });
    await router.push({
      name: "login",
      query: { registered: "1", email: email.value.trim() },
    });
  } catch (err) {
    localError.value = err instanceof Error ? err.message : "Unable to register";
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
          <h1 class="text-xl font-bold tracking-tight text-ink-primary">Create an account</h1>
          <p class="mt-1 text-xs text-ink-muted">
            Join PyroTrace to report and verify active fire hotspots in the field.
          </p>
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
            <label for="reg-username" class="mb-1.5 block text-xs font-medium text-ink-secondary">
              Username
            </label>
            <input
              id="reg-username"
              v-model="username"
              type="text"
              autocomplete="username"
              minlength="3"
              maxlength="64"
              pattern="[a-zA-Z0-9_.-]+"
              required
              placeholder="fire_analyst"
              class="w-full rounded-lg border border-border-subtle bg-surface-base px-3.5 py-2.5 text-sm text-ink-primary placeholder:text-ink-muted/60 focus:border-accent focus:outline-none"
            />
          </div>

          <div>
            <label for="reg-email" class="mb-1.5 block text-xs font-medium text-ink-secondary">
              Email address
            </label>
            <input
              id="reg-email"
              v-model="email"
              type="email"
              autocomplete="email"
              required
              placeholder="analyst@example.org"
              class="w-full rounded-lg border border-border-subtle bg-surface-base px-3.5 py-2.5 text-sm text-ink-primary placeholder:text-ink-muted/60 focus:border-accent focus:outline-none"
            />
          </div>

          <div>
            <label for="reg-password" class="mb-1.5 block text-xs font-medium text-ink-secondary">
              Password (min. 8 characters)
            </label>
            <input
              id="reg-password"
              v-model="password"
              type="password"
              autocomplete="new-password"
              minlength="8"
              maxlength="128"
              required
              placeholder="••••••••"
              class="w-full rounded-lg border border-border-subtle bg-surface-base px-3.5 py-2.5 text-sm text-ink-primary placeholder:text-ink-muted/60 focus:border-accent focus:outline-none"
            />
          </div>

          <div>
            <label
              for="reg-confirm-password"
              class="mb-1.5 block text-xs font-medium text-ink-secondary"
            >
              Confirm password
            </label>
            <input
              id="reg-confirm-password"
              v-model="confirmPassword"
              type="password"
              autocomplete="new-password"
              minlength="8"
              maxlength="128"
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
            <UserPlus aria-hidden="true" class="h-4 w-4" />
            <span>{{ authStore.isSubmitting ? "Creating account..." : "Create Account" }}</span>
          </button>
        </form>

        <p class="mt-6 text-center text-xs text-ink-muted">
          Already have an account?
          <RouterLink :to="{ name: 'login' }" class="font-semibold text-accent hover:underline">
            Sign in
          </RouterLink>
        </p>
      </div>
    </main>
  </div>
</template>
