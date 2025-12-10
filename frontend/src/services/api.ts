import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8001/api'

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

export const newsApi = {
  create: async (newsItem: NewsItemCreate): Promise<NewsItem> => {
    const response = await axios.post<NewsItem>(`${API_BASE_URL}/news`, newsItem)
    return response.data
  },

  list: async (sortBy: 'score' | 'date' = 'score'): Promise<NewsItem[]> => {
    const response = await axios.get<{ items: NewsItem[]; total: number }>(`${API_BASE_URL}/news?sort_by=${sortBy}`)
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

export interface AlertTrigger {
  id: number
  name: string
  symbol?: string
  asset_type?: string
  price_trigger_type: 'intraday_change' | 'gap' | 'absolute'
  price_threshold?: number
  gap_threshold?: number
  require_recent_news: boolean
  news_relevance_threshold: number
  news_max_age_hours: number
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface AlertTriggerCreate {
  name: string
  symbol?: string
  asset_type?: string
  price_trigger_type: 'intraday_change' | 'gap' | 'absolute'
  price_threshold?: number
  gap_threshold?: number
  require_recent_news: boolean
  news_relevance_threshold: number
  news_max_age_hours: number
}

export interface AlertHistory {
  id: number
  trigger_id: number
  trigger_name?: string
  symbol?: string
  asset_name?: string
  price_condition_met: boolean
  news_condition_met: boolean
  price_value?: number
  price_change_percent?: number
  gap_percent?: number
  relevant_news_count: number
  highest_news_score?: number
  alert_summary: string
  expected_impact?: string
  suggested_action?: string
  triggered_at: string
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

  getRiskDashboard: async (topN: number = 5): Promise<RiskDashboard> => {
    const response = await axios.get<RiskDashboard>(`${API_BASE_URL}/portfolio/risk-dashboard?top_n=${topN}`)
    return response.data
  },
}

export const alertsApi = {
  // Triggers
  createTrigger: async (trigger: AlertTriggerCreate): Promise<AlertTrigger> => {
    const response = await axios.post<AlertTrigger>(`${API_BASE_URL}/alerts/triggers`, trigger)
    return response.data
  },
  
  listTriggers: async (isActive?: boolean): Promise<AlertTrigger[]> => {
    const params = isActive !== undefined ? `?is_active=${isActive}` : ''
    const response = await axios.get<{ items: AlertTrigger[]; total: number }>(`${API_BASE_URL}/alerts/triggers${params}`)
    return response.data.items
  },
  
  getTrigger: async (id: number): Promise<AlertTrigger> => {
    const response = await axios.get<AlertTrigger>(`${API_BASE_URL}/alerts/triggers/${id}`)
    return response.data
  },
  
  updateTrigger: async (id: number, updates: Partial<AlertTriggerCreate> & { is_active?: boolean }): Promise<AlertTrigger> => {
    const response = await axios.put<AlertTrigger>(`${API_BASE_URL}/alerts/triggers/${id}`, updates)
    return response.data
  },
  
  deleteTrigger: async (id: number): Promise<void> => {
    await axios.delete(`${API_BASE_URL}/alerts/triggers/${id}`)
  },
  
  // Alert History
  getAlertHistory: async (skip: number = 0, limit: number = 50, triggerId?: number): Promise<{ items: AlertHistory[]; total: number }> => {
    const params = new URLSearchParams()
    params.append('skip', skip.toString())
    params.append('limit', limit.toString())
    if (triggerId) params.append('trigger_id', triggerId.toString())
    const response = await axios.get<{ items: AlertHistory[]; total: number }>(`${API_BASE_URL}/alerts/history?${params}`)
    return response.data
  },
  
  checkTriggers: async (): Promise<{ items: AlertHistory[]; total: number }> => {
    const response = await axios.post<{ items: AlertHistory[]; total: number }>(`${API_BASE_URL}/alerts/check`)
    return response.data
  },
}

export interface BacktestRule {
  id: number
  name: string
  description?: string
  news_sentiment_required: 'positive' | 'negative' | 'any'
  news_min_score: number
  news_max_age_hours: number
  price_change_condition?: 'drop_before' | 'rise_before' | 'none'
  price_change_threshold?: number
  hold_period_days: number
  position_size_pct: number
  start_date?: string
  end_date?: string
  created_at: string
  updated_at: string
}

export interface BacktestRuleCreate {
  name: string
  description?: string
  news_sentiment_required: 'positive' | 'negative' | 'any'
  news_min_score: number
  news_max_age_hours: number
  price_change_condition?: 'drop_before' | 'rise_before' | 'none'
  price_change_threshold?: number
  hold_period_days: number
  position_size_pct: number
  start_date?: string
  end_date?: string
}

export interface EquityCurvePoint {
  date: string
  equity: number
  drawdown: number
}

export interface BacktestResult {
  id: number
  rule_id: number
  rule_name?: string
  total_trades: number
  winning_trades: number
  losing_trades: number
  win_rate: number
  total_pnl: number
  total_pnl_pct: number
  average_win: number
  average_loss: number
  max_drawdown: number
  max_drawdown_pct: number
  equity_curve: EquityCurvePoint[]
  executed_start_date?: string
  executed_end_date?: string
  created_at: string
}

export const backtestApi = {
  // Rules
  createRule: async (rule: BacktestRuleCreate): Promise<BacktestRule> => {
    const response = await axios.post<BacktestRule>(`${API_BASE_URL}/backtest/rules`, rule)
    return response.data
  },
  
  listRules: async (): Promise<BacktestRule[]> => {
    const response = await axios.get<{ items: BacktestRule[]; total: number }>(`${API_BASE_URL}/backtest/rules`)
    return response.data.items
  },
  
  getRule: async (id: number): Promise<BacktestRule> => {
    const response = await axios.get<BacktestRule>(`${API_BASE_URL}/backtest/rules/${id}`)
    return response.data
  },
  
  deleteRule: async (id: number): Promise<void> => {
    await axios.delete(`${API_BASE_URL}/backtest/rules/${id}`)
  },
  
  // Execution
  executeBacktest: async (ruleId: number, initialCapital: number = 10000): Promise<BacktestResult> => {
    const response = await axios.post<BacktestResult>(`${API_BASE_URL}/backtest/execute`, {
      rule_id: ruleId,
      initial_capital: initialCapital
    })
    return response.data
  },
  
  // Results
  listResults: async (ruleId?: number): Promise<{ items: BacktestResult[]; total: number }> => {
    const params = ruleId ? `?rule_id=${ruleId}` : ''
    const response = await axios.get<{ items: BacktestResult[]; total: number }>(`${API_BASE_URL}/backtest/results${params}`)
    return response.data
  },
  
  getResult: async (id: number): Promise<BacktestResult> => {
    const response = await axios.get<BacktestResult>(`${API_BASE_URL}/backtest/results/${id}`)
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

export interface AssetThesis {
  id: number
  portfolio_item_id: number
  portfolio_item_name?: string
  portfolio_item_symbol?: string
  thesis_text: string
  entry_reason?: string
  target_price?: string
  stop_loss?: string
  time_horizon?: string
  linked_news: NewsLink[]
  checklist_items: ChecklistItem[]
  created_at: string
  updated_at: string
}

export interface AssetThesisCreate {
  portfolio_item_id: number
  thesis_text: string
  entry_reason?: string
  target_price?: string
  stop_loss?: string
  time_horizon?: string
}

export interface NewsLink {
  id: number
  thesis_id: number
  news_item_id: number
  news_title?: string
  news_body_preview?: string
  relevance_note?: string
  is_key_news: boolean
  linked_at: string
}

export interface NewsLinkCreate {
  news_item_id: number
  relevance_note?: string
  is_key_news: boolean
}

export interface ChecklistItem {
  id: number
  thesis_id: number
  title: string
  description?: string
  order_index: number
  is_completed: boolean
  completed_at?: string
  completed_notes?: string
  created_at: string
  updated_at: string
}

export interface ChecklistItemCreate {
  title: string
  description?: string
  order_index: number
}

export interface ChecklistItemUpdate {
  title?: string
  description?: string
  order_index?: number
  is_completed?: boolean
  completed_notes?: string
}

export const thesisApi = {
  create: async (thesis: AssetThesisCreate): Promise<AssetThesis> => {
    const response = await axios.post<AssetThesis>(`${API_BASE_URL}/thesis`, thesis)
    return response.data
  },
  
  list: async (portfolioItemId?: number): Promise<AssetThesis[]> => {
    const params = portfolioItemId ? `?portfolio_item_id=${portfolioItemId}` : ''
    const response = await axios.get<{ items: AssetThesis[]; total: number }>(`${API_BASE_URL}/thesis${params}`)
    return response.data.items
  },
  
  get: async (id: number): Promise<AssetThesis> => {
    const response = await axios.get<AssetThesis>(`${API_BASE_URL}/thesis/${id}`)
    return response.data
  },
  
  update: async (id: number, updates: Partial<AssetThesisCreate>): Promise<AssetThesis> => {
    const response = await axios.put<AssetThesis>(`${API_BASE_URL}/thesis/${id}`, updates)
    return response.data
  },
  
  delete: async (id: number): Promise<void> => {
    await axios.delete(`${API_BASE_URL}/thesis/${id}`)
  },
  
  linkNews: async (thesisId: number, link: NewsLinkCreate): Promise<NewsLink> => {
    const response = await axios.post<NewsLink>(`${API_BASE_URL}/thesis/${thesisId}/news`, link)
    return response.data
  },
  
  unlinkNews: async (thesisId: number, linkId: number): Promise<void> => {
    await axios.delete(`${API_BASE_URL}/thesis/${thesisId}/news/${linkId}`)
  },
  
  createChecklistItem: async (thesisId: number, item: ChecklistItemCreate): Promise<ChecklistItem> => {
    const response = await axios.post<ChecklistItem>(`${API_BASE_URL}/thesis/${thesisId}/checklist`, item)
    return response.data
  },
  
  updateChecklistItem: async (itemId: number, updates: ChecklistItemUpdate): Promise<ChecklistItem> => {
    const response = await axios.put<ChecklistItem>(`${API_BASE_URL}/thesis/checklist/${itemId}`, updates)
    return response.data
  },
  
  deleteChecklistItem: async (itemId: number): Promise<void> => {
    await axios.delete(`${API_BASE_URL}/thesis/checklist/${itemId}`)
  },
}

export interface DynamicLimit {
  id: number
  portfolio_item_id: number
  portfolio_item_name?: string
  portfolio_item_symbol?: string
  asset_type?: string
  current_position_pct: number
  recent_drawdown_pct?: number
  realized_volatility?: number
  implied_volatility?: number
  max_position_pct: number
  suggested_stop_loss_pct?: number
  risk_adjusted_size_pct: number
  is_exceeded: boolean
  excess_amount_pct: number
  suggested_reduction_pct: number
  current_value?: number
  calculated_at: string
  next_calculation_at?: string
}

export const limitsApi = {
  calculate: async (force: boolean = false): Promise<{ items: DynamicLimit[]; total: number; exceeded_count: number }> => {
    const response = await axios.post<{ items: DynamicLimit[]; total: number; exceeded_count: number }>(
      `${API_BASE_URL}/limits/calculate?force=${force}`
    )
    return response.data
  },
  
  list: async (exceededOnly: boolean = false): Promise<{ items: DynamicLimit[]; total: number; exceeded_count: number }> => {
    const params = exceededOnly ? '?exceeded_only=true' : ''
    const response = await axios.get<{ items: DynamicLimit[]; total: number; exceeded_count: number }>(`${API_BASE_URL}/limits${params}`)
    return response.data
  },
  
  getForItem: async (portfolioItemId: number): Promise<DynamicLimit> => {
    const response = await axios.get<DynamicLimit>(`${API_BASE_URL}/limits/${portfolioItemId}`)
    return response.data
  },
}

export interface DecisionLog {
  id: number
  portfolio_item_id: number
  portfolio_item_name?: string
  portfolio_item_symbol?: string
  decision_type: 'buy' | 'sell' | 'hold'
  reason: string
  signal_type: 'news' | 'price' | 'both' | 'analysis' | 'other'
  signal_reference?: string
  expected_direction?: 'up' | 'down' | 'neutral'
  expected_price?: string
  expected_timeframe_days?: number
  expected_outcome?: string
  status: 'pending' | 'evaluated' | 'cancelled'
  evaluation_window_days: number
  decided_at: string
  evaluated_at?: string
  evaluation?: DecisionEvaluation
}

export interface DecisionEvaluation {
  id: number
  decision_id: number
  price_at_decision?: number
  price_at_evaluation?: number
  result: 'hit' | 'miss' | 'partial'
  price_change_pct?: number
  outcome_match?: boolean
  evaluation_notes?: string
  lessons_learned?: string
  evaluated_at: string
}

export interface DecisionLogCreate {
  portfolio_item_id: number
  decision_type: 'buy' | 'sell' | 'hold'
  reason: string
  signal_type: 'news' | 'price' | 'both' | 'analysis' | 'other'
  signal_reference?: string
  expected_direction?: 'up' | 'down' | 'neutral'
  expected_price?: string
  expected_timeframe_days?: number
  expected_outcome?: string
  evaluation_window_days?: number
}

export interface DecisionStatistics {
  overall: {
    total_decisions: number
    pending_decisions: number
    evaluated_decisions: number
    total_hits: number
    total_misses: number
    total_partials: number
    overall_hit_rate: number
    avg_price_change_pct: number
  }
  by_signal_type: Record<string, {
    total: number
    hits: number
    misses: number
    partials: number
    hit_rate: number
    avg_price_change_pct: number
  }>
  by_decision_type: Record<string, {
    total: number
    hits: number
    misses: number
    partials: number
    hit_rate: number
  }>
}

export const decisionsApi = {
  create: async (decision: DecisionLogCreate): Promise<DecisionLog> => {
    const response = await axios.post<DecisionLog>(`${API_BASE_URL}/decisions`, decision)
    return response.data
  },
  
  list: async (filters?: {
    portfolio_item_id?: number
    status?: 'pending' | 'evaluated' | 'cancelled'
    signal_type?: string
    decision_type?: 'buy' | 'sell' | 'hold'
  }): Promise<{ items: DecisionLog[]; total: number; pending_count: number; evaluated_count: number }> => {
    const params = new URLSearchParams()
    if (filters?.portfolio_item_id) params.append('portfolio_item_id', filters.portfolio_item_id.toString())
    if (filters?.status) params.append('status_filter', filters.status)
    if (filters?.signal_type) params.append('signal_type', filters.signal_type)
    if (filters?.decision_type) params.append('decision_type', filters.decision_type)
    
    const query = params.toString()
    const response = await axios.get<{ items: DecisionLog[]; total: number; pending_count: number; evaluated_count: number }>(
      `${API_BASE_URL}/decisions${query ? `?${query}` : ''}`
    )
    return response.data
  },
  
  get: async (id: number): Promise<DecisionLog> => {
    const response = await axios.get<DecisionLog>(`${API_BASE_URL}/decisions/${id}`)
    return response.data
  },
  
  evaluate: async (id: number, force: boolean = false): Promise<DecisionEvaluation> => {
    const response = await axios.post<DecisionEvaluation>(`${API_BASE_URL}/decisions/${id}/evaluate?force=${force}`)
    return response.data
  },
  
  evaluatePending: async (forceAll: boolean = false): Promise<{ evaluated_count: number; message: string }> => {
    const response = await axios.post<{ evaluated_count: number; message: string }>(
      `${API_BASE_URL}/decisions/evaluate-pending?force_all=${forceAll}`
    )
    return response.data
  },
  
  updateEvaluation: async (evaluationId: number, updates: { evaluation_notes?: string; lessons_learned?: string }): Promise<DecisionEvaluation> => {
    const response = await axios.put<DecisionEvaluation>(`${API_BASE_URL}/decisions/evaluation/${evaluationId}`, updates)
    return response.data
  },
  
  getStatistics: async (): Promise<DecisionStatistics> => {
    const response = await axios.get<DecisionStatistics>(`${API_BASE_URL}/decisions/statistics/overview`)
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
    var_90d_95: number
    var_30d_99: number
    var_90d_99: number
    portfolio_value: number
  }
}

