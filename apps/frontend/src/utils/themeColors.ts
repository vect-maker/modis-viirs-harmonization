const DEFAULT_THERMAL_ZERO = '#1f2730'

const DEFAULT_THERMAL_PALETTE = [
  '#2d1e3e',
  '#6b2d5c',
  '#b84a39',
  '#e69f00',
  '#ffe066',
] as const

const DEFAULT_MAP_COLORS = {
  hotspotCore: '#e69f00',
  hotspotGlow: '#b84a39',
  hotspotStroke: '#ffffff',
} as const

const DEFAULT_CHART_COLORS = {
  barActive: '#e69f00',
  barDimmed: '#5c3d10',
} as const

function readCssToken(name: string, fallback: string): string {
  if (typeof document === 'undefined') return fallback
  const value = getComputedStyle(document.documentElement).getPropertyValue(name).trim()
  return value || fallback
}

export function getThermalZeroColor(): string {
  return readCssToken('--color-thermal-0', DEFAULT_THERMAL_ZERO)
}

export function getThermalPalette(): readonly string[] {
  return [
    readCssToken('--color-thermal-1', DEFAULT_THERMAL_PALETTE[0]),
    readCssToken('--color-thermal-2', DEFAULT_THERMAL_PALETTE[1]),
    readCssToken('--color-thermal-3', DEFAULT_THERMAL_PALETTE[2]),
    readCssToken('--color-thermal-4', DEFAULT_THERMAL_PALETTE[3]),
    readCssToken('--color-thermal-5', DEFAULT_THERMAL_PALETTE[4]),
  ]
}

export function getMapColors() {
  return {
    hotspotCore: readCssToken('--color-accent', DEFAULT_MAP_COLORS.hotspotCore),
    hotspotGlow: readCssToken('--color-accent-muted', DEFAULT_MAP_COLORS.hotspotGlow),
    hotspotStroke: DEFAULT_MAP_COLORS.hotspotStroke,
  }
}

export function getChartColors() {
  return {
    barActive: readCssToken('--color-accent', DEFAULT_CHART_COLORS.barActive),
    barDimmed: DEFAULT_CHART_COLORS.barDimmed,
  }
}
