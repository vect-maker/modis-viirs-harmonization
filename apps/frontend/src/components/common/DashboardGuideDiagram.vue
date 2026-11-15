<script setup lang="ts">
export type GuideDiagramVariant = 'layers' | 'aoi' | 'timeline' | 'stats'

defineProps<{
  variant: GuideDiagramVariant
}>()
</script>

<template>
  <!-- 1. Layers: Fire Event perimeter grouping raw MODIS/VIIRS hotspots -->
  <svg
    v-if="variant === 'layers'"
    viewBox="0 0 240 88"
    class="h-22 w-full"
    role="img"
    aria-label="Diagram showing thermal hotspot points grouped inside a fire event perimeter"
  >
    <g stroke="#1e293b" stroke-width="1">
      <line x1="0" y1="22" x2="240" y2="22" />
      <line x1="0" y1="44" x2="240" y2="44" />
      <line x1="0" y1="66" x2="240" y2="66" />
      <line x1="60" y1="0" x2="60" y2="88" />
      <line x1="120" y1="0" x2="120" y2="88" />
      <line x1="180" y1="0" x2="180" y2="88" />
    </g>

    <!-- Fire Event perimeter -->
    <polygon
      points="42,24 94,16 122,42 104,70 52,66 34,46"
      fill="#f97316"
      fill-opacity="0.16"
      stroke="#fb923c"
      stroke-width="1.75"
      stroke-dasharray="4 2"
    />
    <!-- Constituent hotspots -->
    <circle cx="58" cy="36" r="4" fill="#ef4444" stroke="#fef08a" stroke-width="1.2" />
    <circle cx="88" cy="30" r="3.5" fill="#f97316" stroke="#fed7aa" stroke-width="1.2" />
    <circle cx="96" cy="54" r="4.5" fill="#ef4444" stroke="#fef08a" stroke-width="1.2" />
    <circle cx="66" cy="56" r="3.2" fill="#eab308" stroke="#fef9c3" stroke-width="1.2" />
    <!-- Centroid ring -->
    <circle cx="77" cy="44" r="7" fill="none" stroke="#fdba74" stroke-width="1.2" stroke-opacity="0.7" />

    <!-- Isolated point outside -->
    <circle cx="176" cy="30" r="3.5" fill="#eab308" stroke="#fef9c3" stroke-width="1.2" />

    <!-- Labels -->
    <text x="136" y="54" fill="#fdba74" font-size="9" font-family="ui-monospace, monospace">
      Event (2+ pts)
    </text>
    <text x="136" y="66" fill="#94a3b8" font-size="8" font-family="ui-sans-serif, sans-serif">
      ≤ 24 h gap · 0.02° grid
    </text>
    <text x="148" y="20" fill="#cbd5e1" font-size="8" font-family="ui-sans-serif, sans-serif">
      Single hotspot
    </text>
  </svg>

  <!-- 2. AOI: Drawn polygon filtering inside vs outside points -->
  <svg
    v-else-if="variant === 'aoi'"
    viewBox="0 0 240 88"
    class="h-22 w-full"
    role="img"
    aria-label="Diagram showing a drawn polygon filtering fire detections inside the selected area"
  >
    <g stroke="#1e293b" stroke-width="1">
      <line x1="0" y1="22" x2="240" y2="22" />
      <line x1="0" y1="44" x2="240" y2="44" />
      <line x1="0" y1="66" x2="240" y2="66" />
      <line x1="60" y1="0" x2="60" y2="88" />
      <line x1="120" y1="0" x2="120" y2="88" />
      <line x1="180" y1="0" x2="180" y2="88" />
    </g>

    <!-- Outside dimmed detections -->
    <circle cx="28" cy="24" r="3" fill="#475569" />
    <circle cx="196" cy="22" r="3" fill="#475569" />
    <circle cx="208" cy="64" r="3" fill="#475569" />

    <!-- Drawn AOI polygon -->
    <polygon
      points="66,18 152,14 166,58 92,72 56,48"
      fill="#38bdf8"
      fill-opacity="0.12"
      stroke="#38bdf8"
      stroke-width="1.75"
    />
    <!-- Vertices -->
    <circle cx="66" cy="18" r="2.5" fill="#e0f2fe" />
    <circle cx="152" cy="14" r="2.5" fill="#e0f2fe" />
    <circle cx="166" cy="58" r="2.5" fill="#e0f2fe" />
    <circle cx="92" cy="72" r="2.5" fill="#e0f2fe" />
    <circle cx="56" cy="48" r="2.5" fill="#e0f2fe" />

    <!-- Highlighted detections inside AOI -->
    <circle cx="96" cy="34" r="4" fill="#f97316" stroke="#fef08a" stroke-width="1.2" />
    <circle cx="128" cy="40" r="4.5" fill="#ef4444" stroke="#fef08a" stroke-width="1.2" />
    <circle cx="108" cy="54" r="3.5" fill="#f97316" stroke="#fed7aa" stroke-width="1.2" />

    <text x="174" y="42" fill="#7dd3fc" font-size="8.5" font-family="ui-monospace, monospace">
      AOI filter
    </text>
    <text x="174" y="53" fill="#94a3b8" font-size="8" font-family="ui-sans-serif, sans-serif">
      3 matched
    </text>
  </svg>

  <!-- 3. Timeline: Daily activity bars + selected day + historical grid -->
  <svg
    v-else-if="variant === 'timeline'"
    viewBox="0 0 240 88"
    class="h-22 w-full"
    role="img"
    aria-label="Diagram showing daily activity bar selection and historical monthly calendar archive"
  >
    <!-- Baseline -->
    <line x1="14" y1="68" x2="146" y2="68" stroke="#334155" stroke-width="1" />
    <!-- Daily bars -->
    <rect x="20" y="46" width="10" height="22" rx="2" fill="#475569" />
    <rect x="34" y="38" width="10" height="30" rx="2" fill="#475569" />
    <rect x="48" y="50" width="10" height="18" rx="2" fill="#475569" />
    <rect x="62" y="22" width="10" height="46" rx="2" fill="#f97316" stroke="#fef08a" stroke-width="1" />
    <rect x="76" y="34" width="10" height="34" rx="2" fill="#64748b" />
    <rect x="90" y="42" width="10" height="26" rx="2" fill="#475569" />
    <rect x="104" y="28" width="10" height="40" rx="2" fill="#64748b" />
    <rect x="118" y="48" width="10" height="20" rx="2" fill="#475569" />
    <rect x="132" y="54" width="10" height="14" rx="2" fill="#475569" />

    <text x="52" y="15" fill="#fdba74" font-size="8" font-family="ui-monospace, monospace">
      Click day
    </text>
    <text x="14" y="80" fill="#94a3b8" font-size="8" font-family="ui-sans-serif, sans-serif">
      Daily UTC bars
    </text>

    <!-- Historical heatmap mini grid -->
    <g transform="translate(164, 16)">
      <rect x="0" y="0" width="12" height="10" rx="2" fill="#1e293b" />
      <rect x="15" y="0" width="12" height="10" rx="2" fill="#7c2d12" />
      <rect x="30" y="0" width="12" height="10" rx="2" fill="#ea580c" />
      <rect x="45" y="0" width="12" height="10" rx="2" fill="#334155" />

      <rect x="0" y="13" width="12" height="10" rx="2" fill="#9a3412" />
      <rect x="15" y="13" width="12" height="10" rx="2" fill="#f97316" />
      <rect x="30" y="13" width="12" height="10" rx="2" fill="#c2410c" />
      <rect x="45" y="13" width="12" height="10" rx="2" fill="#1e293b" />

      <rect x="0" y="26" width="12" height="10" rx="2" fill="#334155" />
      <rect x="15" y="26" width="12" height="10" rx="2" fill="#7c2d12" />
      <rect x="30" y="26" width="12" height="10" rx="2" fill="#fb923c" />
      <rect x="45" y="26" width="12" height="10" rx="2" fill="#9a3412" />
    </g>
    <text x="164" y="68" fill="#cbd5e1" font-size="8" font-family="ui-sans-serif, sans-serif">
      Historical
    </text>
    <text x="164" y="79" fill="#94a3b8" font-size="7.5" font-family="ui-sans-serif, sans-serif">
      2000–2026
    </text>
  </svg>

  <!-- 4. Stats: Trendline + distribution + correlation mini graphs -->
  <svg
    v-else
    viewBox="0 0 240 88"
    class="h-22 w-full"
    role="img"
    aria-label="Diagram showing distribution, forecast trendline, and correlation charts inside Statistics"
  >
    <!-- Left mini chart: Forecast line -->
    <rect x="8" y="10" width="106" height="68" rx="6" fill="#0f172a" stroke="#1e293b" />
    <path
      d="M 16 60 L 36 52 L 54 55 L 72 34 L 90 38"
      fill="none"
      stroke="#38bdf8"
      stroke-width="2"
      stroke-linecap="round"
    />
    <path
      d="M 90 38 L 106 24"
      fill="none"
      stroke="#f97316"
      stroke-width="2"
      stroke-dasharray="3 2"
      stroke-linecap="round"
    />
    <circle cx="90" cy="38" r="2.5" fill="#f97316" />
    <text x="16" y="24" fill="#94a3b8" font-size="8" font-family="ui-sans-serif, sans-serif">
      Forecast &amp; Trend
    </text>

    <!-- Right mini chart: Distribution & Weather correlation -->
    <rect x="124" y="10" width="108" height="68" rx="6" fill="#0f172a" stroke="#1e293b" />
    <rect x="134" y="46" width="9" height="22" rx="1.5" fill="#fb923c" />
    <rect x="147" y="34" width="9" height="34" rx="1.5" fill="#f97316" />
    <rect x="160" y="42" width="9" height="26" rx="1.5" fill="#ea580c" />
    <circle cx="192" cy="56" r="2.2" fill="#38bdf8" />
    <circle cx="202" cy="46" r="2.2" fill="#38bdf8" />
    <circle cx="212" cy="38" r="2.2" fill="#38bdf8" />
    <circle cx="218" cy="32" r="2.2" fill="#7dd3fc" />
    <text x="134" y="24" fill="#94a3b8" font-size="8" font-family="ui-sans-serif, sans-serif">
      Distributions &amp; Weather
    </text>
  </svg>
</template>
