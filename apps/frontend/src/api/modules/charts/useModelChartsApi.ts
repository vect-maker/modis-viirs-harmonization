import { useApiFetch } from '@/api/useApiFetch'
import {
  buildChartQueryString,
  type ClusterMovementQuery,
  type FirePredictQuery,
  type MonthlyForecastQuery,
  type WeatherCorrelationQuery,
} from './requests'
import {
  ClusterMovementEnvelopeSchema,
  FirePredictEnvelopeSchema,
  MonthlyForecastEnvelopeSchema,
  WeatherCorrelationEnvelopeSchema,
} from './responses'
import type {
  ClusterMovementData,
  FirePredictData,
  MonthlyForecastData,
  WeatherCorrelationData,
} from './types'

export function useModelChartsApi() {
  async function getMonthlyForecast(
    params?: MonthlyForecastQuery,
  ): Promise<MonthlyForecastData> {
    const qs = buildChartQueryString({ ...(params ?? {}) }, params?.polygon)
    const { data, error } = await useApiFetch(`/charts/models/monthly-forecast${qs}`)
      .get()
      .json()
    if (error.value || !data.value) {
      throw error.value ?? new Error('Failed to fetch monthly forecast')
    }
    return MonthlyForecastEnvelopeSchema.parse(data.value).data
  }

  async function getClusterMovement(
    params?: ClusterMovementQuery,
  ): Promise<ClusterMovementData> {
    const qs = buildChartQueryString({ ...(params ?? {}) }, params?.polygon)
    const { data, error } = await useApiFetch(`/charts/models/cluster-movement${qs}`)
      .get()
      .json()
    if (error.value || !data.value) {
      throw error.value ?? new Error('Failed to fetch cluster movement')
    }
    return ClusterMovementEnvelopeSchema.parse(data.value).data
  }

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

  async function getPredict(params?: FirePredictQuery): Promise<FirePredictData> {
    const qs = buildChartQueryString({ ...(params ?? {}) }, params?.polygon)
    const { data, error } = await useApiFetch(`/charts/models/predict${qs}`).get().json()
    if (error.value || !data.value) {
      throw error.value ?? new Error('Failed to fetch fire displacement prediction')
    }
    return FirePredictEnvelopeSchema.parse(data.value).data
  }

  return {
    getMonthlyForecast,
    getClusterMovement,
    getWeatherCorrelation,
    getPredict,
  }
}
