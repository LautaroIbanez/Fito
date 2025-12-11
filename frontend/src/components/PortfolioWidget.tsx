import { useState, useEffect } from 'react'
import { portfolioApi, PortfolioItem, PortfolioItemCreate } from '../services/api'
import './WidgetShared.css'
import './PortfolioWidget.css'

const ASSET_TYPES = ['acciones', 'bonos', 'etf', 'fondos', 'divisas', 'otros']

interface PortfolioWidgetProps {
  onUpdate?: () => void
  refreshTrigger?: number
}

export default function PortfolioWidget({ onUpdate, refreshTrigger }: PortfolioWidgetProps) {
  const [items, setItems] = useState<PortfolioItem[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [isAdding, setIsAdding] = useState(false)
  const [isClearing, setIsClearing] = useState(false)
  const [formData, setFormData] = useState({
    asset_type: 'acciones',
    name: '',
  })

  useEffect(() => {
    loadData(true) // Skip onUpdate to prevent infinite loop
  }, [refreshTrigger])

  const loadData = async (skipUpdate = false) => {
    try {
      setIsLoading(true)
      setError(null)
      const portfolioData = await portfolioApi.list()
      setItems(portfolioData)
      if (!skipUpdate) {
        onUpdate?.()
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Error al cargar la cartera')
    } finally {
      setIsLoading(false)
    }
  }


  const handleAddNew = () => {
    setIsAdding(true)
    setFormData({ asset_type: 'acciones', name: '' })
    setError(null)
  }

  const handleSave = async () => {
    if (!formData.name.trim()) {
      setError('El nombre es requerido')
      return
    }

    try {
      setError(null)
      const dataToSave: PortfolioItemCreate = {
        asset_type: formData.asset_type,
        name: formData.name.trim(),
        symbol: '',
        quantity: '',
        price: '',
        total_value: '',
        currency: 'USD',
        notes: '',
      }
      
      await portfolioApi.create(dataToSave)
      setIsAdding(false)
      setFormData({ asset_type: 'acciones', name: '' })
      // Reload data and trigger parent update
      await loadData(false) // Don't skip update - this is a manual action
      onUpdate?.()
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Error al guardar el item')
      // loadData() handles isLoading state in its finally block
    }
  }

  const handleClearAll = async () => {
    if (items.length === 0) return
    
    if (!confirm(`¿Estás seguro de eliminar todos los ${items.length} items de la cartera? Esta acción no se puede deshacer.`)) {
      return
    }

    try {
      setIsClearing(true)
      setError(null)
      await portfolioApi.clearAll()
      // Reload data and trigger parent update
      await loadData(false) // Don't skip update - this is a manual action
      onUpdate?.()
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Error al borrar todos los items')
    } finally {
      setIsClearing(false)
    }
  }

  const handleCancelAdd = () => {
    setIsAdding(false)
    setFormData({ asset_type: 'acciones', name: '' })
    setError(null)
  }

  const handleDeleteItem = async (id: number) => {
    if (!confirm('¿Estás seguro de eliminar este activo de la cartera?')) return
    
    try {
      setError(null)
      await portfolioApi.delete(id)
      await loadData(false) // Reload data after deletion
      onUpdate?.()
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Error al eliminar el activo')
    }
  }

  const isValid = formData.name.trim().length > 0

  if (isLoading) {
    return (
      <div className="portfolio-widget" role="region" aria-label="Widget de Cartera">
        <div className="widget-header">
          <h2>💼 Mi Cartera</h2>
        </div>
        <div className="loading" aria-live="polite" aria-busy="true">
          <p>Cargando...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="portfolio-widget" role="region" aria-label="Widget de Cartera">
      <div className="widget-header">
        <h2>💼 Mi Cartera</h2>
        <div className="widget-actions">
          <button 
            className="action-btn" 
            onClick={handleAddNew} 
            title="Agregar item"
            aria-label="Agregar nuevo item a la cartera"
            disabled={isLoading || isClearing}
          >
            ➕ Agregar
          </button>
          {items.length > 0 && (
            <button 
              className="action-btn" 
              onClick={handleClearAll} 
              title="Borrar todo"
              aria-label="Borrar todos los items de la cartera"
              disabled={isLoading || isClearing}
            >
              🗑️ Borrar todo
            </button>
          )}
          <button 
            className="refresh-btn" 
            onClick={loadData} 
            title="Actualizar cartera"
            aria-label="Actualizar datos de la cartera"
            disabled={isLoading || isClearing}
          >
            🔄
          </button>
        </div>
      </div>

      {error && (
        <div className="error-message" role="alert" aria-live="assertive">{error}</div>
      )}

      {isAdding && (
        <div className="portfolio-form-card">
          <h3>➕ Nuevo Item</h3>
          <div className="simple-form-grid">
            <div className="form-group">
              <label>Categoría *</label>
              <select
                value={formData.asset_type}
                onChange={(e) => setFormData({ ...formData, asset_type: e.target.value })}
              >
                {ASSET_TYPES.map(type => (
                  <option key={type} value={type}>{type.charAt(0).toUpperCase() + type.slice(1)}</option>
                ))}
              </select>
            </div>
            <div className="form-group">
              <label>Nombre *</label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                placeholder="Ej: Apple Inc. o AAPL"
                onKeyPress={(e) => {
                  if (e.key === 'Enter' && isValid) {
                    handleSave()
                  }
                }}
              />
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

      {items.length === 0 && !isAdding ? (
        <div className="empty-state">
          <p>No hay activos en tu cartera.</p>
          <p className="hint">Agrega activos para comenzar.</p>
        </div>
      ) : (
        <div className="section-card items-list-section">
          <h3>📋 Activos en Cartera</h3>
          {items.length > 0 ? (
            <div className="portfolio-items-list">
              {items.map((item) => (
                <div key={item.id} className="portfolio-item-row">
                  <div className="item-info">
                    <span className={`asset-type-badge ${item.asset_type}`}>
                      {item.asset_type}
                    </span>
                    <span className="item-name">{item.name}</span>
                    {item.symbol && <span className="item-symbol">({item.symbol})</span>}
                  </div>
                  <button
                    className="delete-item-btn"
                    onClick={() => handleDeleteItem(item.id)}
                    title="Eliminar"
                    aria-label={`Eliminar ${item.name}`}
                    disabled={isLoading || isClearing}
                  >
                    🗑️
                  </button>
                </div>
              ))}
            </div>
          ) : (
            <div className="empty-section">No hay activos</div>
          )}
        </div>
      )}
    </div>
  )
}

