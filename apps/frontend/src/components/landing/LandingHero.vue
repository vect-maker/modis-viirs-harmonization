<script setup lang="ts">
import { ArrowRight, CalendarDays, Satellite } from '@lucide/vue'
import { getThermalPalette, getThermalZeroColor } from '@/utils/themeColors'

const palette = getThermalPalette()
const zeroColor = getThermalZeroColor()

const previewRows = [
  { year: '2025', levels: [1, 2, 3, 4, 3, 1, 0, 0, 1, 1, 2, 1] },
  { year: '2024', levels: [1, 2, 4, 5, 5, 2, 1, 0, 1, 1, 1, 2] },
  { year: '2023', levels: [1, 2, 3, 4, 4, 2, 0, 1, 1, 1, 2, 1] },
  { year: '2022', levels: [0, 1, 3, 4, 3, 1, 0, 0, 1, 2, 1, 1] },
  { year: '2021', levels: [1, 1, 2, 3, 4, 2, 1, 0, 0, 1, 1, 1] },
] as const

const months = ['J', 'F', 'M', 'A', 'M', 'J', 'J', 'A', 'S', 'O', 'N', 'D']

function cellColor(level: number): string {
  if (level <= 0) return zeroColor
  return palette[level - 1] ?? zeroColor
}
</script>

<template>
  <section class="border-b border-border-subtle py-14 sm:py-20">
    <div class="mx-auto grid max-w-6xl items-center gap-10 px-4 sm:px-6 lg:grid-cols-12 lg:gap-12">
      <div class="space-y-6 lg:col-span-7">
        <div
          class="inline-flex items-center gap-2 rounded-full border border-telemetry/30 bg-telemetry/10 px-3 py-1 text-[11px] font-medium text-telemetry"
        >
          <Satellite aria-hidden="true" class="h-3.5 w-3.5" />
          <span>NASA Space Apps Challenge 2026 · Earth Observation</span>
        </div>

        <h1
          class="text-3xl font-bold tracking-tight text-ink-primary sm:text-4xl lg:text-5xl lg:leading-[1.12]"
        >
          25 Years of Satellite Fire History.
          <span class="text-accent-bright">One Continuous Calendar.</span>
        </h1>

        <p class="max-w-2xl text-base leading-relaxed text-ink-secondary sm:text-lg">
          PyroTrace bridges retiring <strong class="font-semibold text-ink-primary">MODIS</strong>
          (~1&nbsp;km) and modern <strong class="font-semibold text-ink-primary">VIIRS</strong>
          (375&nbsp;m) active fire detections into a unified burning activity calendar—helping
          early-warning teams, researchers, and land managers separate real fire anomalies from
          sensor artifacts.
        </p>

        <div class="flex flex-wrap items-center gap-3 pt-1">
          <RouterLink
            to="/dashboard"
            class="inline-flex min-h-11 items-center gap-2 rounded-lg bg-accent px-5 py-2.5 text-sm font-semibold text-surface-base transition hover:bg-accent-bright focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus"
          >
            <span>Open Interactive Dashboard</span>
            <ArrowRight aria-hidden="true" class="h-4 w-4" />
          </RouterLink>
          <a
            href="#methodology"
            class="inline-flex min-h-11 items-center gap-2 rounded-lg border border-border-strong bg-surface-panel px-5 py-2.5 text-sm font-medium text-ink-secondary transition hover:border-telemetry/50 hover:text-ink-primary focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus"
          >
            <span>How Harmonization Works</span>
          </a>
        </div>

        <dl class="grid grid-cols-3 gap-4 border-t border-border-subtle pt-6">
          <div>
            <dt class="text-[11px] uppercase tracking-wider text-ink-muted">Archive Span</dt>
            <dd class="mt-1 font-mono text-lg font-semibold text-ink-primary sm:text-xl">
              2000–2025
            </dd>
          </div>
          <div>
            <dt class="text-[11px] uppercase tracking-wider text-ink-muted">Nicaragua Slice</dt>
            <dd class="mt-1 font-mono text-lg font-semibold text-accent-bright sm:text-xl">
              800,480
            </dd>
          </div>
          <div>
            <dt class="text-[11px] uppercase tracking-wider text-ink-muted">Sensors</dt>
            <dd class="mt-1 font-mono text-lg font-semibold text-ink-primary sm:text-xl">
              MODIS + VIIRS
            </dd>
          </div>
        </dl>
      </div>

      <div class="lg:col-span-5">
        <div
          class="rounded-2xl border border-border-strong bg-surface-panel p-5 shadow-[0_16px_48px_#0006]"
        >
          <div class="mb-4 flex items-center justify-between gap-3">
            <div class="flex items-center gap-2">
              <CalendarDays aria-hidden="true" class="h-4 w-4 text-accent" />
              <h2 class="text-sm font-semibold text-ink-primary">
                Burning Activity Calendar Preview
              </h2>
            </div>
            <span
              class="rounded border border-border-subtle bg-surface-input px-2 py-0.5 font-mono text-[10px] text-ink-muted"
            >
              Thermal Inferno
            </span>
          </div>

          <div
            class="rounded-xl border border-border-subtle bg-surface-input p-3.5"
            aria-label="Sample 5-step colorblind-safe burning activity calendar matrix"
          >
            <div class="mb-2 grid grid-cols-[2.5rem_repeat(12,minmax(0,1fr))] gap-1 text-center">
              <span class="text-left font-mono text-[10px] text-ink-muted">Yr</span>
              <span
                v-for="m in months"
                :key="m"
                class="font-mono text-[10px] text-ink-muted"
                >{{ m }}</span
              >
            </div>
            <div class="space-y-1">
              <div
                v-for="row in previewRows"
                :key="row.year"
                class="grid grid-cols-[2.5rem_repeat(12,minmax(0,1fr))] items-center gap-1"
              >
                <span class="font-mono text-[11px] text-ink-secondary">{{ row.year }}</span>
                <span
                  v-for="(level, idx) in row.levels"
                  :key="idx"
                  class="h-5 rounded-[3px] border border-white/5"
                  :style="{ backgroundColor: cellColor(level) }"
                />
              </div>
            </div>
          </div>

          <div class="mt-4 flex items-center justify-between gap-2 text-[11px] text-ink-muted">
            <span>Colorblind-safe log ramp</span>
            <div class="flex items-center gap-1">
              <span>Low</span>
              <span
                v-for="c in palette"
                :key="c"
                class="h-3 w-4 rounded-sm"
                :style="{ backgroundColor: c }"
              />
              <span>Peak</span>
            </div>
          </div>

          <p class="mt-3 text-xs leading-relaxed text-ink-muted">
            Interactive map filtering, polygon ROI area calculation, and RFC-4180 CSV export
            available in the live dashboard.
          </p>
        </div>
      </div>
    </div>
  </section>
</template>
