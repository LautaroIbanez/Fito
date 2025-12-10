import { useState, useEffect } from 'react'
import { suggestionsApi, AssetSuggestion } from '../services/api'
import './AssetSuggestions.css'

export default function AssetSuggestions() {
  const [suggestions, setSuggestions] = useState<AssetSuggestion[]>([])
  const [portfolioValue, setPortfolioValue] = useState<number | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [generating, setGenerating] = useState(false)
  
  const [params, setParams] = useState({
    min_news_score: 3.0,
    max_correlation: 0.5,
    min_confidence: 0.6,
    max_suggestions: 10
  })

  useEffect(() => {
    loadSuggestions()
  }, [])

  const loadSuggestions = async () => {
    try {
      setIsLoading(true)
      setError(null)
      const data = await suggestionsApi.list()
      setSuggestions(data.items)
      setPortfolioValue(data.portfolio_value || null)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Error al cargar sugerencias')
    } finally {
      setIsLoading(false)
    }
  }

  const handleGenerate = async () => {
    try {
      setGenerating(true)
      setError(null)
      const data = await suggestionsApi.generate(params)
      setSuggestions(data.items)
      setPortfolioValue(data.portfolio_value || null)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Error al generar sugerencias')
    } finally {
      setGenerating(false)
    }
  }

  const handleDismiss = async (id: number) => {
    try {
      await suggestionsApi.dismiss(id)
      setSuggestions(suggestions.filter(s => s.id !== id))
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Error al descartar sugerencia')
    }
  }

  const getReasonIcon = (reason: string) => {
    switch (reason) {
      case 'diversification': return '📊'
      case 'hedge': return '🛡️'
      case 'momentum': return '🚀'
      default: return '💡'
    }
  }

  const getReasonLabel = (reason: string) => {
    switch (reason) {
      case 'diversification': return 'Diversificación'
      case 'hedge': return 'Hedge'
      case 'momentum': return 'Momentum'
      default: return reason
    }
  }

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.8) return '#28a745'
    if (confidence >= 0.6) return '#ffc107'
    return '#ff9800'
  }

  const getConfidenceLabel = (confidence: number) => {
    if (confidence >= 0.8) return 'Alta'
    if (confidence >= 0.6) return 'Media'
    return 'Baja'
  }

  if (isLoading && suggestions.length === 0) {
    return (
      <div className="asset-suggestions-container">
        <h2>💡 Sugerencias de Nuevos Activos</h2>
        <div className="loading">Cargando...</div>
      </div>
    )
  }

  return (
    <div className="asset-suggestions-container">
      <div className="suggestions-header">
        <h2>💡 Sugerencias de Nuevos Activos</h2>
        <button
          className="generate-button"
          onClick={handleGenerate}
          disabled={generating}
        >
          {generating ? '⏳ Generando...' : '🔄 Generar Sugerencias'}
        </button>
      </div>

      {error && (
        <div className="error-banner">
          <span>⚠️ {error}</span>
          <button onClick={() => setError(null)}>✕</button>
        </div>
      )}

      <div className="generation-params">
        <h3>Parámetros de Generación</h3>
        <div className="params-grid">
          <div className="param-item">
            <label>Score Mínimo Noticias</label>
            <input
              type="number"
              step="0.1"
              value={params.min_news_score}
              onChange={(e) => setParams({ ...params, min_news_score: parseFloat(e.target.value) })}
            />
          </div>
          <div className="param-item">
            <label>Correlación Máxima</label>
            <input
              type="number"
              step="0.1"
              min="-1"
              max="1"
              value={params.max_correlation}
              onChange={(e) => setParams({ ...params, max_correlation: parseFloat(e.target.value) })}
            />
          </div>
          <div className="param-item">
            <label>Confianza Mínima</label>
            <input
              type="number"
              step="0.1"
              min="0"
              max="1"
              value={params.min_confidence}
              onChange={(e) => setParams({ ...params, min_confidence: parseFloat(e.target.value) })}
            />
          </div>
          <div className="param-item">
            <label>Máx. Sugerencias</label>
            <input
              type="number"
              min="1"
              max="50"
              value={params.max_suggestions}
              onChange={(e) => setParams({ ...params, max_suggestions: parseInt(e.target.value) })}
            />
          </div>
        </div>
      </div>

      {suggestions.length === 0 ? (
        <div className="empty-state">
          <p>No hay sugerencias disponibles.</p>
          <p className="hint">
            Haz clic en "Generar Sugerencias" para analizar noticias recientes y encontrar nuevos activos.
          </p>
        </div>
      ) : (
        <>
          <div className="suggestions-summary">
            <p>
              <strong>{suggestions.length}</strong> sugerencia(s) basada(s) en análisis de noticias y correlación con tu cartera.
            </p>
          </div>
          
          <div className="suggestions-list">
            {suggestions.map((suggestion) => (
              <div key={suggestion.id} className="suggestion-card">
                <div className="suggestion-header">
                  <div className="suggestion-title">
                    <h3>
                      {suggestion.symbol && (
                        <span className="symbol">{suggestion.symbol}</span>
                      )}
                      {suggestion.name}
                    </h3>
                    <span className="asset-type-badge">{suggestion.asset_type}</span>
                  </div>
                  <button
                    className="dismiss-button"
                    onClick={() => handleDismiss(suggestion.id)}
                    title="Descartar sugerencia"
                  >
                    ✕
                  </button>
                </div>

                <div className="suggestion-reason">
                  <span className="reason-icon">{getReasonIcon(suggestion.reason)}</span>
                  <div className="reason-content">
                    <strong>{getReasonLabel(suggestion.reason)}</strong>
                    {suggestion.reason_description && (
                      <p>{suggestion.reason_description}</p>
                    )}
                  </div>
                </div>

                <div className="suggestion-metrics">
                  <div className="metric-item">
                    <span className="metric-label">Confianza</span>
                    <span
                      className="metric-value confidence"
                      style={{ color: getConfidenceColor(suggestion.confidence_level) }}
                    >
                      {getConfidenceLabel(suggestion.confidence_level)} ({suggestion.confidence_level.toFixed(2)})
                    </span>
                  </div>

                  <div className="metric-item">
                    <span className="metric-label">Score Noticias</span>
                    <span className="metric-value">{suggestion.news_relevance_score.toFixed(2)}</span>
                  </div>

                  <div className="metric-item">
                    <span className="metric-label">Noticias</span>
                    <span className="metric-value">{suggestion.news_count}</span>
                  </div>

                  {suggestion.correlation_with_portfolio !== undefined && suggestion.correlation_with_portfolio !== null && (
                    <div className="metric-item">
                      <span className="metric-label">Correlación</span>
                      <span className="metric-value">
                        {suggestion.correlation_with_portfolio.toFixed(2)}
                        {!suggestion.correlation_data_available && <span className="note">*</span>}
                      </span>
                    </div>
                  )}
                </div>

                <div className="suggestion-position">
                  <h4>Recomendación de Posición</h4>
                  <div className="position-details">
                    <div className="position-size">
                      <span className="position-label">Tamaño Sugerido:</span>
                      <span className="position-value">{suggestion.suggested_position_size_pct}%</span>
                    </div>
                    {suggestion.max_position_value && portfolioValue && (
                      <div className="position-value">
                        <span className="position-label">Valor Máximo:</span>
                        <span className="position-value">
                          ${suggestion.max_position_value.toLocaleString('es-ES', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                        </span>
                      </div>
                    )}
                  </div>
                  {!suggestion.correlation_data_available && (
                    <p className="correlation-note">
                      * Correlación estimada. En producción, usar datos históricos reales.
                    </p>
                  )}
                </div>

                {suggestion.supporting_news_ids && suggestion.supporting_news_ids.length > 0 && (
                  <div className="supporting-news">
                    <span className="supporting-label">Basado en {suggestion.supporting_news_ids.length} noticia(s) relevante(s)</span>
                  </div>
                )}
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  )
}


