import { NewsItem, NewsSummary, PortfolioImpact } from '../services/api'
import './SignalCard.css'

interface SignalCardProps {
  news: NewsItem
  summary?: NewsSummary
  impact?: PortfolioImpact
  affectedAssets?: string[]
  confidence: number
  directionality: 'positive' | 'negative' | 'neutral'
  invalidators?: string[]
}

export default function SignalCard({
  news,
  summary,
  impact,
  affectedAssets = [],
  confidence,
  directionality,
  invalidators = []
}: SignalCardProps) {
  const getDirectionalityIcon = () => {
    switch (directionality) {
      case 'positive':
        return '📈'
      case 'negative':
        return '📉'
      default:
        return '➡️'
    }
  }

  const getDirectionalityColor = () => {
    switch (directionality) {
      case 'positive':
        return 'positive'
      case 'negative':
        return 'negative'
      default:
        return 'neutral'
    }
  }

  const getConfidenceLevel = () => {
    if (confidence >= 0.8) return 'high'
    if (confidence >= 0.5) return 'medium'
    return 'low'
  }

  return (
    <div className={`signal-card ${getDirectionalityColor()}`}>
      <div className="signal-header">
        <div className="signal-title-section">
          <h3>{news.title || 'Sin título'}</h3>
          <span className="signal-direction">
            {getDirectionalityIcon()} {directionality === 'positive' ? 'Alcista' : directionality === 'negative' ? 'Bajista' : 'Neutral'}
          </span>
        </div>
        <div className="signal-meta">
          <span className={`confidence-badge ${getConfidenceLevel()}`}>
            Confianza: {Math.round(confidence * 100)}%
          </span>
          {news.source && <span className="source-badge">{news.source}</span>}
        </div>
      </div>

      {/* Qué es */}
      <div className="signal-section">
        <h4>📰 Qué es</h4>
        <p className="signal-what">
          {summary?.summary || news.body.substring(0, 200) + '...'}
        </p>
      </div>

      {/* Qué implica */}
      {(summary?.explanation || impact?.description) && (
        <div className="signal-section">
          <h4>💡 Qué implica</h4>
          <p className="signal-implication">
            {summary?.explanation || impact?.description}
          </p>
        </div>
      )}

      {/* A quién afecta */}
      {affectedAssets.length > 0 && (
        <div className="signal-section">
          <h4>🎯 A quién afecta</h4>
          <div className="affected-assets">
            {affectedAssets.map((asset, idx) => (
              <span key={idx} className="asset-tag">
                {asset}
              </span>
            ))}
          </div>
          {impact?.affected_assets && impact.affected_assets.length > 0 && (
            <p className="impact-description">{impact.description}</p>
          )}
        </div>
      )}

      {/* Invalidadores */}
      {invalidators.length > 0 && (
        <div className="signal-section invalidators">
          <h4>⚠️ Qué invalidaría esta señal</h4>
          <ul className="invalidators-list">
            {invalidators.map((invalidator, idx) => (
              <li key={idx}>{invalidator}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Score y detalles adicionales */}
      <div className="signal-footer">
        <div className="signal-score">
          <span className="score-label">Impacto:</span>
          <span className="score-value">{news.score?.toFixed(1) || 'N/A'}</span>
        </div>
        {news.score_components && (
          <details className="score-details">
            <summary>Ver componentes del score</summary>
            <div className="score-components">
              {news.score_components.ticker_matches > 0 && (
                <div className="score-component">
                  <span>Tickers mencionados: {news.score_components.ticker_matches}</span>
                </div>
              )}
              {news.score_components.category_matches > 0 && (
                <div className="score-component">
                  <span>Categorías: {news.score_components.category_matches}</span>
                </div>
              )}
              {news.score_components.sentiment_type && (
                <div className="score-component">
                  <span>Sentimiento: {news.score_components.sentiment_type}</span>
                </div>
              )}
              {news.score_components.age_days !== undefined && (
                <div className="score-component">
                  <span>Antigüedad: {news.score_components.age_days} días</span>
                </div>
              )}
            </div>
          </details>
        )}
      </div>
    </div>
  )
}
