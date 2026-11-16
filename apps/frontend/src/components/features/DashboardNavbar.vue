<script setup lang="ts">
import { computed } from 'vue'
import { ArrowLeft, LogIn, User } from '@lucide/vue'
import { useI18n } from 'vue-i18n'
import LocaleSwitcher from '@/components/common/LocaleSwitcher.vue'
import PyroTraceLogo from '@/components/common/PyroTraceLogo.vue'
import DashboardGuidePopover from '@/components/features/DashboardGuidePopover.vue'
import { useAuthStore } from '@/stores/auth'

const { t } = useI18n()
const authStore = useAuthStore()

const links = computed(() => [
  { key: 'home', label: t('nav.home'), to: { name: 'landing' } },
  { key: 'project', label: t('nav.project'), to: { name: 'landing', hash: '#proyecto' } },
  { key: 'data', label: t('nav.data'), to: { name: 'landing', hash: '#datos' } },
  { key: 'community', label: t('nav.community'), to: { name: 'landing', hash: '#comunidad' } },
])
</script>

<template>
  <header
    class="z-30 shrink-0 border-b border-border-subtle bg-surface-base/95 backdrop-blur-md"
  >
    <div class="mx-auto flex h-[4.5rem] items-center justify-between gap-6 px-5 sm:px-8">
      <RouterLink
        :to="{ name: 'landing' }"
        :aria-label="t('nav.brandHomeAria')"
        class="inline-flex shrink-0 items-center rounded-md py-1 focus-visible:outline-2 focus-visible:outline-focus"
      >
        <PyroTraceLogo class="h-9 w-auto" />
      </RouterLink>

      <nav :aria-label="t('nav.dashboardNavAria')" class="hidden items-center gap-8 md:flex">
        <RouterLink
          v-for="link in links"
          :key="link.key"
          :to="link.to"
          class="text-[14px] font-medium text-ink-muted transition-colors hover:text-ink-primary focus-visible:outline-2 focus-visible:outline-focus"
        >
          {{ link.label }}
        </RouterLink>
      </nav>

      <div class="flex items-center gap-3">
        <LocaleSwitcher variant="dashboard" />
        <DashboardGuidePopover />
        <RouterLink
          v-if="authStore.isAuthenticated"
          :to="{ name: 'profile' }"
          class="inline-flex min-h-10 items-center gap-2 rounded-lg border border-border-subtle bg-surface-raised px-3.5 py-2 text-[13px] font-medium text-ink-primary transition hover:border-accent/50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus"
        >
          <User aria-hidden="true" class="h-3.5 w-3.5 text-accent" />
          <span>{{ authStore.user?.username }}</span>
        </RouterLink>
        <RouterLink
          v-else
          :to="{ name: 'login' }"
          class="inline-flex min-h-10 items-center gap-2 rounded-lg border border-border-subtle bg-surface-raised px-3.5 py-2 text-[13px] font-medium text-ink-secondary transition hover:text-ink-primary focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus"
        >
          <LogIn aria-hidden="true" class="h-3.5 w-3.5" />
          <span>{{ t('nav.signInTitle') }}</span>
        </RouterLink>

        <RouterLink
          :to="{ name: 'landing' }"
          class="inline-flex min-h-10 items-center gap-2 rounded-lg bg-accent px-4 py-2 text-[13px] font-semibold text-surface-base transition hover:bg-accent-bright focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus"
        >
          <ArrowLeft aria-hidden="true" class="h-4 w-4" />
          <span>{{ t('nav.overview') }}</span>
        </RouterLink>
      </div>
    </div>
  </header>
</template>
