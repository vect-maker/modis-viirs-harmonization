import { useApiFetch } from '@/api/useApiFetch'
import {
  buildChartQueryString,
  type ConfidenceDbscanQuery,
  type CorrelationsQuery,
  type SpatialAnomaliesQuery,
  type SpatialDensityQuery,
} from './requests'
import {
  ConfidenceDbscanEnvelopeSchema,
  CorrelationsEnvelopeSchema,
  SpatialAnomaliesEnvelopeSchema,
  SpatialDensityEnvelopeSchema,
} from './responses'
import type {
  ConfidenceDbscanData,
  CorrelationPair,
  SpatialAnomaliesData,
  SpatialDensityData,
} from './types'

export function useDiagnosticChartsApi() {
  async function getConfidenceDbscan(
    params?: ConfidenceDbscanQuery,
  ): Promise<ConfidenceDbscanData> {
    const qs = buildChartQueryString({ ...(params ?? {}) }, params?.polygon)
    const { data, error } = await useApiFetch(`/charts/diagnostics/confidence-dbscan${qs}`)
      .get()
      .json()
    if (error.value || !data.value) {
      throw error.value ?? new Error('Failed to fetch confidence DBSCAN')
    }
    return ConfidenceDbscanEnvelopeSchema.parse(data.value).data
  }

  async function getCorrelations(params?: CorrelationsQuery): Promise<CorrelationPair[]> {
    const qs = buildChartQueryString({ ...(params ?? {}) }, params?.polygon)
    const { data, error } = await useApiFetch(`/charts/diagnostics/correlations${qs}`)
      .get()
      .json()
    if (error.value || !data.value) {
      throw error.value ?? new Error('Failed to fetch correlations')
    }
    return CorrelationsEnvelopeSchema.parse(data.value).data
  }

  async function getSpatialDensity(params?: SpatialDensityQuery): Promise<SpatialDensityData> {
    const qs = buildChartQueryString({ ...(params ?? {}) }, params?.polygon)
    const { data, error } = await useApiFetch(`/charts/diagnostics/spatial-density${qs}`)
      .get()
      .json()
    if (error.value || !data.value) {
      throw error.value ?? new Error('Failed to fetch spatial density')
    }
    return SpatialDensityEnvelopeSchema.parse(data.value).data
  }

  async function getSpatialAnomalies(
    params?: SpatialAnomaliesQuery,
  ): Promise<SpatialAnomaliesData> {
    const qs = buildChartQueryString({ ...(params ?? {}) }, params?.polygon)
    const { data, error } = await useApiFetch(`/charts/diagnostics/spatial-anomalies${qs}`)
      .get()
      .json()
    if (error.value || !data.value) {
      throw error.value ?? new Error('Failed to fetch spatial anomalies')
    }
    return SpatialAnomaliesEnvelopeSchema.parse(data.value).data
  }

  return {
    getConfidenceDbscan,
    getCorrelations,
    getSpatialDensity,
    getSpatialAnomalies,
  }
}
