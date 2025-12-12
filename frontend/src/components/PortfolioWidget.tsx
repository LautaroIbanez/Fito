import { useState, useEffect } from 'react'
import { portfolioApi, PortfolioItem, PortfolioItemCreate, PortfolioRanking, PortfolioRankings } from '../services/api'
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
  const [rankings, setRankings] = useState<Record<number, PortfolioRanking>>({})
  const [loadingRankings, setLoadingRankings] = useState(false)
  const [selectedRankingDetails, setSelectedRankingDetails] = useState<PortfolioRanking | null>(null)
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
    loadRankings()
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

  const loadRankings = async () => {
    try {
      setLoadingRankings(true)
      const rankingsData = await portfolioApi.getRankings()
      const rankingsMap: Record<number, PortfolioRanking> = {}
      // Asegurar que cada ranking esté correctamente mapeado por item_id
      rankingsData.rankings.forEach(ranking => {
        if (ranking.item_id) {
          rankingsMap[ranking.item_id] = ranking
        } else {
          console.warn('Ranking sin item_id:', ranking)
        }
      })
      setRankings(rankingsMap)
      console.log(`Rankings cargados: ${Object.keys(rankingsMap).length} items`, rankingsMap)
    } catch (err: any) {
      console.error('Error al cargar rankings:', err)
      // No mostrar error al usuario, solo log
    } finally {
      setLoadingRankings(false)
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
      // Recargar rankings después de agregar/editar un item
      await loadRankings()
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
      // Recargar rankings después de eliminar un item
      await loadRankings()
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
              {items.map((item) => {
                const ranking = rankings[item.id]
                return (
                <div key={item.id} className="portfolio-item-container">
                  <div className="portfolio-item-row">
                    <div className="item-info">
                      {ranking && (
                        <button
                          className={`ranking-indicator ranking-${ranking.color}`}
                          onClick={() => {
                            // Asegurar que el ranking corresponde al item correcto
                            const correctRanking = rankings[item.id]
                            if (correctRanking && correctRanking.item_id === item.id) {
                              setSelectedRankingDetails(correctRanking)
                            } else {
                              console.warn(`Ranking mismatch: item.id=${item.id}, ranking.item_id=${ranking.item_id}`)
                              setSelectedRankingDetails(ranking)
                            }
                          }}
                          title={
                            ranking.thresholds && ranking.weights && ranking.factor_push
                              ? `Ranking: ${ranking.status_text} (Score: ${ranking.composite_score.toFixed(1)}/100)\n\nRangos:\n• Verde: ${ranking.thresholds.green_min.toFixed(0)}-${ranking.thresholds.green_max}\n• Ámbar: ${ranking.thresholds.amber_min.toFixed(0)}-${ranking.thresholds.amber_max.toFixed(0)}\n• Rojo: 0-${ranking.thresholds.red_max.toFixed(0)}\n\nBreakdown:\n• Sentimiento: ${ranking.sentiment_score.toFixed(1)}/100 (${(ranking.weights.sentiment * 100).toFixed(0)}% peso)\n• Técnico: ${ranking.technical_score.toFixed(1)}/100 (${(ranking.weights.technical * 100).toFixed(0)}% peso)\n\nContribución:\n• Sentimiento: ${ranking.factor_push.sentiment >= 0 ? '+' : ''}${ranking.factor_push.sentiment.toFixed(1)}\n• Técnico: ${ranking.factor_push.technical >= 0 ? '+' : ''}${ranking.factor_push.technical.toFixed(1)}\n\nClick para ver detalles`
                              : `Ranking: ${ranking.status_text} (Score: ${ranking.composite_score.toFixed(1)}/100)\nSentimiento: ${ranking.sentiment_score.toFixed(1)}/100\nTécnico: ${ranking.technical_score.toFixed(1)}/100\n\nClick para ver detalles`
                          }
                          aria-label={`Ver detalles de ranking para ${item.name}: ${ranking.status_text}`}
                        >
                          <span className="ranking-dot" aria-hidden="true"></span>
                          <span className="ranking-status-text">{ranking.status_text}</span>
                        </button>
                      )}
                      {loadingRankings && !ranking && (
                        <span className="ranking-loading" aria-label="Cargando ranking...">⏳</span>
                      )}
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
                        {expandedChartId === item.id ? (
                          <>
                            <span className="chart-icon" aria-hidden="true">
                              <svg width="14" height="14" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
                                <path d="M2 4L6 8L9 5L14 10" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
                              </svg>
                            </span>
                            Ocultar
                          </>
                        ) : (
                          <>
                            <span className="chart-icon" aria-hidden="true">
                              <svg width="14" height="14" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
                                <path d="M2 12L6 8L9 11L14 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
                                <path d="M10 4H14V8" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
                              </svg>
                            </span>
                            Ver Gráfico
                          </>
                        )}
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
              )})}
            </div>
          ) : (
            <div className="empty-section">No hay activos</div>
          )}
        </div>
      )}

      {/* Modal de detalles de ranking */}
      {selectedRankingDetails && (
        <div className="ranking-modal-overlay" onClick={() => setSelectedRankingDetails(null)}>
          <div className="ranking-modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="ranking-modal-header">
              <h3>
                <span className="section-icon" aria-hidden="true">
                  <svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M8 2L10 6H14L11 9L12 13L8 11L4 13L5 9L2 6H6L8 2Z" fill="currentColor"/>
                  </svg>
                </span>
                Detalles de Ranking: {selectedRankingDetails.name}
              </h3>
              <button
                className="ranking-modal-close"
                onClick={() => setSelectedRankingDetails(null)}
                aria-label="Cerrar modal"
              >
                ✕
              </button>
            </div>
            <div className="ranking-modal-body">
              <div className="ranking-summary">
                <div className={`ranking-badge-large ranking-${selectedRankingDetails.color}`}>
                  <span className="ranking-dot-large"></span>
                  <div>
                    <div className="ranking-status-large">{selectedRankingDetails.status_text}</div>
                    <div className="ranking-score">Score: {selectedRankingDetails.composite_score.toFixed(1)}/100</div>
                  </div>
                </div>
                
                {/* Rangos del semáforo */}
                {selectedRankingDetails.thresholds && (
                  <div className="ranking-thresholds">
                    <div className="threshold-item threshold-red">
                      <span className="threshold-dot"></span>
                      <span className="threshold-range">Rojo: 0-{selectedRankingDetails.thresholds.red_max.toFixed(0)}</span>
                    </div>
                    <div className="threshold-item threshold-amber">
                      <span className="threshold-dot"></span>
                      <span className="threshold-range">Ámbar: {selectedRankingDetails.thresholds.amber_min.toFixed(0)}-{selectedRankingDetails.thresholds.amber_max.toFixed(0)}</span>
                    </div>
                    <div className="threshold-item threshold-green">
                      <span className="threshold-dot"></span>
                      <span className="threshold-range">Verde: {selectedRankingDetails.thresholds.green_min.toFixed(0)}-{selectedRankingDetails.thresholds.green_max}</span>
                    </div>
                  </div>
                )}
                
                {/* Breakdown del score y contribuciones */}
                {selectedRankingDetails.weights && selectedRankingDetails.contributions && (
                  <div className="ranking-breakdown">
                    <h5>Breakdown del Score</h5>
                    <div className="breakdown-bars">
                      <div className="breakdown-item">
                        <div className="breakdown-label">
                          <span>Sentimiento</span>
                          <span className="breakdown-weight">({(selectedRankingDetails.weights.sentiment * 100).toFixed(0)}% peso)</span>
                        </div>
                        <div className="breakdown-bar-container">
                          <div 
                            className="breakdown-bar breakdown-sentiment" 
                            style={{ width: `${selectedRankingDetails.sentiment_score}%` }}
                          >
                            {selectedRankingDetails.sentiment_score.toFixed(1)}
                          </div>
                        </div>
                        <div className="breakdown-contribution">
                          Contribución: {selectedRankingDetails.contributions.sentiment.toFixed(1)} puntos
                        </div>
                      </div>
                      <div className="breakdown-item">
                        <div className="breakdown-label">
                          <span>Técnico</span>
                          <span className="breakdown-weight">({(selectedRankingDetails.weights.technical * 100).toFixed(0)}% peso)</span>
                        </div>
                        <div className="breakdown-bar-container">
                          <div 
                            className="breakdown-bar breakdown-technical" 
                            style={{ width: `${selectedRankingDetails.technical_score}%` }}
                          >
                            {selectedRankingDetails.technical_score.toFixed(1)}
                          </div>
                        </div>
                        <div className="breakdown-contribution">
                          Contribución: {selectedRankingDetails.contributions.technical.toFixed(1)} puntos
                        </div>
                      </div>
                    </div>
                  </div>
                )}
                
                {/* Factor push - qué empujó el color */}
                {selectedRankingDetails.factor_push && (
                  <div className="ranking-factor-push">
                    <h5>Contribución al Color Actual</h5>
                    <div className="factor-push-items">
                      <div className={`factor-push-item ${selectedRankingDetails.factor_push.sentiment >= 0 ? 'positive' : 'negative'}`}>
                        <span className="factor-name">Sentimiento:</span>
                        <span className={`factor-value ${selectedRankingDetails.factor_push.sentiment >= 0 ? 'positive' : 'negative'}`}>
                          {selectedRankingDetails.factor_push.sentiment >= 0 ? '+' : ''}{selectedRankingDetails.factor_push.sentiment.toFixed(1)}
                        </span>
                        <span className="factor-explanation">
                          {selectedRankingDetails.factor_push.sentiment >= 0 
                            ? 'Empuja hacia verde' 
                            : 'Empuja hacia rojo'}
                        </span>
                      </div>
                      <div className={`factor-push-item ${selectedRankingDetails.factor_push.technical >= 0 ? 'positive' : 'negative'}`}>
                        <span className="factor-name">Técnico:</span>
                        <span className={`factor-value ${selectedRankingDetails.factor_push.technical >= 0 ? 'positive' : 'negative'}`}>
                          {selectedRankingDetails.factor_push.technical >= 0 ? '+' : ''}{selectedRankingDetails.factor_push.technical.toFixed(1)}
                        </span>
                        <span className="factor-explanation">
                          {selectedRankingDetails.factor_push.technical >= 0 
                            ? 'Empuja hacia verde' 
                            : 'Empuja hacia rojo'}
                        </span>
                      </div>
                    </div>
                  </div>
                )}
                
                {/* Recomendación de acción */}
                {selectedRankingDetails.action_recommendation && (
                  <div className={`ranking-action-recommendation ranking-action-${selectedRankingDetails.color}`}>
                    <span className="action-icon" aria-hidden="true">
                      <svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
                        <circle cx="8" cy="8" r="6" stroke="currentColor" strokeWidth="1.5" fill="none"/>
                        <path d="M8 5V8M8 11H8.01" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
                      </svg>
                    </span>
                    <span className="action-text">{selectedRankingDetails.action_recommendation}</span>
                  </div>
                )}
                
                {/* Explicación rápida del score */}
                <div className="ranking-quick-explanation">
                  {selectedRankingDetails.composite_score >= (selectedRankingDetails.thresholds?.green_min || 65) ? (
                    <p>Score favorable por sentimiento positivo y señales técnicas alentadoras.</p>
                  ) : selectedRankingDetails.composite_score >= (selectedRankingDetails.thresholds?.amber_min || 40) ? (
                    <p>
                      Score neutro: {
                        (selectedRankingDetails.details.sentiment.data_quality === 'insufficient' && 
                         selectedRankingDetails.details.technical.data_quality === 'insufficient') 
                          ? 'Datos insuficientes de noticias y señales técnicas.'
                        : selectedRankingDetails.details.sentiment.data_quality === 'insufficient'
                          ? 'Sin noticias recientes suficientes.'
                        : selectedRankingDetails.details.technical.data_quality === 'insufficient'
                          ? 'Sin señales técnicas suficientes.'
                        : 'Señales mixtas o neutrales.'
                      }
                    </p>
                  ) : (
                    <p>Score de precaución por sentimiento negativo o señales técnicas débiles.</p>
                  )}
                </div>
                
                {/* Acciones rápidas */}
                <div className="ranking-quick-actions">
                  <button 
                    className="quick-action-btn quick-action-chart"
                    onClick={() => {
                      // TODO: Implementar navegación a gráficos
                      const symbol = selectedRankingDetails.symbol || selectedRankingDetails.name;
                      window.open(`https://www.tradingview.com/chart/?symbol=${encodeURIComponent(symbol)}`, '_blank');
                    }}
                    aria-label={`Ver gráfico e indicadores para ${selectedRankingDetails.name}`}
                  >
                    <span className="action-btn-icon" aria-hidden="true">
                      <svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
                        <path d="M2 12L6 8L9 11L14 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
                        <path d="M10 4H14V8" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
                      </svg>
                    </span>
                    <span className="action-btn-text">Ver Chart/Indicadores</span>
                  </button>
                  <button 
                    className="quick-action-btn quick-action-news"
                    onClick={() => {
                      // Scroll a la sección de noticias dentro del modal
                      const modal = document.querySelector('.ranking-modal-body');
                      const newsSection = modal?.querySelector('.ranking-headlines') || 
                                         modal?.querySelector('.ranking-detail-section:has(.ranking-headlines)');
                      if (newsSection) {
                        newsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
                        // Resaltar brevemente la sección
                        newsSection.classList.add('highlight-news-section');
                        setTimeout(() => {
                          newsSection.classList.remove('highlight-news-section');
                        }, 2000);
                      } else {
                        // Si no hay noticias, mostrar mensaje en la sección de sentimiento
                        const sentimentSection = modal?.querySelector('.ranking-detail-section');
                        if (sentimentSection) {
                          sentimentSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
                        }
                      }
                    }}
                    aria-label={`Ver noticias clave para ${selectedRankingDetails.name}`}
                  >
                    <span className="action-btn-icon" aria-hidden="true">
                      <svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
                        <rect x="2" y="4" width="12" height="8" rx="1" stroke="currentColor" strokeWidth="1.5" fill="none"/>
                        <path d="M2 6H14" stroke="currentColor" strokeWidth="1.5"/>
                        <path d="M4 8H12" stroke="currentColor" strokeWidth="1.5"/>
                      </svg>
                    </span>
                    <span className="action-btn-text">Noticias Clave</span>
                  </button>
                </div>
                
                {selectedRankingDetails.updated_at && (
                  <div className="ranking-update-time">
                    <small>Actualizado: {new Date(selectedRankingDetails.updated_at).toLocaleString('es-ES', { 
                      year: 'numeric', 
                      month: 'short', 
                      day: 'numeric', 
                      hour: '2-digit', 
                      minute: '2-digit' 
                    })}</small>
                  </div>
                )}
              </div>

              <div className="ranking-details-grid">
                <div className="ranking-detail-section">
                  <div className="ranking-section-header">
                    <h4>
                      <span className="section-icon" aria-hidden="true">
                        <svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
                          <rect x="2" y="4" width="12" height="8" rx="1" stroke="currentColor" strokeWidth="1.5" fill="none"/>
                          <path d="M2 6H14" stroke="currentColor" strokeWidth="1.5"/>
                          <path d="M4 8H12" stroke="currentColor" strokeWidth="1.5"/>
                        </svg>
                      </span>
                      Sentimiento ({selectedRankingDetails.details.sentiment.score.toFixed(1)}/100)
                    </h4>
                    {selectedRankingDetails.details.sentiment.last_news_date && (
                      <small className="ranking-data-source">
                        Última noticia: {new Date(selectedRankingDetails.details.sentiment.last_news_date).toLocaleDateString('es-ES', { 
                          month: 'short', 
                          day: 'numeric' 
                        })}
                      </small>
                    )}
                  </div>
                  
                  {selectedRankingDetails.details.sentiment.indicators_used && 
                   Array.isArray(selectedRankingDetails.details.sentiment.indicators_used) &&
                   selectedRankingDetails.details.sentiment.indicators_used.length > 0 && (
                    <div className="ranking-indicators">
                      <strong>Indicadores usados:</strong> {selectedRankingDetails.details.sentiment.indicators_used.join(', ')}
                    </div>
                  )}
                  
                  {(!selectedRankingDetails.details.sentiment.indicators_used || 
                    !Array.isArray(selectedRankingDetails.details.sentiment.indicators_used) ||
                    selectedRankingDetails.details.sentiment.indicators_used.length === 0) && (
                    <div className="ranking-indicators" style={{ background: '#fff3e0', borderLeftColor: '#ff9800' }}>
                      <strong>Indicadores:</strong> Análisis de sentimiento de noticias (últimos 7 días)
                    </div>
                  )}
                  
                  <p className="ranking-explanation">{selectedRankingDetails.details.sentiment.explanation || 'Sin datos disponibles'}</p>
                  
                  {selectedRankingDetails.details.sentiment.reliability_note && (
                    <div className="ranking-reliability-note">
                      <span className="reliability-icon" aria-hidden="true">
                        <svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
                          <circle cx="8" cy="8" r="6" stroke="currentColor" strokeWidth="1.5" fill="none"/>
                          <path d="M8 5V8M8 11H8.01" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
                        </svg>
                      </span>
                      <span>{selectedRankingDetails.details.sentiment.reliability_note}</span>
                    </div>
                  )}
                  
                  {/* Subtotales: Compañía y Sector */}
                  <div className="sentiment-subtotals">
                    <div className="sentiment-subtotal-item">
                      <div className="subtotal-header">
                        <h5>
                          <span className="subtotal-icon" aria-hidden="true">
                            <svg width="14" height="14" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
                              <rect x="3" y="5" width="10" height="9" rx="1" stroke="currentColor" strokeWidth="1.5" fill="none"/>
                              <path d="M5 5V3C5 2.44772 5.44772 2 6 2H10C10.5523 2 11 2.44772 11 3V5" stroke="currentColor" strokeWidth="1.5"/>
                              <path d="M8 8V11" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
                            </svg>
                          </span>
                          Compañía
                        </h5>
                        {selectedRankingDetails.details.sentiment.company_score !== undefined && (
                          <span className={`subtotal-score ${selectedRankingDetails.details.sentiment.company_score >= 60 ? 'positive' : selectedRankingDetails.details.sentiment.company_score >= 40 ? 'neutral' : 'negative'}`}>
                            {selectedRankingDetails.details.sentiment.company_score.toFixed(1)}/100
                          </span>
                        )}
                      </div>
                      <div className="subtotal-details">
                        <div className="subtotal-metric">
                          <strong>Artículos:</strong> {
                            selectedRankingDetails.details.sentiment.company_news_count > 0 
                              ? selectedRankingDetails.details.sentiment.company_news_count 
                              : <span className="no-data">Sin noticias relevantes</span>
                          }
                        </div>
                        {selectedRankingDetails.details.sentiment.company_last_date && (
                          <div className="subtotal-metric">
                            <strong>Última noticia:</strong> {new Date(selectedRankingDetails.details.sentiment.company_last_date).toLocaleDateString('es-ES', { 
                              year: 'numeric',
                              month: 'short', 
                              day: 'numeric' 
                            })}
                          </div>
                        )}
                        {selectedRankingDetails.details.sentiment.lookback_days && (
                          <div className="subtotal-metric">
                            <strong>Ventana temporal:</strong> Últimos {selectedRankingDetails.details.sentiment.lookback_days} días
                          </div>
                        )}
                      </div>
                    </div>
                    
                    <div className="sentiment-subtotal-item">
                      <div className="subtotal-header">
                        <h5>
                          <span className="subtotal-icon" aria-hidden="true">
                            <svg width="14" height="14" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
                              <rect x="2" y="3" width="12" height="10" rx="1" stroke="currentColor" strokeWidth="1.5" fill="none"/>
                              <path d="M5 7H11M5 10H9" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
                            </svg>
                          </span>
                          Sector
                        </h5>
                        {selectedRankingDetails.details.sentiment.sector_score !== undefined && (
                          <span className={`subtotal-score ${selectedRankingDetails.details.sentiment.sector_score >= 60 ? 'positive' : selectedRankingDetails.details.sentiment.sector_score >= 40 ? 'neutral' : 'negative'}`}>
                            {selectedRankingDetails.details.sentiment.sector_score.toFixed(1)}/100
                          </span>
                        )}
                      </div>
                      <div className="subtotal-details">
                        <div className="subtotal-metric">
                          <strong>Artículos:</strong> {
                            selectedRankingDetails.details.sentiment.sector_news_count > 0 
                              ? selectedRankingDetails.details.sentiment.sector_news_count 
                              : <span className="no-data">Sin noticias relevantes</span>
                          }
                        </div>
                        {selectedRankingDetails.details.sentiment.sector_synthesis && (
                          <div className="subtotal-metric">
                            <strong>Síntesis:</strong> <span className="sector-synthesis">{selectedRankingDetails.details.sentiment.sector_synthesis}</span>
                          </div>
                        )}
                        {selectedRankingDetails.details.sentiment.sector_last_date && (
                          <div className="subtotal-metric">
                            <strong>Última noticia:</strong> {new Date(selectedRankingDetails.details.sentiment.sector_last_date).toLocaleDateString('es-ES', { 
                              year: 'numeric',
                              month: 'short', 
                              day: 'numeric' 
                            })}
                          </div>
                        )}
                        {selectedRankingDetails.details.sentiment.lookback_days && (
                          <div className="subtotal-metric">
                            <strong>Ventana temporal:</strong> Últimos {selectedRankingDetails.details.sentiment.lookback_days} días
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                  
                  <div className="ranking-metrics">
                    {selectedRankingDetails.details.sentiment.data_quality && (
                      <div>
                        <strong>Calidad de datos:</strong> {
                          selectedRankingDetails.details.sentiment.data_quality === 'high' ? 'Alta ✓' :
                          selectedRankingDetails.details.sentiment.data_quality === 'medium' ? 'Media ⚠' :
                          selectedRankingDetails.details.sentiment.data_quality === 'insufficient' ? 'Insuficiente ✗' : 'Desconocida'
                        }
                      </div>
                    )}
                  </div>
                  
                  {selectedRankingDetails.details.sentiment.headlines && 
                   Array.isArray(selectedRankingDetails.details.sentiment.headlines) &&
                   selectedRankingDetails.details.sentiment.headlines.length > 0 && (
                    <div className="ranking-headlines">
                      <strong>Headlines relevantes:</strong>
                      <ul>
                        {selectedRankingDetails.details.sentiment.headlines.map((headline, idx) => (
                          <li key={idx}>{headline}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                  
                  {(!selectedRankingDetails.details.sentiment.headlines || 
                    !Array.isArray(selectedRankingDetails.details.sentiment.headlines) ||
                    selectedRankingDetails.details.sentiment.headlines.length === 0) &&
                   selectedRankingDetails.details.sentiment.company_news_count === 0 &&
                   selectedRankingDetails.details.sentiment.sector_news_count === 0 && (
                    <div className="ranking-reliability-note">
                      <span className="reliability-icon" aria-hidden="true">
                        <svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
                          <circle cx="8" cy="8" r="6" stroke="currentColor" strokeWidth="1.5" fill="none"/>
                          <path d="M8 5V8M8 11H8.01" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
                        </svg>
                      </span>
                      <span>No hay noticias recientes disponibles para este activo.</span>
                    </div>
                  )}
                </div>

                <div className="ranking-detail-section">
                  <div className="ranking-section-header">
                    <h4>📈 Análisis Técnico ({selectedRankingDetails.details.technical.score.toFixed(1)}/100)</h4>
                    {selectedRankingDetails.details.technical.last_update && (
                      <small className="ranking-data-source">
                        Actualizado: {new Date(selectedRankingDetails.details.technical.last_update).toLocaleString('es-ES', { 
                          month: 'short', 
                          day: 'numeric',
                          hour: '2-digit',
                          minute: '2-digit'
                        })}
                      </small>
                    )}
                  </div>
                  
                  {selectedRankingDetails.details.technical.indicators_used && 
                   Array.isArray(selectedRankingDetails.details.technical.indicators_used) &&
                   selectedRankingDetails.details.technical.indicators_used.length > 0 && (
                    <div className="ranking-indicators">
                      <strong>Indicadores usados:</strong> {selectedRankingDetails.details.technical.indicators_used.join(', ')}
                    </div>
                  )}
                  
                  {(!selectedRankingDetails.details.technical.indicators_used || 
                    !Array.isArray(selectedRankingDetails.details.technical.indicators_used) ||
                    selectedRankingDetails.details.technical.indicators_used.length === 0) && (
                    <div className="ranking-indicators" style={{ background: '#fff3e0', borderLeftColor: '#ff9800' }}>
                      <strong>Indicadores:</strong> RSI 14d, MA50 vs Precio, Volumen vs Promedio (20d)
                    </div>
                  )}
                  
                  <p className="ranking-explanation">{selectedRankingDetails.details.technical.explanation || 'Sin señales técnicas disponibles'}</p>
                  
                  {selectedRankingDetails.details.technical.reliability_note && (
                    <div className="ranking-reliability-note">
                      <span className="reliability-icon" aria-hidden="true">
                        <svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
                          <circle cx="8" cy="8" r="6" stroke="currentColor" strokeWidth="1.5" fill="none"/>
                          <path d="M8 5V8M8 11H8.01" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
                        </svg>
                      </span>
                      <span>{selectedRankingDetails.details.technical.reliability_note}</span>
                    </div>
                  )}
                  
                  {selectedRankingDetails.details.technical.signals && 
                   Object.keys(selectedRankingDetails.details.technical.signals).length > 0 && (
                    <div className="ranking-signals">
                      {Object.entries(selectedRankingDetails.details.technical.signals).map(([key, signal]: [string, any]) => (
                        <div key={key} className="ranking-signal-item">
                          <div className="signal-header">
                            <strong>{key.toUpperCase()}</strong>
                            {signal?.indicator && <span className="signal-indicator">{signal.indicator}</span>}
                            {signal?.period && <span className="signal-period">({signal.period})</span>}
                          </div>
                          <div className="signal-description">{signal?.description || 'Sin descripción'}</div>
                        </div>
                      ))}
                    </div>
                  )}
                  
                  {(!selectedRankingDetails.details.technical.signals || 
                    Object.keys(selectedRankingDetails.details.technical.signals).length === 0) && (
                    <div className="ranking-reliability-note">
                      <span className="reliability-icon" aria-hidden="true">
                        <svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
                          <circle cx="8" cy="8" r="6" stroke="currentColor" strokeWidth="1.5" fill="none"/>
                          <path d="M8 5V8M8 11H8.01" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
                        </svg>
                      </span>
                      <span>No hay señales técnicas disponibles. {selectedRankingDetails.details.technical.reliability_note || 'Datos insuficientes para análisis técnico.'}</span>
                    </div>
                  )}
                  
                  {selectedRankingDetails.details.technical.data_quality && (
                    <div className="ranking-metrics">
                      <div>Calidad de datos: {
                        selectedRankingDetails.details.technical.data_quality === 'high' ? 'Alta' :
                        selectedRankingDetails.details.technical.data_quality === 'medium' ? 'Media' :
                        selectedRankingDetails.details.technical.data_quality === 'insufficient' ? 'Insuficiente' : 'Desconocida'
                      }</div>
                    </div>
                  )}
                </div>
              </div>

              {selectedRankingDetails.weights && (
                <div className="ranking-weights-info">
                  <small>
                    <strong>Pesos configurados:</strong> Sentimiento {(selectedRankingDetails.weights.sentiment * 100).toFixed(0)}% | Técnico {(selectedRankingDetails.weights.technical * 100).toFixed(0)}%
                  </small>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

