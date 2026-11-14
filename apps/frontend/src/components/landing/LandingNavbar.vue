<script setup lang="ts">
import { ArrowRight } from '@lucide/vue'
import PyroTraceLogo from '@/components/common/PyroTraceLogo.vue'
</script>

<template>
  <header
    class="sticky top-0 z-40 border-b border-border-subtle bg-surface-base/90 backdrop-blur-md"
  >
    <div class="mx-auto flex h-16 max-w-6xl items-center justify-between gap-4 px-4 sm:px-6">
      <RouterLink
        to="/"
        class="inline-flex items-center rounded-md px-1 py-1 focus-visible:outline-2 focus-visible:outline-focus"
      >
        <PyroTraceLogo class="h-8 w-auto" />
      </RouterLink>

      <nav aria-label="Primary navigation" class="hidden items-center gap-6 md:flex">
        <a
          href="#problem"
          class="text-xs font-medium text-ink-muted transition-colors hover:text-ink-primary focus-visible:outline-2 focus-visible:outline-focus"
        >
          Continuity Gap
        </a>
        <a
          href="#methodology"
          class="text-xs font-medium text-ink-muted transition-colors hover:text-ink-primary focus-visible:outline-2 focus-visible:outline-focus"
        >
          Methodology
        </a>
        <a
          href="#audience"
          class="text-xs font-medium text-ink-muted transition-colors hover:text-ink-primary focus-visible:outline-2 focus-visible:outline-focus"
        >
          Who It’s For
        </a>
      </nav>

      <RouterLink
        to="/dashboard"
        class="inline-flex min-h-10 items-center gap-2 rounded-lg bg-accent px-4 py-2 text-xs font-semibold text-surface-base transition hover:bg-accent-bright focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus"
      >
        <span>Launch Dashboard</span>
        <ArrowRight aria-hidden="true" class="h-3.5 w-3.5" />
      </RouterLink>
    </div>
  </header>
</template>
