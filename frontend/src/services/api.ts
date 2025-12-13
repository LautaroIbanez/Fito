import axios from 'axios'
import { diagnostics } from '../utils/diagnostics'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8001/api'

// Configurar interceptores de axios para diagnóstico
axios.interceptors.request.use(
  (config) => {
    const callId = diagnostics.startHttpCall(config.method?.toUpperCase() || 'GET', config.url || '')
    // Guardar el ID en la configuración para usarlo en la respuesta
    ;(config as any).__diagnosticsId = callId
    return config
  },
  (error) => {
    console.error('[API] Error en interceptor de request:', error)
    return Promise.reject(error)
  }
)

axios.interceptors.response.use(
  (response) => {
    const callId = (response.config as any).__diagnosticsId
    if (callId) {
      diagnostics.endHttpCall(callId, response.status)
    }
    return response
  },
  (error) => {
    const callId = (error.config as any)?.__diagnosticsId
    if (callId) {
      const status = error.response?.status
      const errorMessage = error.response?.data?.detail || error.message || 'Error desconocido'
      diagnostics.endHttpCall(callId, status, errorMessage)
    }
    return Promise.reject(error)
  }
)

export interface NewsItem {
  id: number
  title?: string
  body: string
  source?: string
  created_at: string
  score?: number
  score_components?: {
    base?: number
    ticker_matches?: number
    ticker_score?: number
    category_matches?: number
    category_score?: number
    sentiment_type?: string
    sentiment_score?: number
    temporal_decay?: number
    age_days?: number
    is_obsolete?: boolean
  }
  is_obsolete?: boolean
}

export interface NewsItemCreate {
  title?: string
  body: string
  source?: string
}

export interface PortfolioItem {
  id: number
  asset_type: string
  name: string
  symbol?: string
  quantity?: string
  price?: string
  total_value?: string
  currency?: string
  notes?: string
  created_at: string
  updated_at: string
}

export interface PortfolioItemCreate {
  asset_type: string
  name: string
  symbol?: string
  quantity?: string
  price?: string
  total_value?: string
  currency?: string
  notes?: string
}

export interface AnalysisResponse {
  analysis: {
    raw: string
    structured: {
      resumen_ejecutivo: string
      riesgos_identificados: string
      actores_clave: string
      senales_tempranas: string
      recomendaciones_cartera?: string
      conclusiones_accionables: string
    }
    model_used: string
    tokens_used?: number
  }
  news_count: number
  portfolio_count: number
  generated_at: string
  version: string
}

export interface NewsSummary {
  news_id: number
  news_title: string
  summary: string
  explanation: string
  score: number
  sentiment: string
}

export interface PortfolioImpact {
  type: 'positive' | 'negative' | 'neutral'
  description: string
  affected_assets?: string[]
}

export interface Suggestion {
  action: 'add' | 'watch' | 'trim' | 'exit'
  description: string
  tone: 'positive' | 'negative' | 'neutral' | 'unknown'
}

export interface NewsSummariesResponse {
  summaries: NewsSummary[]
  portfolio_impacts: PortfolioImpact[]
  suggestions: Suggestion[]
  generated_at: string
  news_count: number
}

export const newsApi = {
  create: async (newsItem: NewsItemCreate): Promise<NewsItem> => {
    const response = await axios.post<NewsItem>(`${API_BASE_URL}/news`, newsItem)
    return response.data
  },

  list: async (sortBy: 'score' | 'date' = 'score'): Promise<NewsItem[]> => {
    const response = await axios.get<{ items: NewsItem[]; total: number }>(`${API_BASE_URL}/news?sort_by=${sortBy}`)
    return response.data.items
  },

  update: async (id: number, newsItem: NewsItemCreate): Promise<NewsItem> => {
    const response = await axios.put<NewsItem>(`${API_BASE_URL}/news/${id}`, newsItem)
    return response.data
  },

  delete: async (id: number): Promise<void> => {
    await axios.delete(`${API_BASE_URL}/news/${id}`)
  },

  clearAll: async (): Promise<NewsItem[]> => {
    const response = await axios.delete<{ items: NewsItem[]; total: number }>(`${API_BASE_URL}/news`)
    return response.data.items
  },

  generateAnalysis: async (): Promise<AnalysisResponse> => {
    const response = await axios.post<AnalysisResponse>(`${API_BASE_URL}/analysis`, {})
    return response.data
  },

  getSituationSummary: async (): Promise<SituationSummary> => {
    const response = await axios.get<SituationSummary>(`${API_BASE_URL}/news/summary`)
    return response.data
  },

  getNewsSummaries: async (maxItems: number = 10): Promise<NewsSummariesResponse> => {
    const response = await axios.post<NewsSummariesResponse>(
      `${API_BASE_URL}/analysis/news-summaries?max_items=${maxItems}`,
      {}
    )
    return response.data
  },
}


export interface RiskDashboard {
  portfolio_value: number
  exposure_by_asset: Array<{
    id: number
    name: string
    symbol?: string
    asset_type: string
    value: number
    percentage: number
    currency: string
  }>
  exposure_by_sector: Array<{
    sector: string
    value: number
    percentage: number
    asset_count: number
  }>
  top_concentrations: Array<{
    id: number
    name: string
    symbol?: string
    asset_type: string
    value: number
    percentage: number
    currency: string
  }>
  volatility: {
    volatility_30d: number
    volatility_90d: number
    annual_volatility: number
  }
  var: {
    var_30d_95: number
    var_30d_99: number
    var_90d_95: number
    var_90d_99: number
    portfolio_value: number
  }
}

export const portfolioApi = {
  list: async (): Promise<PortfolioItem[]> => {
    const response = await axios.get<{ items: PortfolioItem[]; total: number }>(`${API_BASE_URL}/portfolio`)
    return response.data.items
  },

  create: async (item: PortfolioItemCreate): Promise<PortfolioItem> => {
    const response = await axios.post<PortfolioItem>(`${API_BASE_URL}/portfolio`, item)
    return response.data
  },

  update: async (id: number, item: PortfolioItemCreate): Promise<PortfolioItem> => {
    const response = await axios.put<PortfolioItem>(`${API_BASE_URL}/portfolio/${id}`, item)
    return response.data
  },

  delete: async (id: number): Promise<void> => {
    await axios.delete(`${API_BASE_URL}/portfolio/${id}`)
  },

  clearAll: async (): Promise<PortfolioItem[]> => {
    const response = await axios.delete<{ items: PortfolioItem[]; total: number }>(`${API_BASE_URL}/portfolio`)
    return response.data.items
  },

  getRiskDashboard: async (top_n: number = 5): Promise<RiskDashboard> => {
    const response = await axios.get<RiskDashboard>(`${API_BASE_URL}/portfolio/risk-dashboard?top_n=${top_n}`)
    return response.data
  },

  getPriceHistory: async (itemId: number, days: number = 60): Promise<{ item_id: number; symbol?: string; name: string; data: Array<{ date: string; price: number }>; days: number; note: string }> => {
    const response = await axios.get(`${API_BASE_URL}/portfolio/${itemId}/price-history?days=${days}`)
    return response.data
  },

  getProfessionalInsights: async (): Promise<{ insights: Array<{ title: string; explanation: string }> }> => {
    const response = await axios.get(`${API_BASE_URL}/portfolio/professional-insights`)
    return response.data
  },

  getRankings: async (): Promise<PortfolioRankings> => {
    const response = await axios.get<PortfolioRankings>(`${API_BASE_URL}/portfolio/rankings`)
    return response.data
  },

}




export interface AssetSuggestion {
  id: number
  asset_type: string
  name: string
  symbol?: string
  reason: 'diversification' | 'hedge' | 'momentum'
  reason_description?: string
  correlation_with_portfolio?: number
  news_relevance_score: number
  news_count: number
  suggested_position_size_pct: number
  max_position_value?: number
  confidence_level: number
  supporting_news_ids?: number[]
  correlation_data_available: boolean
  generated_at: string
  expires_at?: string
}

export interface GenerateSuggestionsRequest {
  min_news_score?: number
  max_correlation?: number
  min_confidence?: number
  max_suggestions?: number
}

export const suggestionsApi = {
  generate: async (params?: GenerateSuggestionsRequest): Promise<{ items: AssetSuggestion[]; total: number; portfolio_value?: number }> => {
    const response = await axios.post<{ items: AssetSuggestion[]; total: number; portfolio_value?: number }>(
      `${API_BASE_URL}/suggestions/generate`,
      params || {}
    )
    return response.data
  },
  
  list: async (): Promise<{ items: AssetSuggestion[]; total: number; portfolio_value?: number }> => {
    const response = await axios.get<{ items: AssetSuggestion[]; total: number; portfolio_value?: number }>(`${API_BASE_URL}/suggestions`)
    return response.data
  },
  
  dismiss: async (id: number): Promise<void> => {
    await axios.delete(`${API_BASE_URL}/suggestions/${id}`)
  },
}







export interface BatchSummary {
  batch_number: number
  news_count: number
  summary: string
  tokens_used?: number
}

export interface SituationSummary {
  summary: string  // Mantener para compatibilidad
  meta_summary: string
  batch_summaries: BatchSummary[]
  news_count: number
  recent_news_count: number
  batches_processed: number
  total_prompt_tokens: number
  generated_at: string
  has_content: boolean
  tokens_used?: number
}

export interface PortfolioRanking {
  item_id: number
  symbol?: string
  name: string
  asset_type?: string
  composite_score: number
  sentiment_score: number
  technical_score: number
  color: 'green' | 'amber' | 'red'
  status_text: string
  action_recommendation?: string
  updated_at?: string
  thresholds?: {
    red_max: number
    amber_min: number
    amber_max: number
    green_min: number
    green_max: number
  }
  weights?: {
    sentiment: number
    technical: number
    freshness?: number
    coverage?: number
  }
  contributions?: {
    sentiment: number
    technical: number
    freshness?: number
    coverage?: number
  }
  factor_push?: {
    sentiment: number
    technical: number
  }
  data_sufficiency?: {
    sufficient: boolean
    message: string
    details?: {
      news?: string
      technical?: string
    }
    recommendation?: string
  }
  details: {
    sentiment: {
      score: number
      explanation: string
      company_news_count: number
      sector_news_count: number
      headlines: string[]
      data_quality?: 'high' | 'medium' | 'low' | 'insufficient'
      last_news_date?: string
      indicators_used?: string[]
      reliability_note?: string
      company_score?: number
      sector_score?: number
      sector_synthesis?: string
      lookback_days?: number
      company_last_date?: string
      sector_last_date?: string
      positive_count?: number
      negative_count?: number
      neutral_count?: number
      avg_sentiment?: number
    }
    technical: {
      score: number
      explanation: string
      signals: Record<string, {
        value: number
        score: number
        description: string
        indicator?: string
        period?: string
      }>
      data_quality?: 'high' | 'medium' | 'low' | 'insufficient'
      last_update?: string
      indicators_used?: string[]
      reliability_note?: string
    }
    freshness?: {
      score: number
      avg_age_hours?: number
      newest_age_hours?: number
      data_quality?: 'high' | 'medium' | 'low' | 'insufficient'
      message?: string
    }
    coverage?: {
      score: number
      news_count?: number
      technical_signals_count?: number
      data_quality?: 'high' | 'medium' | 'low' | 'insufficient'
      message?: string
    }
  }
}

export interface PortfolioRankings {
  rankings: PortfolioRanking[]
  total: number
  generated_at: string
}

export interface ScenarioData {
  driver: string
  driver_description: string
  related_news_ids: number[]
  scenarios: {
    base?: { 
      title: string
      description: string
      confidence: number
      invalidators?: Array<{ condition: string; description: string }>
    }
    risk?: { 
      title: string
      description: string
      confidence: number
      invalidators?: Array<{ condition: string; description: string }>
    }
    opportunity?: { 
      title: string
      description: string
      confidence: number
      invalidators?: Array<{ condition: string; description: string }>
    }
  }
  portfolio_mappings: Array<{
    asset_type: string
    identifier: string
    name?: string
    sensitivity: number
    confidence: number
  }>
}

export interface ScenarioEngineResponse {
  drivers: ScenarioData[]
  total_drivers: number
  total_news_analyzed: number
  generated_at: string
  partial_results: boolean
  missing_fields: string[]
  warnings: string[]
}

export const scenariosApi = {
  generate: async (params?: {
    news_ids?: number[]
    max_drivers?: number
    include_portfolio_mapping?: boolean
  }): Promise<ScenarioEngineResponse> => {
    const response = await axios.post<ScenarioEngineResponse>(
      `${API_BASE_URL}/scenarios`,
      params || {}
    )
    return response.data
  }
}


