import { NewsItem } from '../services/api'
import './NewsList.css'

interface NewsListProps {
  items: NewsItem[]
  onDelete: (id: number) => void
  isLoading: boolean
}

export default function NewsList({ items, onDelete, isLoading }: NewsListProps) {
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

  return (
    <div className="news-list-container">
      <h2>📋 Noticias Guardadas ({items.length})</h2>
      <div className="news-list">
        {items.map((item) => (
          <div key={item.id} className="news-item">
            <div className="news-item-header">
              {item.title && (
                <h3 className="news-item-title">{item.title}</h3>
              )}
              <div className="news-item-meta">
                {item.source && (
                  <span className="news-item-source">📰 {item.source}</span>
                )}
                <span className="news-item-date">{formatDate(item.created_at)}</span>
              </div>
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

