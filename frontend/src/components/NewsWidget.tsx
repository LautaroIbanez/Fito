import { useState, useEffect } from 'react'
import { newsApi, NewsItem, NewsItemCreate } from '../services/api'
import './WidgetShared.css'
import './NewsWidget.css'

interface NewsWidgetProps {
  onUpdate?: () => void
  refreshTrigger?: number
  maxItems?: number
  sortBy?: 'score' | 'date'
}

const MIN_BODY_LENGTH = 200
const MAX_BODY_LENGTH = 10000
const MAX_TITLE_LENGTH = 200
const MAX_SOURCE_LENGTH = 100

export default function NewsWidget({ onUpdate, refreshTrigger, maxItems = 10, sortBy = 'score' }: NewsWidgetProps) {
  const [items, setItems] = useState<NewsItem[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [expandedId, setExpandedId] = useState<number | null>(null)
  const [isAdding, setIsAdding] = useState(false)
  const [isClearing, setIsClearing] = useState(false)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [formData, setFormData] = useState({
    title: '',
    body: '',
    source: '',
  })

  useEffect(() => {
    loadNews(true) // Skip onUpdate to prevent infinite loop
  }, [refreshTrigger, sortBy])

  const loadNews = async (skipUpdate = false) => {
    try {
      setIsLoading(true)
      setError(null)
      const data = await newsApi.list(sortBy)
      setItems(data.slice(0, maxItems))
      if (!skipUpdate) {
        onUpdate?.()
      }
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

  const handleAddNew = () => {
    setIsAdding(true)
    setEditingId(null)
    setFormData({ title: '', body: '', source: '' })
    setError(null)
  }

  const handleEdit = (item: NewsItem) => {
    setEditingId(item.id)
    setIsAdding(false)
    setFormData({
      title: item.title || '',
      body: item.body,
      source: item.source || '',
    })
    setError(null)
  }

  const handleDelete = async (id: number) => {
    if (!confirm('¿Estás seguro de eliminar esta noticia?')) return
    
    try {
      setError(null)
      await newsApi.delete(id)
      await loadNews(false) // Reload data after deletion
      onUpdate?.()
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Error al eliminar la noticia')
    }
  }

  const handleSave = async () => {
    const bodyLength = formData.body.trim().length
    if (bodyLength < MIN_BODY_LENGTH || bodyLength > MAX_BODY_LENGTH) {
      setError(`El cuerpo debe tener entre ${MIN_BODY_LENGTH} y ${MAX_BODY_LENGTH} caracteres`)
      return
    }

    try {
      setError(null)
      const dataToSave: NewsItemCreate = {
        title: formData.title.trim() || undefined,
        body: formData.body.trim(),
        source: formData.source.trim() || undefined,
      }
      
      if (editingId) {
        await newsApi.update(editingId, dataToSave)
      } else {
        await newsApi.create(dataToSave)
      }
      
      await loadNews(false) // Reload data after save
      setIsAdding(false)
      setEditingId(null)
      setFormData({ title: '', body: '', source: '' })
      onUpdate?.()
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Error al guardar la noticia')
    }
  }

  const handleClearAll = async () => {
    if (items.length === 0) return
    
    if (!confirm(`¿Estás seguro de eliminar todas las ${items.length} noticias? Esta acción no se puede deshacer.`)) {
      return
    }

    try {
      setIsClearing(true)
      setError(null)
      await newsApi.clearAll()
      await loadNews()
      onUpdate?.()
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Error al borrar todas las noticias')
    } finally {
      setIsClearing(false)
    }
  }

  const handleCancelAdd = () => {
    setIsAdding(false)
    setEditingId(null)
    setFormData({ title: '', body: '', source: '' })
    setError(null)
  }

  const bodyLength = formData.body.length
  const isValid = bodyLength >= MIN_BODY_LENGTH && bodyLength <= MAX_BODY_LENGTH

  if (isLoading && !isAdding) {
    return (
      <div className="news-widget" role="region" aria-label="Widget de Noticias">
        <div className="widget-header">
          <h2>📰 Noticias</h2>
          <div className="widget-actions">
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
        </div>
        <div className="loading" aria-live="polite" aria-busy="true">
          <p>Cargando noticias...</p>
        </div>
      </div>
    )
  }

  if (error && !isAdding) {
    return (
      <div className="news-widget" role="region" aria-label="Widget de Noticias">
        <div className="widget-header">
          <h2>📰 Noticias</h2>
          <div className="widget-actions">
            <button 
              className="refresh-btn" 
              onClick={loadNews}
              aria-label="Reintentar cargar noticias"
            >
              🔄
            </button>
          </div>
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

  if (items.length === 0 && !isAdding) {
    return (
      <div className="news-widget" role="region" aria-label="Widget de Noticias">
        <div className="widget-header">
          <h2>📰 Noticias</h2>
          <div className="widget-actions">
            <button 
              className="action-btn" 
              onClick={handleAddNew} 
              title="Agregar noticia"
              aria-label="Agregar nueva noticia"
              disabled={isLoading || isClearing}
            >
              ➕ Agregar
            </button>
            <button 
              className="refresh-btn" 
              onClick={loadNews}
              aria-label="Actualizar noticias"
              disabled={isLoading || isClearing}
            >
              🔄
            </button>
          </div>
        </div>
        <div className="empty-state" aria-live="polite">
          <p>No hay noticias disponibles.</p>
          <p className="hint">Agrega noticias usando el botón "Agregar" para comenzar.</p>
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
            className="action-btn" 
            onClick={handleAddNew} 
            title="Agregar noticia"
            aria-label="Agregar nueva noticia"
            disabled={isLoading || isClearing}
          >
            ➕ Agregar
          </button>
          {items.length > 0 && (
            <button 
              className="action-btn" 
              onClick={handleClearAll} 
              title="Borrar todo"
              aria-label="Borrar todas las noticias"
              disabled={isLoading || isClearing}
            >
              🗑️ Borrar todo
            </button>
          )}
          <button 
            className="refresh-btn" 
            onClick={loadNews} 
            title="Actualizar noticias"
            aria-label="Actualizar lista de noticias"
            disabled={isLoading || isClearing}
          >
            🔄
          </button>
        </div>
      </div>

      {error && (
        <div className="error-message" role="alert" aria-live="assertive">{error}</div>
      )}

      {(isAdding || editingId) && (
        <div className="news-form-card">
          <h3>{editingId ? '✏️ Editar Noticia' : '➕ Nueva Noticia'}</h3>
          <div className="news-form-grid">
            <div className="form-group full-width">
              <label>Título (opcional)</label>
              <input
                type="text"
                value={formData.title}
                onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                placeholder="Título de la noticia"
                maxLength={MAX_TITLE_LENGTH}
                disabled={isLoading}
              />
              <div className="char-count">{formData.title.length} / {MAX_TITLE_LENGTH}</div>
            </div>
            <div className="form-group full-width">
              <label>
                Cuerpo de la noticia <span className="required">*</span>
              </label>
              <textarea
                value={formData.body}
                onChange={(e) => setFormData({ ...formData, body: e.target.value })}
                placeholder="Pega aquí el texto completo de la noticia (mínimo 200 caracteres)"
                minLength={MIN_BODY_LENGTH}
                maxLength={MAX_BODY_LENGTH}
                rows={8}
                disabled={isLoading}
                className={!isValid && bodyLength > 0 ? 'error' : ''}
              />
              <div className={`char-count ${!isValid && bodyLength > 0 ? 'error' : ''}`}>
                {bodyLength} / {MAX_BODY_LENGTH}
                {bodyLength < MIN_BODY_LENGTH && bodyLength > 0 && (
                  <span className="min-required"> (mínimo {MIN_BODY_LENGTH})</span>
                )}
              </div>
            </div>
            <div className="form-group full-width">
              <label>Fuente (opcional)</label>
              <input
                type="text"
                value={formData.source}
                onChange={(e) => setFormData({ ...formData, source: e.target.value })}
                placeholder="Ej: El País, BBC News, etc."
                maxLength={MAX_SOURCE_LENGTH}
                disabled={isLoading}
              />
              <div className="char-count">{formData.source.length} / {MAX_SOURCE_LENGTH}</div>
            </div>
          </div>
          <div className="form-actions">
            <button
              className="save-button"
              onClick={handleSave}
              disabled={!isValid || isLoading}
            >
              💾 Guardar
            </button>
            <button className="cancel-button" onClick={handleCancelAdd} disabled={isLoading}>
              ✕ Cancelar
            </button>
          </div>
        </div>
      )}

      {items.length === 0 && !isAdding ? null : (
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
                  <div className="tile-actions">
                    <button
                      className="edit-news-btn"
                      onClick={() => handleEdit(item)}
                      title="Editar"
                      aria-label={`Editar noticia ${item.title || 'sin título'}`}
                      disabled={isLoading || isClearing}
                    >
                      ✏️
                    </button>
                    <button
                      className="delete-news-btn"
                      onClick={() => handleDelete(item.id)}
                      title="Eliminar"
                      aria-label={`Eliminar noticia ${item.title || 'sin título'}`}
                      disabled={isLoading || isClearing}
                    >
                      🗑️
                    </button>
                  </div>
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
      )}
    </div>
  )
}

