<script setup lang="ts">
import { ArrowLeft } from '@lucide/vue'
import PyroTraceLogo from '@/components/common/PyroTraceLogo.vue'

const links = [
  { label: 'Home', to: '/' },
  { label: 'Project', to: '/#proyecto' },
  { label: 'Data', to: '/#datos' },
  { label: 'Community', to: '/#comunidad' },
]
</script>

<template>
  <header
    class="z-30 shrink-0 border-b border-border-subtle bg-surface-base/95 backdrop-blur-md"
  >
    <div class="mx-auto flex h-[4.5rem] items-center justify-between gap-6 px-5 sm:px-8">
      <RouterLink
        to="/"
        aria-label="PyroTrace home"
        class="inline-flex shrink-0 items-center rounded-md py-1 focus-visible:outline-2 focus-visible:outline-focus"
      >
        <PyroTraceLogo class="h-9 w-auto" />
      </RouterLink>

      <nav aria-label="Dashboard navigation" class="hidden items-center gap-8 md:flex">
        <RouterLink
          v-for="link in links"
          :key="link.to"
          :to="link.to"
          class="text-[14px] font-medium text-ink-muted transition-colors hover:text-ink-primary focus-visible:outline-2 focus-visible:outline-focus"
        >
          {{ link.label }}
        </RouterLink>
      </nav>

      <div class="flex items-center gap-3">
        <RouterLink
          to="/"
          class="inline-flex min-h-10 items-center gap-2 rounded-lg bg-accent px-4 py-2 text-[13px] font-semibold text-surface-base transition hover:bg-accent-bright focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus"
        >
          <ArrowLeft aria-hidden="true" class="h-4 w-4" />
          <span>Overview</span>
        </RouterLink>
      </div>
    </div>
  </header>
</template>
