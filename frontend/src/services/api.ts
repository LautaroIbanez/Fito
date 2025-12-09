import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8001/api'

export interface NewsItem {
  id: number
  title?: string
  body: string
  source?: string
  created_at: string
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

export const newsApi = {
  create: async (newsItem: NewsItemCreate): Promise<NewsItem> => {
    const response = await axios.post<NewsItem>(`${API_BASE_URL}/news`, newsItem)
    return response.data
  },

  list: async (): Promise<NewsItem[]> => {
    const response = await axios.get<{ items: NewsItem[]; total: number }>(`${API_BASE_URL}/news`)
    return response.data.items
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
}

