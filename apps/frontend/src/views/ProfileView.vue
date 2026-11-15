<script setup lang="ts">
import { LogOut, Save } from "@lucide/vue";
import { computed, ref, watchEffect } from "vue";
import { useRouter } from "vue-router";
import DashboardNavbar from "@/components/features/DashboardNavbar.vue";
import { useAuthStore } from "@/stores/auth";

const router = useRouter();
const authStore = useAuthStore();

const username = ref("");
const email = ref("");
const saveSuccess = ref(false);
const localError = ref<string | null>(null);

watchEffect(() => {
  if (authStore.user) {
    username.value = authStore.user.username;
    email.value = authStore.user.email;
  }
});

const initials = computed(() => {
  const name = authStore.user?.username ?? "";
  return name.slice(0, 2).toUpperCase() || "PT";
});

const memberSince = computed(() => {
  if (!authStore.user?.created_at) return "";
  return new Date(authStore.user.created_at).toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
});

async function handleSave() {
  saveSuccess.value = false;
  localError.value = null;
  try {
    await authStore.updateProfile({
      username: username.value.trim(),
      email: email.value.trim(),
    });
    saveSuccess.value = true;
  } catch (err) {
    localError.value = err instanceof Error ? err.message : "Failed to update profile";
  }
}

async function handleLogout() {
  await authStore.logout();
  await router.push({ name: "login" });
}
</script>

<template>
  <div class="flex min-h-screen flex-col bg-surface-base text-ink-primary">
    <DashboardNavbar />

    <main class="mx-auto w-full max-w-2xl flex-1 px-5 py-10">
      <div class="rounded-2xl border border-border-subtle bg-surface-raised p-8 shadow-xl">
        <div class="flex flex-wrap items-center justify-between gap-4 border-b border-border-subtle pb-6">
          <div class="flex items-center gap-4">
            <div
              aria-hidden="true"
              class="flex h-14 w-14 items-center justify-center rounded-full border border-accent/40 bg-accent/15 text-lg font-bold text-accent"
            >
              {{ initials }}
            </div>
            <div>
              <h1 class="text-lg font-bold text-ink-primary">
                {{ authStore.user?.username }}
              </h1>
              <p class="text-xs text-ink-muted">
                Role: <span class="font-medium text-ink-secondary">{{ authStore.user?.role }}</span>
                <span v-if="memberSince"> • Member since {{ memberSince }}</span>
              </p>
            </div>
          </div>

          <button
            type="button"
            :disabled="authStore.isSubmitting"
            class="inline-flex min-h-10 cursor-pointer items-center gap-2 rounded-lg border border-border-subtle bg-surface-base px-3.5 py-2 text-xs font-medium text-ink-secondary transition hover:border-red-500/40 hover:text-red-300 disabled:opacity-60"
            @click="handleLogout"
          >
            <LogOut aria-hidden="true" class="h-3.5 w-3.5" />
            <span>Sign Out</span>
          </button>
        </div>

        <div
          v-if="saveSuccess"
          role="status"
          class="mt-6 rounded-lg border border-emerald-500/30 bg-emerald-950/40 px-3.5 py-2.5 text-xs text-emerald-200"
        >
          Profile updated successfully.
        </div>

        <div
          v-if="localError || authStore.error"
          role="alert"
          class="mt-6 rounded-lg border border-red-500/30 bg-red-950/40 px-3.5 py-2.5 text-xs text-red-200"
        >
          {{ localError || authStore.error }}
        </div>

        <form class="mt-6 space-y-5" @submit.prevent="handleSave">
          <div>
            <label for="profile-username" class="mb-1.5 block text-xs font-medium text-ink-secondary">
              Username
            </label>
            <input
              id="profile-username"
              v-model="username"
              type="text"
              minlength="3"
              maxlength="64"
              pattern="[a-zA-Z0-9_.-]+"
              required
              class="w-full rounded-lg border border-border-subtle bg-surface-base px-3.5 py-2.5 text-sm text-ink-primary focus:border-accent focus:outline-none"
            />
          </div>

          <div>
            <label for="profile-email" class="mb-1.5 block text-xs font-medium text-ink-secondary">
              Email address
            </label>
            <input
              id="profile-email"
              v-model="email"
              type="email"
              required
              class="w-full rounded-lg border border-border-subtle bg-surface-base px-3.5 py-2.5 text-sm text-ink-primary focus:border-accent focus:outline-none"
            />
          </div>

          <div class="flex justify-end pt-2">
            <button
              type="submit"
              :disabled="authStore.isSubmitting"
              class="inline-flex min-h-10 cursor-pointer items-center gap-2 rounded-lg bg-accent px-5 py-2 text-xs font-semibold text-surface-base transition hover:bg-accent-bright disabled:cursor-not-allowed disabled:opacity-60"
            >
              <Save aria-hidden="true" class="h-3.5 w-3.5" />
              <span>{{ authStore.isSubmitting ? "Saving..." : "Save Changes" }}</span>
            </button>
          </div>
        </form>
      </div>
    </main>
  </div>
</template>
