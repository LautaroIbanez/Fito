import { useState, useEffect } from 'react'
import { portfolioApi, PortfolioItem, PortfolioItemCreate } from '../services/api'
import Modal from '../components/Modal'
import PortfolioForm from '../components/PortfolioForm'
import './ActivoView.css'

export default function ActivoView() {
  const [portfolioItems, setPortfolioItems] = useState<PortfolioItem[]>([])
  const [selectedItem, setSelectedItem] = useState<PortfolioItem | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [editingItem, setEditingItem] = useState<PortfolioItem | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  useEffect(() => {
    loadPortfolio()
  }, [])

  const loadPortfolio = async () => {
    try {
      setIsLoading(true)
      setError(null)
      const items = await portfolioApi.list()
      setPortfolioItems(items)
      if (items.length > 0 && !selectedItem) {
        setSelectedItem(items[0])
      } else if (items.length === 0) {
        setSelectedItem(null)
      }
    } catch (err: any) {
      console.error('Error cargando cartera:', err)
      setError(err.message || 'Error al cargar cartera')
    } finally {
      setIsLoading(false)
    }
  }

  const handleEdit = (item: PortfolioItem) => {
    setEditingItem(item)
  }

  const handleDelete = async (item: PortfolioItem) => {
    if (!confirm(`¿Estás seguro de que quieres eliminar "${item.name}"?`)) {
      return
    }

    try {
      await portfolioApi.delete(item.id)
      // Si el item eliminado era el seleccionado, limpiar selección
      if (selectedItem?.id === item.id) {
        setSelectedItem(null)
      }
      await loadPortfolio()
    } catch (err: any) {
      console.error('Error eliminando activo:', err)
      alert(err.message || 'Error al eliminar el activo')
    }
  }

  const handleUpdateSubmit = async (formData: PortfolioItemCreate) => {
    if (!editingItem) return

    try {
      setIsSubmitting(true)
      await portfolioApi.update(editingItem.id, formData)
      setEditingItem(null)
      await loadPortfolio()
      // Mantener el mismo item seleccionado después de actualizar
      const updatedItems = await portfolioApi.list()
      const updatedItem = updatedItems.find(item => item.id === editingItem.id)
      if (updatedItem) {
        setSelectedItem(updatedItem)
      }
    } catch (err: any) {
      console.error('Error actualizando activo:', err)
      throw err
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleCancelEdit = () => {
    setEditingItem(null)
  }

  if (isLoading) {
    return (
      <div className="activo-view loading">
        <div className="loading-spinner">⏳ Cargando activos...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="activo-view error">
        <div className="error-message">⚠️ {error}</div>
        <button onClick={loadPortfolio} className="retry-button">
          Reintentar
        </button>
      </div>
    )
  }

  return (
    <div className="activo-view">
      <header className="activo-header">
        <h1>💼 Activos y Posiciones</h1>
        <button onClick={loadPortfolio} className="refresh-button">
          🔄 Actualizar
        </button>
      </header>

      {portfolioItems.length === 0 ? (
        <div className="empty-state">
          <p>No hay activos en la cartera</p>
          <p className="hint">Agrega activos desde la vista HOY</p>
        </div>
      ) : (
        <div className="activo-content">
          <div className="activo-list">
            <h2>Selecciona un activo</h2>
            <div className="items-list">
              {portfolioItems.map((item) => (
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
                      <strong>{item.symbol || item.name}</strong>
                      <span className="item-type">{item.asset_type}</span>
                    </div>
                    {item.total_value && (
                      <div className="item-value">
                        {item.currency || 'USD'} {item.total_value}
                      </div>
                    )}
                  </button>
                  <div className="item-actions">
                    <button
                      className="item-action-button edit"
                      onClick={() => handleEdit(item)}
                      title="Editar activo"
                    >
                      ✏️ Editar
                    </button>
                    <button
                      className="item-action-button delete"
                      onClick={() => handleDelete(item)}
                      title="Eliminar activo"
                    >
                      🗑️ Eliminar
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {selectedItem && (
            <div className="activo-details">
              <h2>{selectedItem.name}</h2>
              <div className="details-grid">
                <div className="detail-item">
                  <span className="detail-label">Símbolo</span>
                  <span className="detail-value">{selectedItem.symbol || 'N/A'}</span>
                </div>
                <div className="detail-item">
                  <span className="detail-label">Tipo</span>
                  <span className="detail-value">{selectedItem.asset_type}</span>
                </div>
                {selectedItem.quantity && (
                  <div className="detail-item">
                    <span className="detail-label">Cantidad</span>
                    <span className="detail-value">{selectedItem.quantity}</span>
                  </div>
                )}
                {selectedItem.price && (
                  <div className="detail-item">
                    <span className="detail-label">Precio</span>
                    <span className="detail-value">
                      {selectedItem.currency || 'USD'} {selectedItem.price}
                    </span>
                  </div>
                )}
                {selectedItem.total_value && (
                  <div className="detail-item">
                    <span className="detail-label">Valor Total</span>
                    <span className="detail-value">
                      {selectedItem.currency || 'USD'} {selectedItem.total_value}
                    </span>
                  </div>
                )}
                {selectedItem.notes && (
                  <div className="detail-item full-width">
                    <span className="detail-label">Notas</span>
                    <span className="detail-value">{selectedItem.notes}</span>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {editingItem && (
        <Modal
          isOpen={true}
          onClose={handleCancelEdit}
          title={`Editar activo: ${editingItem.name}`}
        >
          <PortfolioForm
            onSubmit={handleUpdateSubmit}
            onCancel={handleCancelEdit}
            isSubmitting={isSubmitting}
            initialData={{
              asset_type: editingItem.asset_type,
              name: editingItem.name,
              symbol: editingItem.symbol || '',
              quantity: editingItem.quantity || '',
              price: editingItem.price || '',
              total_value: editingItem.total_value || '',
              currency: editingItem.currency || 'USD',
              notes: editingItem.notes || ''
            }}
          />
        </Modal>
      )}
    </div>
  )
}
