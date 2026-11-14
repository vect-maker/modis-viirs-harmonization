export type CalendarSensor = 'ALL' | 'MODIS' | 'VIIRS'
export interface HistoricalMonth {
  year: number
  month: number
  total: number
  modisCount: number | null
  viirsCount: number | null
  observedDays: number
  avgFrp: number | null
  firstDetection: string
  lastDetection: string
}
export interface HistoricalArchive {
  country: string
  timezone: string
  harmonized: boolean
  coverageVerified: boolean
  source: string
  totalRecords: number
  firstDetection: string
  lastDetection: string
  months: HistoricalMonth[]
}
export interface CalendarCell {
  year: number
  month: number
  count: number | null
}
