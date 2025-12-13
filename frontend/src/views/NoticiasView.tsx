import { useState, useEffect } from 'react'
import { newsApi, NewsItem, NewsItemCreate } from '../services/api'
import Modal from '../components/Modal'
import NewsForm from '../components/NewsForm'
import './NoticiasView.css'

export default function NoticiasView() {
  const [newsItems, setNewsItems] = useState<NewsItem[]>([])
  const [selectedItem, setSelectedItem] = useState<NewsItem | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [editingItem, setEditingItem] = useState<NewsItem | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [isCreating, setIsCreating] = useState(false)

  useEffect(() => {
    loadNews()
  }, [])

  const loadNews = async () => {
    try {
      setIsLoading(true)
      setError(null)
      const items = await newsApi.list('date')
      setNewsItems(items)
      if (items.length > 0 && !selectedItem) {
        setSelectedItem(items[0])
      } else if (items.length === 0) {
        setSelectedItem(null)
      }
    } catch (err: any) {
      console.error('Error cargando noticias:', err)
      setError(err.message || 'Error al cargar noticias')
    } finally {
      setIsLoading(false)
    }
  }

  const handleEdit = (item: NewsItem) => {
    setEditingItem(item)
    setIsCreating(false)
  }

  const handleAdd = () => {
    setEditingItem(null)
    setIsCreating(true)
  }

  const handleDelete = async (item: NewsItem) => {
    if (!confirm(`¿Estás seguro de que quieres eliminar esta noticia?`)) {
      return
    }

    try {
      await newsApi.delete(item.id)
      // Si el item eliminado era el seleccionado, limpiar selección
      if (selectedItem?.id === item.id) {
        setSelectedItem(null)
      }
      await loadNews()
    } catch (err: any) {
      console.error('Error eliminando noticia:', err)
      alert(err.message || 'Error al eliminar la noticia')
    }
  }

  const handleUpdateSubmit = async (title: string, body: string, source: string) => {
    if (!editingItem) return

    try {
      setIsSubmitting(true)
      await newsApi.update(editingItem.id, { title, body, source })
      setEditingItem(null)
      setIsCreating(false)
      await loadNews()
      // Mantener el mismo item seleccionado después de actualizar
      const updatedItems = await newsApi.list('date')
      const updatedItem = updatedItems.find(item => item.id === editingItem.id)
      if (updatedItem) {
        setSelectedItem(updatedItem)
      }
    } catch (err: any) {
      console.error('Error actualizando noticia:', err)
      throw err
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleCreateSubmit = async (title: string, body: string, source: string) => {
    try {
      setIsSubmitting(true)
      const newItem = await newsApi.create({ title, body, source })
      setEditingItem(null)
      setIsCreating(false)
      await loadNews()
      // Seleccionar el nuevo item
      setSelectedItem(newItem)
    } catch (err: any) {
      console.error('Error creando noticia:', err)
      throw err
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleCancelEdit = () => {
    setEditingItem(null)
    setIsCreating(false)
  }

  if (isLoading) {
    return (
      <div className="noticias-view loading">
        <div className="loading-spinner">⏳ Cargando noticias...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="noticias-view error">
        <div className="error-message">⚠️ {error}</div>
        <button onClick={loadNews} className="retry-button">
          Reintentar
        </button>
      </div>
    )
  }

  return (
    <div className="noticias-view">
      <header className="noticias-header">
        <h1>📰 Noticias</h1>
        <div className="header-actions">
          <button onClick={handleAdd} className="add-button">
            ➕ Agregar Noticia
          </button>
          <button onClick={loadNews} className="refresh-button">
            🔄 Actualizar
          </button>
        </div>
      </header>

      {newsItems.length === 0 && !isCreating ? (
        <div className="empty-state">
          <p>No hay noticias agregadas</p>
          <button onClick={handleAdd} className="add-button">
            ➕ Agregar tu primera noticia
          </button>
        </div>
      ) : (
        <div className="noticias-content">
          <div className="noticias-list">
            <h2>Lista de noticias ({newsItems.length})</h2>
            <div className="items-list">
              {newsItems.map((item) => (
                <div
                  key={item.id}
                  className={`item-button ${selectedItem?.id === item.id ? 'active' : ''}`}
                >
                  <button
                    onClick={() => setSelectedItem(item)}
                    style={{ 
                      width: '100%', 
                      background: 'none', 
                      border: 'none', 
                      textAlign: 'left',
                      cursor: 'pointer',
                      padding: 0
                    }}
                  >
                    <div className="item-header">
                      <strong>{item.title || 'Sin título'}</strong>
                      {item.source && (
                        <span className="item-source">{item.source}</span>
                      )}
                    </div>
                    <div className="item-preview">
                      {item.body.substring(0, 100)}...
                    </div>
                    <div className="item-meta">
                      {new Date(item.created_at).toLocaleDateString('es-ES', {
                        year: 'numeric',
                        month: 'short',
                        day: 'numeric',
                        hour: '2-digit',
                        minute: '2-digit'
                      })}
                      {item.score !== undefined && item.score !== null && (
                        <span className="item-score">Score: {item.score.toFixed(2)}</span>
                      )}
                    </div>
                  </button>
                  <div className="item-actions">
                    <button
                      className="item-action-button edit"
                      onClick={() => handleEdit(item)}
                      title="Editar noticia"
                    >
                      ✏️ Editar
                    </button>
                    <button
                      className="item-action-button delete"
                      onClick={() => handleDelete(item)}
                      title="Eliminar noticia"
                    >
                      🗑️ Eliminar
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {selectedItem && (
            <div className="noticias-details">
              <h2>{selectedItem.title || 'Sin título'}</h2>
              <div className="details-meta">
                {selectedItem.source && (
                  <div className="detail-item">
                    <span className="detail-label">Fuente</span>
                    <span className="detail-value">{selectedItem.source}</span>
                  </div>
                )}
                <div className="detail-item">
                  <span className="detail-label">Fecha</span>
                  <span className="detail-value">
                    {new Date(selectedItem.created_at).toLocaleString('es-ES')}
                  </span>
                </div>
                {selectedItem.score !== undefined && selectedItem.score !== null && (
                  <div className="detail-item">
                    <span className="detail-label">Score</span>
                    <span className="detail-value">{selectedItem.score.toFixed(2)}</span>
                  </div>
                )}
              </div>
              <div className="detail-body">
                <h3>Contenido</h3>
                <p>{selectedItem.body}</p>
              </div>
            </div>
          )}
        </div>
      )}

      {(editingItem || isCreating) && (
        <Modal
          isOpen={true}
          onClose={handleCancelEdit}
          title={isCreating ? 'Agregar nueva noticia' : `Editar noticia: ${editingItem?.title || 'Sin título'}`}
        >
          <NewsForm
            onSubmit={isCreating ? handleCreateSubmit : handleUpdateSubmit}
            isSubmitting={isSubmitting}
            initialData={editingItem ? {
              title: editingItem.title || '',
              body: editingItem.body,
              source: editingItem.source || ''
            } : undefined}
          />
        </Modal>
      )}
    </div>
  )
}

