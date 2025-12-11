import { useState, useEffect } from 'react'
import { newsApi, SituationSummary } from '../services/api'
import './SituationSummary.css'

interface SituationSummaryProps {
  autoRefresh?: boolean
  onUpdate?: () => void
}

export default function SituationSummaryComponent({ autoRefresh = false, onUpdate }: SituationSummaryProps) {
  const [summary, setSummary] = useState<SituationSummary | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const loadSummary = async () => {
    try {
      setIsLoading(true)
      setError(null)
      const data = await newsApi.getSituationSummary()
      setSummary(data)
      if (onUpdate) {
        onUpdate()
      }
    } catch (err: any) {
      const errorMsg = err.response?.data?.detail || 'Error al generar resumen de situación'
      setError(errorMsg)
      setSummary(null)
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    if (autoRefresh) {
      loadSummary()
    }
  }, [autoRefresh])

  return (
    <div className="situation-summary">
      <div className="situation-summary-header">
        <h2>📊 Situación Actual</h2>
        <button
          onClick={loadSummary}
          disabled={isLoading}
          className="refresh-button"
          title="Actualizar resumen"
        >
          {isLoading ? '⏳ Generando...' : '🔄 Actualizar'}
        </button>
      </div>

      {error && (
        <div className="error-message">
          ⚠️ {error}
        </div>
      )}

      {!error && !summary && !isLoading && (
        <div className="empty-state">
          <p>💡 Haz clic en "Actualizar" para generar un resumen de la situación actual basado en las noticias.</p>
        </div>
      )}

      {!error && summary && !summary.has_content && (
        <div className="empty-state">
          <p>📰 No hay noticias disponibles para generar un resumen.</p>
          <p className="hint">Agrega algunas noticias primero para ver el resumen de la situación actual.</p>
        </div>
      )}

      {!error && summary && summary.has_content && (
        <div className="summary-content">
          <div className="summary-meta">
            <span>📰 {summary.news_count} noticia{summary.news_count !== 1 ? 's' : ''} analizada{summary.news_count !== 1 ? 's' : ''}</span>
            {summary.recent_news_count > 0 && (
              <span>• {summary.recent_news_count} reciente{summary.recent_news_count !== 1 ? 's' : ''}</span>
            )}
            {summary.generated_at && (
              <span>• Generado: {new Date(summary.generated_at).toLocaleString()}</span>
            )}
          </div>
          <div className="summary-text">
            {summary.summary.split('\n').map((paragraph, idx) => (
              paragraph.trim() && (
                <p key={idx}>{paragraph}</p>
              )
            ))}
          </div>
        </div>
      )}

      {isLoading && (
        <div className="loading-state">
          <p>⏳ Generando resumen de situación actual...</p>
        </div>
      )}
    </div>
  )
}


