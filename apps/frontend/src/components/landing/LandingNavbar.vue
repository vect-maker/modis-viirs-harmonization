<script setup lang="ts">
import { Flame, ArrowRight } from '@lucide/vue'
</script>

<template>
  <header
    class="sticky top-0 z-40 border-b border-border-subtle bg-surface-base/90 backdrop-blur-md"
  >
    <div class="mx-auto flex h-16 max-w-6xl items-center justify-between gap-4 px-4 sm:px-6">
      <RouterLink
        to="/"
        class="inline-flex items-center gap-2.5 rounded-md px-1 py-1 text-base font-semibold tracking-tight text-ink-primary focus-visible:outline-2 focus-visible:outline-focus"
      >
        <span
          class="flex h-8 w-8 items-center justify-center rounded-lg border border-accent/35 bg-accent/15 text-accent-bright"
        >
          <Flame aria-hidden="true" class="h-4 w-4" />
        </span>
        <span>PyroTrace</span>
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
