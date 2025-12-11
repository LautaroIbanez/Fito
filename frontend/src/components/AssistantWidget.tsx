import { useState } from 'react'
import { newsApi, NewsSummariesResponse, NewsSummary, PortfolioImpact, Suggestion } from '../services/api'
import './WidgetShared.css'
import './AssistantWidget.css'

interface AssistantWidgetProps {
  onUpdate?: () => void
  refreshTrigger?: number
  maxItems?: number
}

export default function AssistantWidget({ onUpdate, refreshTrigger, maxItems = 10 }: AssistantWidgetProps) {
  const [data, setData] = useState<NewsSummariesResponse | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [isDegraded, setIsDegraded] = useState(false)

  // Removed automatic analysis on load - analysis now runs only when "Analizar" button is clicked

  const loadSummaries = async () => {
    try {
      setIsLoading(true)
      setError(null)
      setIsDegraded(false)
      const response = await newsApi.getNewsSummaries(maxItems)
      setData(response)
      onUpdate?.()
    } catch (err: any) {
      const errorMsg = err.response?.data?.detail || 'Error al generar análisis del asistente'
      setError(errorMsg)
      setIsDegraded(true)
      // En modo degradado, aún intentamos mostrar datos básicos si están disponibles
      setData(null)
    } finally {
      setIsLoading(false)
    }
  }

  const getSentimentEmoji = (sentiment: string) => {
    switch (sentiment?.toLowerCase()) {
      case 'positive':
      case 'bullish':
        return '📈'
      case 'negative':
      case 'bearish':
        return '📉'
      default:
        return '➡️'
    }
  }

  const getImpactIcon = (type: string) => {
    switch (type) {
      case 'positive':
        return '✅'
      case 'negative':
        return '⚠️'
      default:
        return '➡️'
    }
  }

  const getActionIcon = (action: string) => {
    switch (action) {
      case 'add':
        return '➕'
      case 'watch':
        return '👁️'
      case 'trim':
        return '✂️'
      case 'exit':
        return '🚪'
      default:
        return '📋'
    }
  }

  const getToneColor = (tone: string) => {
    switch (tone) {
      case 'positive':
        return '#4caf50'
      case 'negative':
        return '#f44336'
      case 'neutral':
        return '#666'
      default:
        return '#888'
    }
  }

  if (isLoading) {
    return (
      <div className="assistant-widget" role="region" aria-label="Widget del Asistente IA">
        <div className="widget-header">
          <h2>🤖 Asistente IA</h2>
          <div className="widget-actions">
            <button 
              className="action-btn" 
              onClick={loadSummaries} 
              disabled
              aria-label="Analizar"
              aria-busy="true"
            >
              🔍 Analizar
            </button>
            <button 
              className="refresh-btn" 
              onClick={loadSummaries} 
              disabled
              aria-label="Actualizar análisis"
              aria-busy="true"
            >
              🔄
            </button>
          </div>
        </div>
        <div className="loading" aria-live="polite" aria-busy="true">
          <div className="spinner" aria-hidden="true"></div>
          <p>Generando análisis...</p>
        </div>
      </div>
    )
  }

  if (error && !data) {
    return (
      <div className="assistant-widget" role="region" aria-label="Widget del Asistente IA">
        <div className="widget-header">
          <h2>🤖 Asistente IA</h2>
          <div className="widget-actions">
            <button 
              className="action-btn" 
              onClick={loadSummaries}
              aria-label="Analizar"
            >
              🔍 Analizar
            </button>
            <button 
              className="refresh-btn" 
              onClick={loadSummaries}
              aria-label="Reintentar cargar análisis"
            >
              🔄
            </button>
          </div>
        </div>
        <div className="degraded-state" role="alert" aria-live="assertive">
          <div className="degraded-icon" aria-hidden="true">⚠️</div>
          <p className="degraded-title">Servicio no disponible</p>
          <p className="degraded-message">
            El asistente IA no está disponible temporalmente. El resto de los widgets funcionan normalmente.
          </p>
          <button 
            className="retry-button" 
            onClick={loadSummaries}
            aria-label="Reintentar cargar análisis del asistente IA"
          >
            Reintentar
          </button>
        </div>
      </div>
    )
  }

  if (!data || data.summaries.length === 0) {
    return (
      <div className="assistant-widget" role="region" aria-label="Widget del Asistente IA">
        <div className="widget-header">
          <h2>🤖 Asistente IA</h2>
          <div className="widget-actions">
            <button 
              className="action-btn" 
              onClick={loadSummaries}
              aria-label="Analizar"
              disabled={isLoading}
            >
              🔍 Analizar
            </button>
            <button 
              className="refresh-btn" 
              onClick={loadSummaries}
              aria-label="Actualizar análisis"
              disabled={isLoading}
            >
              🔄
            </button>
          </div>
        </div>
        <div className="empty-state" aria-live="polite">
          <p>No hay análisis disponible.</p>
          <p className="hint">Haz clic en "Analizar" para generar un análisis de las noticias actuales.</p>
        </div>
      </div>
    )
  }

  return (
    <div className="assistant-widget" role="region" aria-label="Widget del Asistente IA">
      <div className="widget-header">
        <h2>🤖 Asistente IA</h2>
        <div className="widget-actions">
          <button 
            className="action-btn" 
            onClick={loadSummaries} 
            title="Analizar"
            aria-label="Analizar noticias"
            disabled={isLoading}
          >
            🔍 Analizar
          </button>
          <button 
            className="refresh-btn" 
            onClick={loadSummaries} 
            title="Actualizar análisis"
            aria-label="Actualizar análisis del asistente IA"
            disabled={isLoading}
          >
            🔄
          </button>
        </div>
      </div>

      {isDegraded && (
        <div className="degraded-banner">
          <span>⚠️ Modo degradado: Algunos análisis pueden estar incompletos</span>
        </div>
      )}

      <div className="widget-content">
        <div className="summaries-section">
          <h3>📰 Resúmenes por Noticia</h3>
          <div className="summaries-list">
            {data.summaries.map((summary: NewsSummary) => (
              <div key={summary.news_id} className="summary-item">
                <div className="summary-header">
                  <h4 className="summary-title">{summary.news_title}</h4>
                  <div className="summary-meta">
                    {summary.sentiment && (
                      <span className="sentiment-badge" title={`Sentimiento: ${summary.sentiment}`}>
                        {getSentimentEmoji(summary.sentiment)}
                      </span>
                    )}
                    {summary.score !== undefined && (
                      <span className="score-badge" title={`Score: ${summary.score.toFixed(2)}`}>
                        ⭐ {summary.score.toFixed(1)}
                      </span>
                    )}
                  </div>
                </div>
                <div className="summary-content">
                  <div className="summary-text">
                    <strong>Resumen:</strong> {summary.summary}
                  </div>
                  {summary.explanation && (
                    <div className="explanation-text">
                      <strong>Explicación:</strong> {summary.explanation}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>

        {(data.portfolio_impacts.length > 0 || data.suggestions.length > 0) && (
          <div className="impacts-section">
            <h3>💼 Impactos en Cartera</h3>
            
            {data.portfolio_impacts.length > 0 && (
              <div className="impacts-list">
                {data.portfolio_impacts.map((impact: PortfolioImpact, idx: number) => (
                  <div key={idx} className="impact-item" data-impact-type={impact.type}>
                    <div className="impact-header">
                      <span className="impact-icon">{getImpactIcon(impact.type)}</span>
                      <span className="impact-type">{impact.type.toUpperCase()}</span>
                    </div>
                    <p className="impact-description">{impact.description}</p>
                    {impact.affected_assets && impact.affected_assets.length > 0 && (
                      <div className="affected-assets">
                        <strong>Activos afectados:</strong> {impact.affected_assets.join(', ')}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}

            {data.suggestions.length > 0 && (
              <div className="suggestions-list">
                <h4>Sugerencias de Acción</h4>
                {data.suggestions.map((suggestion: Suggestion, idx: number) => (
                  <div key={idx} className="suggestion-item" style={{ borderLeftColor: getToneColor(suggestion.tone) }}>
                    <div className="suggestion-header">
                      <span className="suggestion-icon">{getActionIcon(suggestion.action)}</span>
                      <span className="suggestion-action">{suggestion.action.toUpperCase()}</span>
                      <span 
                        className="suggestion-tone" 
                        style={{ color: getToneColor(suggestion.tone) }}
                      >
                        {suggestion.tone}
                      </span>
                    </div>
                    <p className="suggestion-description">{suggestion.description}</p>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {data.portfolio_impacts.length === 0 && data.suggestions.length === 0 && (
          <div className="no-impacts">
            <p>No se detectaron impactos específicos en la cartera actual.</p>
          </div>
        )}
      </div>
    </div>
  )
}

