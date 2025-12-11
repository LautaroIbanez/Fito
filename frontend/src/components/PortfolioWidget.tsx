import { useState, useEffect } from 'react'
import { portfolioApi, PortfolioItem, PortfolioItemCreate } from '../services/api'
import PriceChart from './PriceChart'
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
  const [editingId, setEditingId] = useState<number | null>(null)
  const [expandedChartId, setExpandedChartId] = useState<number | null>(null)
  const [priceData, setPriceData] = useState<Record<number, Array<{ date: string; price: number }>>>({})
  const [loadingCharts, setLoadingCharts] = useState<Record<number, boolean>>({})
  const [formData, setFormData] = useState({
    asset_type: 'acciones',
    name: '',
    symbol: '',
    quantity: '',
    price: '',
    total_value: '',
    currency: 'USD',
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
    setEditingId(null)
    setFormData({ asset_type: 'acciones', name: '', symbol: '', quantity: '', price: '', total_value: '', currency: 'USD' })
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
        symbol: formData.symbol.trim(),
        quantity: formData.quantity.trim(),
        price: formData.price.trim(),
        total_value: formData.total_value.trim(),
        currency: formData.currency,
        notes: '',
      }
      
      if (editingId) {
        await portfolioApi.update(editingId, dataToSave)
        setEditingId(null)
      } else {
        await portfolioApi.create(dataToSave)
        setIsAdding(false)
      }
      
      setFormData({ asset_type: 'acciones', name: '', symbol: '', quantity: '', price: '', total_value: '', currency: 'USD' })
      // Reload data and trigger parent update
      await loadData(false) // Don't skip update - this is a manual action
      onUpdate?.()
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Error al guardar el item')
      // loadData() handles isLoading state in its finally block
    }
  }

  const handleEdit = (item: PortfolioItem) => {
    setEditingId(item.id)
    setFormData({
      asset_type: item.asset_type || 'acciones',
      name: item.name || '',
      symbol: item.symbol || '',
      quantity: item.quantity || '',
      price: item.price || '',
      total_value: item.total_value || '',
      currency: item.currency || 'USD',
    })
    setIsAdding(false)
    setError(null)
  }

  const handleCancelEdit = () => {
    setEditingId(null)
    setFormData({ asset_type: 'acciones', name: '', symbol: '', quantity: '', price: '', total_value: '', currency: 'USD' })
    setError(null)
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
    setEditingId(null)
    setFormData({ asset_type: 'acciones', name: '', symbol: '', quantity: '', price: '', total_value: '', currency: 'USD' })
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

  const handleToggleChart = async (itemId: number) => {
    if (expandedChartId === itemId) {
      setExpandedChartId(null)
    } else {
      setExpandedChartId(itemId)
      
      // Cargar datos de precio si no están en caché
      if (!priceData[itemId]) {
        try {
          setLoadingCharts(prev => ({ ...prev, [itemId]: true }))
          const history = await portfolioApi.getPriceHistory(itemId, 60)
          setPriceData(prev => ({ ...prev, [itemId]: history.data }))
        } catch (err: any) {
          console.error('Error al cargar historial de precios:', err)
        } finally {
          setLoadingCharts(prev => ({ ...prev, [itemId]: false }))
        }
      }
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

      {(isAdding || editingId) && (
        <div className="portfolio-form-card">
          <h3>{editingId ? '✏️ Editar Item' : '➕ Nuevo Item'}</h3>
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
              />
            </div>
            <div className="form-group">
              <label>Símbolo</label>
              <input
                type="text"
                value={formData.symbol}
                onChange={(e) => setFormData({ ...formData, symbol: e.target.value })}
                placeholder="Ej: AAPL"
              />
            </div>
            <div className="form-group">
              <label>Cantidad</label>
              <input
                type="text"
                value={formData.quantity}
                onChange={(e) => {
                  const qty = e.target.value
                  const price = formData.price
                  let total = ''
                  if (qty && price) {
                    const qtyNum = parseFloat(qty.replace(/,/g, ''))
                    const priceNum = parseFloat(price.replace(/,/g, ''))
                    if (!isNaN(qtyNum) && !isNaN(priceNum)) {
                      total = (qtyNum * priceNum).toFixed(2)
                    }
                  }
                  setFormData({ ...formData, quantity: qty, total_value: total || formData.total_value })
                }}
                placeholder="Ej: 100"
              />
            </div>
            <div className="form-group">
              <label>Precio Unitario</label>
              <input
                type="text"
                value={formData.price}
                onChange={(e) => {
                  const price = e.target.value
                  const qty = formData.quantity
                  let total = ''
                  if (qty && price) {
                    const qtyNum = parseFloat(qty.replace(/,/g, ''))
                    const priceNum = parseFloat(price.replace(/,/g, ''))
                    if (!isNaN(qtyNum) && !isNaN(priceNum)) {
                      total = (qtyNum * priceNum).toFixed(2)
                    }
                  }
                  setFormData({ ...formData, price: price, total_value: total || formData.total_value })
                }}
                placeholder="Ej: 150.50"
              />
            </div>
            <div className="form-group">
              <label>Valor Total</label>
              <input
                type="text"
                value={formData.total_value}
                onChange={(e) => setFormData({ ...formData, total_value: e.target.value })}
                placeholder="Ej: 15050.00"
              />
              <small className="form-hint">Se calcula automáticamente si ingresas cantidad y precio</small>
            </div>
            <div className="form-group">
              <label>Moneda</label>
              <select
                value={formData.currency}
                onChange={(e) => setFormData({ ...formData, currency: e.target.value })}
              >
                <option value="USD">USD</option>
                <option value="ARS">ARS</option>
                <option value="EUR">EUR</option>
                <option value="BRL">BRL</option>
              </select>
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
            <button className="cancel-button" onClick={editingId ? handleCancelEdit : handleCancelAdd} disabled={isLoading}>
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
                <div key={item.id} className="portfolio-item-container">
                  <div className="portfolio-item-row">
                    <div className="item-info">
                      <span className={`asset-type-badge ${item.asset_type}`}>
                        {item.asset_type}
                      </span>
                      <span className="item-name">{item.name}</span>
                      {item.symbol && <span className="item-symbol">({item.symbol})</span>}
                    </div>
                    <div className="item-actions">
                      <button
                        className="edit-item-btn"
                        onClick={() => handleEdit(item)}
                        title="Editar"
                        aria-label={`Editar ${item.name}`}
                        disabled={isLoading || isClearing || editingId !== null}
                      >
                        ✏️
                      </button>
                      <button
                        className="chart-toggle-btn"
                        onClick={() => handleToggleChart(item.id)}
                        title="Ver gráfico de precios"
                        aria-label={`Ver gráfico para ${item.name}`}
                        disabled={isLoading || isClearing || loadingCharts[item.id] || editingId !== null}
                      >
                        {expandedChartId === item.id ? '📉 Ocultar' : '📈 Ver Gráfico'}
                      </button>
                      <button
                        className="delete-item-btn"
                        onClick={() => handleDeleteItem(item.id)}
                        title="Eliminar"
                        aria-label={`Eliminar ${item.name}`}
                        disabled={isLoading || isClearing || editingId !== null}
                      >
                        🗑️
                      </button>
                    </div>
                  </div>
                  
                  {expandedChartId === item.id && (
                    <div className="item-chart-container">
                      {loadingCharts[item.id] ? (
                        <div className="chart-loading">Cargando datos de precios...</div>
                      ) : priceData[item.id] && priceData[item.id].length > 0 ? (
                        <PriceChart
                          data={priceData[item.id]}
                          title={item.name}
                          symbol={item.symbol}
                          height={250}
                        />
                      ) : (
                        <div className="chart-error">No hay datos de precio disponibles para este activo</div>
                      )}
                    </div>
                  )}
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

