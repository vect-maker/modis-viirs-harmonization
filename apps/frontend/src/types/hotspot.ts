export interface FireHotspot {
  latitude: number
  longitude: number
  acq_datetime: string
  instrument: 'MODIS' | 'VIIRS'
  satellite: string
  confidence_class: string
  confidence: number
  frp: number
  bright_mir: number
  daynight: 'D' | 'N'
}
