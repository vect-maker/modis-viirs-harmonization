import { useApiFetch } from '@/api/useApiFetch'
import { buildChartQueryString, type WeatherCorrelationQuery } from './requests'
import { WeatherCorrelationEnvelopeSchema } from './responses'
import type { WeatherCorrelationData } from './types'

export function useModelChartsApi() {
  async function getWeatherCorrelation(
    params: WeatherCorrelationQuery,
  ): Promise<WeatherCorrelationData> {
    const qs = buildChartQueryString({ ...params }, params.polygon)
    const { data, error } = await useApiFetch(`/charts/models/weather-correlation${qs}`)
      .get()
      .json()
    if (error.value || !data.value) {
      throw error.value ?? new Error('Failed to fetch weather correlation')
    }
    return WeatherCorrelationEnvelopeSchema.parse(data.value).data
  }

  return {
    getWeatherCorrelation,
  }
}
