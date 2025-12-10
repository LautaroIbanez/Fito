import { NewsItem } from '../services/api'
import './NewsList.css'

interface NewsListProps {
  items: NewsItem[]
  onDelete: (id: number) => void
  onClearAll: () => void
  isLoading: boolean
  sortBy?: 'score' | 'date'
}

export default function NewsList({ items, onDelete, onClearAll, isLoading, sortBy = 'score' }: NewsListProps) {
  const formatDate = (dateString: string) => {
    const date = new Date(dateString)
    return new Intl.DateTimeFormat('es-ES', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    }).format(date)
  }

  const handleCopy = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text)
      alert('Texto copiado al portapapeles')
    } catch (err) {
      console.error('Error al copiar:', err)
    }
  }

  if (isLoading) {
    return (
      <div className="news-list-container">
        <h2>📋 Noticias Guardadas</h2>
        <div className="loading">Cargando...</div>
      </div>
    )
  }

  if (items.length === 0) {
    return (
      <div className="news-list-container">
        <h2>📋 Noticias Guardadas</h2>
        <div className="empty-state">
          <p>No hay noticias guardadas aún.</p>
          <p className="hint">Ingresa tu primera noticia usando el formulario de arriba.</p>
        </div>
      </div>
    )
  }

  const getScoreColor = (score: number | undefined) => {
    if (!score) return '#888'
    if (score >= 5) return '#4caf50' // Verde para alta relevancia
    if (score >= 2) return '#ff9800' // Naranja para relevancia media
    return '#f44336' // Rojo para baja relevancia
  }

  const getSentimentEmoji = (sentiment?: string) => {
    switch (sentiment) {
      case 'positive': return '📈'
      case 'negative': return '📉'
      default: return '➡️'
    }
  }

  return (
    <div className="news-list-container">
      <div className="news-list-header">
        <h2>📋 Noticias Guardadas ({items.length})</h2>
        <div className="header-actions">
          {items.length > 0 && (
            <button
              className="clear-all-button"
              onClick={onClearAll}
              title="Limpiar todas las noticias"
            >
              🗑️ Limpiar Noticias
            </button>
          )}
        </div>
      </div>
      {items.length > 0 && (
        <div className="sort-info">
          <span className="sort-badge">
            Ordenado por: {sortBy === 'score' ? '⭐ Relevancia (Score)' : '📅 Fecha'}
          </span>
        </div>
      )}
      <div className="news-list">
        {items.map((item) => (
          <div 
            key={item.id} 
            className={`news-item ${item.is_obsolete ? 'obsolete-news' : ''}`}
          >
            <div className="news-item-header">
              <div className="news-item-title-row">
                {item.title && (
                  <h3 className="news-item-title">{item.title}</h3>
                )}
                {item.is_obsolete && (
                  <span className="obsolete-badge" title={`Noticia obsoleta (más de 30 días)`}>
                    ⚠️ OBSOLETA
                  </span>
                )}
              </div>
              <div className="news-item-meta">
                {item.source && (
                  <span className="news-item-source">📰 {item.source}</span>
                )}
                <span className="news-item-date">{formatDate(item.created_at)}</span>
                {item.score !== undefined && (
                  <span 
                    className="news-item-score"
                    style={{ color: getScoreColor(item.score) }}
                    title={`Score de relevancia: ${item.score.toFixed(2)}`}
                  >
                    ⭐ {item.score.toFixed(2)}
                  </span>
                )}
                {item.score_components?.sentiment_type && (
                  <span className="news-item-sentiment" title={`Sentimiento: ${item.score_components.sentiment_type}`}>
                    {getSentimentEmoji(item.score_components.sentiment_type)}
                  </span>
                )}
              </div>
              {item.score_components && (
                <div className="news-item-score-details">
                  {item.score_components.ticker_matches > 0 && (
                    <span className="score-badge ticker-badge">
                      📊 {item.score_components.ticker_matches} ticker{item.score_components.ticker_matches !== 1 ? 's' : ''}
                    </span>
                  )}
                  {item.score_components.category_matches > 0 && (
                    <span className="score-badge category-badge">
                      📈 {item.score_components.category_matches} categoría{item.score_components.category_matches !== 1 ? 's' : ''}
                    </span>
                  )}
                  {item.score_components.age_days !== undefined && (
                    <span className="score-badge age-badge">
                      ⏰ {item.score_components.age_days} día{item.score_components.age_days !== 1 ? 's' : ''}
                    </span>
                  )}
                </div>
              )}
            </div>
            <div className="news-item-body">
              {item.body.length > 300 ? (
                <>
                  {item.body.substring(0, 300)}...
                  <button
                    className="expand-button"
                    onClick={() => alert(item.body)}
                  >
                    Ver completo
                  </button>
                </>
              ) : (
                item.body
              )}
            </div>
            <div className="news-item-actions">
              <button
                className="action-button copy-button"
                onClick={() => handleCopy(item.body)}
                title="Copiar texto"
              >
                📋 Copiar
              </button>
              <button
                className="action-button delete-button"
                onClick={() => {
                  if (confirm('¿Estás seguro de eliminar esta noticia?')) {
                    onDelete(item.id)
                  }
                }}
                title="Eliminar"
              >
                🗑️ Eliminar
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

