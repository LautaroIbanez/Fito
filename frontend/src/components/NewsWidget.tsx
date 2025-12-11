import { useState, useEffect } from 'react'
import { newsApi, NewsItem } from '../services/api'
import './WidgetShared.css'
import './NewsWidget.css'

interface NewsWidgetProps {
  onUpdate?: () => void
  refreshTrigger?: number
  maxItems?: number
  sortBy?: 'score' | 'date'
}

export default function NewsWidget({ onUpdate, refreshTrigger, maxItems = 10, sortBy = 'score' }: NewsWidgetProps) {
  const [items, setItems] = useState<NewsItem[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [expandedId, setExpandedId] = useState<number | null>(null)

  useEffect(() => {
    loadNews()
  }, [refreshTrigger, sortBy])

  const loadNews = async () => {
    try {
      setIsLoading(true)
      setError(null)
      const data = await newsApi.list(sortBy)
      setItems(data.slice(0, maxItems))
      onUpdate?.()
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Error al cargar las noticias')
    } finally {
      setIsLoading(false)
    }
  }

  const formatTime = (dateString: string) => {
    const date = new Date(dateString)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60))
    const diffDays = Math.floor(diffHours / 24)
    
    if (diffHours < 1) {
      const diffMins = Math.floor(diffMs / (1000 * 60))
      return diffMins < 1 ? 'Ahora' : `Hace ${diffMins}m`
    }
    if (diffHours < 24) {
      return `Hace ${diffHours}h`
    }
    if (diffDays === 1) {
      return 'Ayer'
    }
    if (diffDays < 7) {
      return `Hace ${diffDays}d`
    }
    return date.toLocaleDateString('es-ES', { day: 'numeric', month: 'short' })
  }

  const formatFullDate = (dateString: string) => {
    const date = new Date(dateString)
    return new Intl.DateTimeFormat('es-ES', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    }).format(date)
  }

  const getScoreColor = (score: number | undefined) => {
    if (!score) return '#888'
    if (score >= 5) return '#4caf50'
    if (score >= 2) return '#ff9800'
    return '#f44336'
  }

  const getSentimentEmoji = (sentiment?: string) => {
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

  const getLeadText = (body: string, maxLength: number = 150) => {
    if (body.length <= maxLength) return body
    const truncated = body.substring(0, maxLength)
    const lastSpace = truncated.lastIndexOf(' ')
    return lastSpace > 0 ? truncated.substring(0, lastSpace) + '...' : truncated + '...'
  }

  const getTickers = (item: NewsItem): string[] => {
    const tickers: string[] = []
    if (item.score_components?.ticker_matches && item.score_components.ticker_matches > 0) {
      const tickerPattern = /\b([A-Z]{1,5})(?:\.[A-Z]{1,2})?\b/g
      const text = `${item.title || ''} ${item.body}`.toUpperCase()
      const matches = text.match(tickerPattern)
      if (matches) {
        const uniqueTickers = [...new Set(matches)].slice(0, 5)
        tickers.push(...uniqueTickers)
      }
    }
    return tickers
  }

  const getSectors = (item: NewsItem): string[] => {
    const sectors: string[] = []
    if (item.score_components?.category_matches && item.score_components.category_matches > 0) {
      const commonSectors = ['TECH', 'FINANCE', 'ENERGY', 'HEALTHCARE', 'CONSUMER', 'INDUSTRIAL', 'MATERIALS', 'REAL ESTATE', 'UTILITIES']
      const text = `${item.title || ''} ${item.body}`.toUpperCase()
      commonSectors.forEach(sector => {
        if (text.includes(sector)) {
          sectors.push(sector)
        }
      })
    }
    return sectors
  }

  if (isLoading) {
    return (
      <div className="news-widget" role="region" aria-label="Widget de Noticias">
        <div className="widget-header">
          <h2>📰 Noticias</h2>
          <button 
            className="refresh-btn" 
            onClick={loadNews} 
            disabled
            aria-label="Actualizar noticias"
            aria-busy="true"
          >
            🔄
          </button>
        </div>
        <div className="loading" aria-live="polite" aria-busy="true">
          <p>Cargando noticias...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="news-widget" role="region" aria-label="Widget de Noticias">
        <div className="widget-header">
          <h2>📰 Noticias</h2>
          <button 
            className="refresh-btn" 
            onClick={loadNews}
            aria-label="Reintentar cargar noticias"
          >
            🔄
          </button>
        </div>
        <div className="error-message" role="alert" aria-live="assertive">{error}</div>
        <button 
          className="retry-button" 
          onClick={loadNews}
          aria-label="Reintentar cargar noticias"
        >
          Reintentar
        </button>
      </div>
    )
  }

  if (items.length === 0) {
    return (
      <div className="news-widget" role="region" aria-label="Widget de Noticias">
        <div className="widget-header">
          <h2>📰 Noticias</h2>
          <button 
            className="refresh-btn" 
            onClick={loadNews}
            aria-label="Actualizar noticias"
          >
            🔄
          </button>
        </div>
        <div className="empty-state" aria-live="polite">
          <p>No hay noticias disponibles.</p>
          <p className="hint">Agrega noticias usando el formulario para comenzar.</p>
        </div>
      </div>
    )
  }

  return (
    <div className="news-widget" role="region" aria-label="Widget de Noticias">
      <div className="widget-header">
        <h2>📰 Noticias ({items.length})</h2>
        <div className="widget-actions">
          <button 
            className="refresh-btn" 
            onClick={loadNews} 
            title="Actualizar noticias"
            aria-label="Actualizar lista de noticias"
          >
            🔄
          </button>
        </div>
      </div>

      <div className="news-tiles">
        {items.map((item) => {
          const isExpanded = expandedId === item.id
          const tickers = getTickers(item)
          const sectors = getSectors(item)
          const leadText = isExpanded ? item.body : getLeadText(item.body)

          return (
            <div
              key={item.id}
              className={`news-tile ${item.is_obsolete ? 'obsolete' : ''} ${isExpanded ? 'expanded' : ''}`}
              data-news-id={item.id}
              data-score={item.score || ''}
              data-sentiment={item.score_components?.sentiment_type || ''}
              data-tickers={tickers.join(',')}
              data-sectors={sectors.join(',')}
              data-body={item.body}
              data-title={item.title || ''}
              data-source={item.source || ''}
              data-created-at={item.created_at}
              data-ticker-matches={item.score_components?.ticker_matches || 0}
              data-category-matches={item.score_components?.category_matches || 0}
              data-age-days={item.score_components?.age_days || 0}
            >
              <div className="tile-header">
                <div className="tile-title-row">
                  {item.title ? (
                    <h3 className="tile-title">{item.title}</h3>
                  ) : (
                    <h3 className="tile-title no-title">Sin título</h3>
                  )}
                  {item.is_obsolete && (
                    <span className="obsolete-badge" title="Noticia obsoleta (más de 30 días)">⚠️</span>
                  )}
                </div>
                <div className="tile-meta">
                  {item.source && (
                    <span className="tile-source" title={`Fuente: ${item.source}`}>📰 {item.source}</span>
                  )}
                  <span className="tile-time" title={formatFullDate(item.created_at)}>
                    {formatTime(item.created_at)}
                  </span>
                  {item.score !== undefined && (
                    <span
                      className="tile-score"
                      style={{ color: getScoreColor(item.score) }}
                      title={`Score de relevancia: ${item.score.toFixed(2)}`}
                    >
                      ⭐ {item.score.toFixed(1)}
                    </span>
                  )}
                  {item.score_components?.sentiment_type && (
                    <span
                      className="tile-sentiment"
                      title={`Sentimiento: ${item.score_components.sentiment_type}`}
                    >
                      {getSentimentEmoji(item.score_components.sentiment_type)}
                    </span>
                  )}
                </div>
              </div>

              <div className="tile-body">
                <p className="tile-lead">{leadText}</p>
                {(tickers.length > 0 || sectors.length > 0) && (
                  <div className="tile-tags">
                    {tickers.length > 0 && (
                      <div className="tag-group">
                        <span className="tag-label">Tickers:</span>
                        {tickers.map((ticker, idx) => (
                          <span key={idx} className="tag ticker-tag" title={`Ticker: ${ticker}`}>
                            {ticker}
                          </span>
                        ))}
                      </div>
                    )}
                    {sectors.length > 0 && (
                      <div className="tag-group">
                        <span className="tag-label">Sectores:</span>
                        {sectors.map((sector, idx) => (
                          <span key={idx} className="tag sector-tag" title={`Sector: ${sector}`}>
                            {sector}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                )}
                {item.score_components && (
                  <div className="tile-score-details">
                    {item.score_components.ticker_matches !== undefined && item.score_components.ticker_matches > 0 && (
                      <span className="score-badge" title={`${item.score_components.ticker_matches} ticker(s) mencionado(s)`}>
                        📊 {item.score_components.ticker_matches}
                      </span>
                    )}
                    {item.score_components.category_matches !== undefined && item.score_components.category_matches > 0 && (
                      <span className="score-badge" title={`${item.score_components.category_matches} categoría(s) mencionada(s)`}>
                        📈 {item.score_components.category_matches}
                      </span>
                    )}
                    {item.score_components.age_days !== undefined && (
                      <span className="score-badge" title={`${item.score_components.age_days} día(s) de antigüedad`}>
                        ⏰ {item.score_components.age_days}d
                      </span>
                    )}
                  </div>
                )}
              </div>

              {item.body.length > 150 && (
                <button
                  className="expand-button"
                  onClick={() => setExpandedId(isExpanded ? null : item.id)}
                >
                  {isExpanded ? '▲ Ocultar' : '▼ Ver completo'}
                </button>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

