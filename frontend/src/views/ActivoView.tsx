import { useState, useEffect } from 'react'
import { portfolioApi, PortfolioItem, PortfolioItemCreate, PriceDataResponse, PriceDataPoint } from '../services/api'
import Modal from '../components/Modal'
import PortfolioForm from '../components/PortfolioForm'
import PriceChart from '../components/PriceChart'
import './ActivoView.css'

export default function ActivoView() {
  const [portfolioItems, setPortfolioItems] = useState<PortfolioItem[]>([])
  const [selectedItem, setSelectedItem] = useState<PortfolioItem | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [editingItem, setEditingItem] = useState<PortfolioItem | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [priceData, setPriceData] = useState<PriceDataResponse | null>(null)
  const [isLoadingPrice, setIsLoadingPrice] = useState(false)
  const [priceError, setPriceError] = useState<string | null>(null)
  const [pricePeriod, setPricePeriod] = useState<string>('1mo')

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

  const handleCreateSubmit = async (formData: PortfolioItemCreate) => {
    try {
      setIsSubmitting(true)
      const newItem = await portfolioApi.create(formData)
      setEditingItem(null)
      await loadPortfolio()
      // Seleccionar el nuevo item
      setSelectedItem(newItem)
    } catch (err: any) {
      console.error('Error creando activo:', err)
      throw err
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleLoadPriceData = async () => {
    if (!selectedItem || !selectedItem.symbol) {
      setPriceError('El activo seleccionado no tiene un símbolo configurado')
      return
    }

    try {
      setIsLoadingPrice(true)
      setPriceError(null)
      const data = await portfolioApi.getPriceData(selectedItem.id, pricePeriod, '1d')
      setPriceData(data)
    } catch (err: any) {
      console.error('Error cargando datos de precio:', err)
      setPriceError(err.response?.data?.detail || err.message || 'Error al obtener datos de precio y volumen')
      setPriceData(null)
    } finally {
      setIsLoadingPrice(false)
    }
  }

  // Limpiar datos de precio cuando cambia el item seleccionado
  useEffect(() => {
    setPriceData(null)
    setPriceError(null)
  }, [selectedItem?.id])

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
        <h1>💼 Cartera</h1>
        <div className="header-actions">
          <button onClick={() => setEditingItem({} as PortfolioItem)} className="add-button">
            ➕ Agregar Activo
          </button>
          <button onClick={loadPortfolio} className="refresh-button">
            🔄 Actualizar
          </button>
        </div>
      </header>

      {portfolioItems.length === 0 && !editingItem ? (
        <div className="empty-state">
          <p>No hay activos en la cartera</p>
          <button onClick={() => setEditingItem({} as PortfolioItem)} className="add-button">
            ➕ Agregar tu primer activo
          </button>
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
              <div className="details-header">
                <h2>{selectedItem.name}</h2>
                <div className="price-data-controls">
                  <select 
                    value={pricePeriod} 
                    onChange={(e) => setPricePeriod(e.target.value)}
                    className="period-select"
                    disabled={isLoadingPrice}
                  >
                    <option value="1d">1 Día</option>
                    <option value="5d">5 Días</option>
                    <option value="1mo">1 Mes</option>
                    <option value="3mo">3 Meses</option>
                    <option value="6mo">6 Meses</option>
                    <option value="1y">1 Año</option>
                    <option value="2y">2 Años</option>
                  </select>
                  <button
                    onClick={handleLoadPriceData}
                    disabled={isLoadingPrice || !selectedItem.symbol}
                    className="update-price-button"
                    title="Actualizar precio y volumen desde Yahoo Finance"
                  >
                    {isLoadingPrice ? '⏳ Cargando...' : '📈 Actualizar Precio/Volumen'}
                  </button>
                </div>
              </div>
              
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
                {priceData?.current_price && (
                  <div className="detail-item">
                    <span className="detail-label">Precio Actual</span>
                    <span className="detail-value price-current">
                      {priceData.currency} {priceData.current_price.toFixed(2)}
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

              {/* Gráfico de precio */}
              {priceError && (
                <div className="price-error">
                  <p>⚠️ {priceError}</p>
                  <button onClick={handleLoadPriceData} className="retry-price-button">
                    Reintentar
                  </button>
                </div>
              )}

              {isLoadingPrice && (
                <div className="price-loading">
                  <div className="loading-spinner">⏳ Cargando datos de precio y volumen...</div>
                </div>
              )}

              {priceData && priceData.data.length > 0 && !isLoadingPrice && (
                <div className="price-chart-section">
                  <h3>Gráfico de Precio y Volumen</h3>
                  <PriceChart
                    data={priceData.data.map(point => ({
                      date: new Date(point.date),
                      price: point.close
                    }))}
                    title={selectedItem.name}
                    symbol={priceData.symbol}
                    height={300}
                    onTechnicalDataReady={(techData) => {
                      // Los datos técnicos están disponibles para el asistente IA
                      // Se pueden acceder también desde window.lastTechnicalData
                      console.log('Datos técnicos listos para IA:', techData.formatted)
                    }}
                  />
                  <div className="price-data-info">
                    <p>
                      <strong>Período:</strong> {pricePeriod} | 
                      <strong> Puntos de datos:</strong> {priceData.data_points} | 
                      <strong> Exchange:</strong> {priceData.exchange || 'N/A'}
                    </p>
                  </div>
                </div>
              )}

              {priceData && priceData.data.length === 0 && !isLoadingPrice && (
                <div className="price-empty">
                  <p>No se encontraron datos de precio para este activo.</p>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {editingItem && (
        <Modal
          isOpen={true}
          onClose={handleCancelEdit}
          title={editingItem.id ? `Editar activo: ${editingItem.name}` : 'Agregar nuevo activo'}
        >
          <PortfolioForm
            onSubmit={editingItem.id ? handleUpdateSubmit : handleCreateSubmit}
            onCancel={handleCancelEdit}
            isSubmitting={isSubmitting}
            initialData={editingItem.id ? {
              asset_type: editingItem.asset_type,
              name: editingItem.name,
              symbol: editingItem.symbol || '',
              quantity: editingItem.quantity || '',
              price: editingItem.price || '',
              total_value: editingItem.total_value || '',
              currency: editingItem.currency || 'USD',
              notes: editingItem.notes || ''
            } : undefined}
          />
        </Modal>
      )}
    </div>
  )
}

