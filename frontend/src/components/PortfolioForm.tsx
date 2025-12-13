import { useState } from 'react'
import { PortfolioItemCreate } from '../services/api'
import './PortfolioForm.css'

interface PortfolioFormProps {
  onSubmit: (item: PortfolioItemCreate) => Promise<void>
  onCancel: () => void
  isSubmitting: boolean
  initialData?: PortfolioItemCreate
}

export default function PortfolioForm({ onSubmit, onCancel, isSubmitting, initialData }: PortfolioFormProps) {
  const [formData, setFormData] = useState<PortfolioItemCreate>({
    asset_type: initialData?.asset_type || 'acciones',
    name: initialData?.name || '',
    symbol: initialData?.symbol || '',
    quantity: initialData?.quantity || '',
    price: initialData?.price || '',
    total_value: initialData?.total_value || '',
    currency: initialData?.currency || 'USD',
    notes: initialData?.notes || ''
  })
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)

    if (!formData.name.trim()) {
      setError('El nombre del activo es requerido')
      return
    }

    try {
      await onSubmit(formData)
    } catch (err: any) {
      setError(err.message || 'Error al guardar el activo')
    }
  }

  return (
    <form onSubmit={handleSubmit} className="portfolio-form">
      <div className="form-group">
        <label htmlFor="asset_type">Tipo de activo *</label>
        <select
          id="asset_type"
          value={formData.asset_type}
          onChange={(e) => setFormData({ ...formData, asset_type: e.target.value })}
          disabled={isSubmitting}
          required
        >
          <option value="acciones">Acciones</option>
          <option value="bonos">Bonos</option>
          <option value="etf">ETF</option>
          <option value="fondos">Fondos</option>
          <option value="divisas">Divisas</option>
          <option value="otros">Otros</option>
        </select>
      </div>

      <div className="form-group">
        <label htmlFor="name">Nombre *</label>
        <input
          id="name"
          type="text"
          value={formData.name}
          onChange={(e) => setFormData({ ...formData, name: e.target.value })}
          placeholder="Ej: Apple Inc."
          disabled={isSubmitting}
          required
          maxLength={200}
        />
      </div>

      <div className="form-group">
        <label htmlFor="symbol">Símbolo/Ticker</label>
        <input
          id="symbol"
          type="text"
          value={formData.symbol}
          onChange={(e) => setFormData({ ...formData, symbol: e.target.value.toUpperCase() })}
          placeholder="Ej: AAPL"
          disabled={isSubmitting}
          maxLength={50}
        />
      </div>

      <div className="form-row">
        <div className="form-group">
          <label htmlFor="quantity">Cantidad</label>
          <input
            id="quantity"
            type="text"
            value={formData.quantity}
            onChange={(e) => setFormData({ ...formData, quantity: e.target.value })}
            placeholder="Ej: 100"
            disabled={isSubmitting}
            maxLength={50}
          />
        </div>

        <div className="form-group">
          <label htmlFor="price">Precio unitario</label>
          <input
            id="price"
            type="text"
            value={formData.price}
            onChange={(e) => setFormData({ ...formData, price: e.target.value })}
            placeholder="Ej: 150.50"
            disabled={isSubmitting}
            maxLength={50}
          />
        </div>
      </div>

      <div className="form-row">
        <div className="form-group">
          <label htmlFor="total_value">Valor total</label>
          <input
            id="total_value"
            type="text"
            value={formData.total_value}
            onChange={(e) => setFormData({ ...formData, total_value: e.target.value })}
            placeholder="Ej: 15050.00"
            disabled={isSubmitting}
            maxLength={50}
          />
        </div>

        <div className="form-group">
          <label htmlFor="currency">Moneda</label>
          <select
            id="currency"
            value={formData.currency}
            onChange={(e) => setFormData({ ...formData, currency: e.target.value })}
            disabled={isSubmitting}
          >
            <option value="USD">USD</option>
            <option value="EUR">EUR</option>
            <option value="GBP">GBP</option>
            <option value="ARS">ARS</option>
          </select>
        </div>
      </div>

      <div className="form-group">
        <label htmlFor="notes">Notas</label>
        <textarea
          id="notes"
          value={formData.notes}
          onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
          placeholder="Notas adicionales sobre este activo"
          disabled={isSubmitting}
          rows={3}
        />
      </div>

      {error && <div className="error-message">{error}</div>}

      <div className="form-actions">
        <button type="button" onClick={onCancel} className="cancel-button" disabled={isSubmitting}>
          Cancelar
        </button>
        <button type="submit" className="submit-button" disabled={isSubmitting}>
          {isSubmitting ? '⏳ Guardando...' : '💾 Guardar'}
        </button>
      </div>
    </form>
  )
}

