import { useState, useEffect } from 'react'
import { portfolioApi, PortfolioItem, PortfolioItemCreate } from '../services/api'
import './PortfolioTable.css'

const ASSET_TYPES = ['acciones', 'bonos', 'etf', 'fondos', 'divisas', 'otros']

interface PortfolioTableProps {
  onUpdate?: () => void
}

export default function PortfolioTable({ onUpdate }: PortfolioTableProps) {
  const [items, setItems] = useState<PortfolioItem[]>([])
  const [editingId, setEditingId] = useState<number | null>(null)
  const [isAdding, setIsAdding] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [formData, setFormData] = useState<PortfolioItemCreate>({
    asset_type: 'acciones',
    name: '',
    symbol: '',
    quantity: '',
    price: '',
    total_value: '',
    currency: 'USD',
    notes: '',
  })

  const [simpleFormData, setSimpleFormData] = useState({
    asset_type: 'acciones',
    name: '',
  })

  useEffect(() => {
    loadPortfolio()
  }, [])

  const loadPortfolio = async () => {
    try {
      setIsLoading(true)
      const data = await portfolioApi.list()
      setItems(data)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Error al cargar la cartera')
    } finally {
      setIsLoading(false)
    }
  }

  const handleSave = async () => {
    try {
      setError(null)
      const dataToSave: PortfolioItemCreate = {
        asset_type: simpleFormData.asset_type,
        name: simpleFormData.name,
        symbol: '',
        quantity: '',
        price: '',
        total_value: '',
        currency: 'USD',
        notes: '',
      }
      
      if (editingId) {
        await portfolioApi.update(editingId, dataToSave)
      } else {
        await portfolioApi.create(dataToSave)
      }
      await loadPortfolio()
      resetForm()
      onUpdate?.()
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Error al guardar el item')
    }
  }

  const handleEdit = (item: PortfolioItem) => {
    setEditingId(item.id)
    setIsAdding(false)
    setSimpleFormData({
      asset_type: item.asset_type,
      name: item.name,
    })
    setFormData({
      asset_type: item.asset_type,
      name: item.name,
      symbol: item.symbol || '',
      quantity: item.quantity || '',
      price: item.price || '',
      total_value: item.total_value || '',
      currency: item.currency || 'USD',
      notes: item.notes || '',
    })
  }

  const handleDelete = async (id: number) => {
    if (!confirm('¿Estás seguro de eliminar este item de la cartera?')) return
    
    try {
      await portfolioApi.delete(id)
      await loadPortfolio()
      onUpdate?.()
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Error al eliminar el item')
    }
  }

  const handleAddNew = () => {
    setEditingId(null)
    setSimpleFormData({
      asset_type: 'acciones',
      name: '',
    })
    setFormData({
      asset_type: 'acciones',
      name: '',
      symbol: '',
      quantity: '',
      price: '',
      total_value: '',
      currency: 'USD',
      notes: '',
    })
    setIsAdding(true)
  }

  const resetForm = () => {
    setSimpleFormData({
      asset_type: 'acciones',
      name: '',
    })
    setFormData({
      asset_type: 'acciones',
      name: '',
      symbol: '',
      quantity: '',
      price: '',
      total_value: '',
      currency: 'USD',
      notes: '',
    })
    setIsAdding(false)
    setEditingId(null)
  }

  const isValid = simpleFormData.name.trim().length > 0

  if (isLoading) {
    return (
      <div className="portfolio-container">
        <h2>💼 Mi Cartera</h2>
        <div className="loading">Cargando cartera...</div>
      </div>
    )
  }

  return (
    <div className="portfolio-container">
      <div className="portfolio-header">
        <h2>💼 Mi Cartera ({items.length})</h2>
        <button className="add-button" onClick={handleAddNew}>
          ➕ Agregar Item
        </button>
      </div>

      {error && (
        <div className="error-message">{error}</div>
      )}

      {(isAdding || editingId) && (
        <div className="portfolio-form-card">
          <h3>{editingId ? '✏️ Editar Item' : '➕ Nuevo Item'}</h3>
          <div className="simple-form-grid">
            <div className="form-group">
              <label>Categoría *</label>
              <select
                value={simpleFormData.asset_type}
                onChange={(e) => setSimpleFormData({ ...simpleFormData, asset_type: e.target.value })}
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
                value={simpleFormData.name}
                onChange={(e) => setSimpleFormData({ ...simpleFormData, name: e.target.value })}
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
              disabled={!isValid}
            >
              💾 Guardar
            </button>
            <button className="cancel-button" onClick={resetForm}>
              ✕ Cancelar
            </button>
          </div>
        </div>
      )}

      {items.length === 0 && !isAdding && !editingId ? (
        <div className="empty-state">
          <p>No hay items en tu cartera aún.</p>
          <p className="hint">Haz clic en "Agregar Item" para comenzar.</p>
        </div>
      ) : (
        <div className="portfolio-table-wrapper">
          <table className="portfolio-table">
            <thead>
              <tr>
                <th>Categoría</th>
                <th>Nombre</th>
                <th>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.id}>
                  <td>
                    <span className={`asset-type-badge ${item.asset_type}`}>
                      {item.asset_type}
                    </span>
                  </td>
                  <td>{item.name}</td>
                  <td>
                    <div className="table-actions">
                      <button
                        className="edit-button"
                        onClick={() => handleEdit(item)}
                        title="Editar"
                      >
                        ✏️
                      </button>
                      <button
                        className="delete-button"
                        onClick={() => handleDelete(item.id)}
                        title="Eliminar"
                      >
                        🗑️
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

