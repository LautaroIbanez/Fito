import { useState, useEffect } from 'react'
import { alertsApi, AlertTrigger, AlertTriggerCreate } from '../services/api'
import './AlertTriggers.css'

export default function AlertTriggers() {
  const [triggers, setTriggers] = useState<AlertTrigger[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [showForm, setShowForm] = useState(false)
  
  const [formData, setFormData] = useState<AlertTriggerCreate>({
    name: '',
    symbol: '',
    asset_type: '',
    price_trigger_type: 'intraday_change',
    price_threshold: undefined,
    gap_threshold: undefined,
    require_recent_news: true,
    news_relevance_threshold: 2.0,
    news_max_age_hours: 24,
  })

  useEffect(() => {
    loadTriggers()
  }, [])

  const loadTriggers = async () => {
    try {
      setIsLoading(true)
      setError(null)
      const data = await alertsApi.listTriggers()
      setTriggers(data)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Error al cargar triggers')
    } finally {
      setIsLoading(false)
    }
  }

  const resetForm = () => {
    setFormData({
      name: '',
      symbol: '',
      asset_type: '',
      price_trigger_type: 'intraday_change',
      price_threshold: undefined,
      gap_threshold: undefined,
      require_recent_news: true,
      news_relevance_threshold: 2.0,
      news_max_age_hours: 24,
    })
    setEditingId(null)
    setShowForm(false)
  }

  const handleSave = async () => {
    try {
      setIsLoading(true)
      setError(null)
      
      const payload: any = { ...formData }
      if (!payload.symbol || payload.symbol.trim() === '') delete payload.symbol
      if (!payload.asset_type || payload.asset_type.trim() === '') delete payload.asset_type
      
      if (editingId) {
        await alertsApi.updateTrigger(editingId, payload)
      } else {
        await alertsApi.createTrigger(payload)
      }
      
      resetForm()
      loadTriggers()
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Error al guardar trigger')
    } finally {
      setIsLoading(false)
    }
  }

  const handleEdit = (trigger: AlertTrigger) => {
    setFormData({
      name: trigger.name,
      symbol: trigger.symbol || '',
      asset_type: trigger.asset_type || '',
      price_trigger_type: trigger.price_trigger_type,
      price_threshold: trigger.price_threshold || undefined,
      gap_threshold: trigger.gap_threshold || undefined,
      require_recent_news: trigger.require_recent_news,
      news_relevance_threshold: trigger.news_relevance_threshold,
      news_max_age_hours: trigger.news_max_age_hours,
    })
    setEditingId(trigger.id)
    setShowForm(true)
  }

  const handleDelete = async (id: number) => {
    if (!confirm('¿Estás seguro de eliminar este trigger?')) return
    
    try {
      setIsLoading(true)
      setError(null)
      await alertsApi.deleteTrigger(id)
      loadTriggers()
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Error al eliminar trigger')
    } finally {
      setIsLoading(false)
    }
  }

  const toggleActive = async (trigger: AlertTrigger) => {
    try {
      setIsLoading(true)
      await alertsApi.updateTrigger(trigger.id, { is_active: !trigger.is_active })
      loadTriggers()
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Error al actualizar trigger')
    } finally {
      setIsLoading(false)
    }
  }

  if (isLoading && triggers.length === 0) {
    return (
      <div className="alert-triggers-container">
        <h2>🔔 Triggers de Alertas</h2>
        <div className="loading">Cargando...</div>
      </div>
    )
  }

  return (
    <div className="alert-triggers-container">
      <div className="triggers-header">
        <h2>🔔 Triggers de Alertas</h2>
        <button className="add-button" onClick={() => setShowForm(true)}>
          ➕ Nuevo Trigger
        </button>
      </div>

      {error && (
        <div className="error-banner">
          <span>⚠️ {error}</span>
          <button onClick={() => setError(null)}>✕</button>
        </div>
      )}

      {showForm && (
        <div className="trigger-form-card">
          <h3>{editingId ? '✏️ Editar Trigger' : '➕ Nuevo Trigger'}</h3>
          
          <div className="form-grid">
            <div className="form-group">
              <label>Nombre *</label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                placeholder="Ej: Alerta AAPL >5%"
              />
            </div>

            <div className="form-group">
              <label>Símbolo (opcional)</label>
              <input
                type="text"
                value={formData.symbol}
                onChange={(e) => setFormData({ ...formData, symbol: e.target.value })}
                placeholder="AAPL, MSFT, etc."
              />
            </div>

            <div className="form-group">
              <label>Tipo de Activo (opcional)</label>
              <select
                value={formData.asset_type}
                onChange={(e) => setFormData({ ...formData, asset_type: e.target.value })}
              >
                <option value="">Todos</option>
                <option value="acciones">Acciones</option>
                <option value="bonos">Bonos</option>
                <option value="etf">ETF</option>
                <option value="fondos">Fondos</option>
                <option value="divisas">Divisas</option>
              </select>
            </div>

            <div className="form-group">
              <label>Tipo de Trigger *</label>
              <select
                value={formData.price_trigger_type}
                onChange={(e) => setFormData({ ...formData, price_trigger_type: e.target.value as any })}
              >
                <option value="intraday_change">Cambio Intradía (±X%)</option>
                <option value="gap">Gap de Apertura (±X%)</option>
                <option value="absolute">Precio Absoluto</option>
              </select>
            </div>

            {formData.price_trigger_type === 'intraday_change' && (
              <div className="form-group">
                <label>Umbral de Cambio (%) *</label>
                <input
                  type="number"
                  step="0.1"
                  value={formData.price_threshold || ''}
                  onChange={(e) => setFormData({ ...formData, price_threshold: parseFloat(e.target.value) || undefined })}
                  placeholder="5.0"
                />
              </div>
            )}

            {formData.price_trigger_type === 'gap' && (
              <div className="form-group">
                <label>Umbral de Gap (%) *</label>
                <input
                  type="number"
                  step="0.1"
                  value={formData.gap_threshold || ''}
                  onChange={(e) => setFormData({ ...formData, gap_threshold: parseFloat(e.target.value) || undefined })}
                  placeholder="3.0"
                />
              </div>
            )}

            {formData.price_trigger_type === 'absolute' && (
              <div className="form-group">
                <label>Precio Umbral *</label>
                <input
                  type="number"
                  step="0.01"
                  value={formData.price_threshold || ''}
                  onChange={(e) => setFormData({ ...formData, price_threshold: parseFloat(e.target.value) || undefined })}
                  placeholder="150.0"
                />
              </div>
            )}

            <div className="form-group checkbox-group">
              <label>
                <input
                  type="checkbox"
                  checked={formData.require_recent_news}
                  onChange={(e) => setFormData({ ...formData, require_recent_news: e.target.checked })}
                />
                Requiere noticias recientes
              </label>
            </div>

            {formData.require_recent_news && (
              <>
                <div className="form-group">
                  <label>Score Mínimo de Noticias</label>
                  <input
                    type="number"
                    step="0.1"
                    value={formData.news_relevance_threshold}
                    onChange={(e) => setFormData({ ...formData, news_relevance_threshold: parseFloat(e.target.value) })}
                  />
                </div>

                <div className="form-group">
                  <label>Antigüedad Máxima de Noticias (horas)</label>
                  <input
                    type="number"
                    value={formData.news_max_age_hours}
                    onChange={(e) => setFormData({ ...formData, news_max_age_hours: parseInt(e.target.value) })}
                  />
                </div>
              </>
            )}
          </div>

          <div className="form-actions">
            <button className="save-button" onClick={handleSave} disabled={!formData.name}>
              💾 Guardar
            </button>
            <button className="cancel-button" onClick={resetForm}>✕ Cancelar</button>
          </div>
        </div>
      )}

      <div className="triggers-list">
        {triggers.length === 0 ? (
          <div className="empty-state">
            <p>No hay triggers configurados.</p>
            <p className="hint">Crea un trigger para recibir alertas cuando se cumplan condiciones de precio y noticias.</p>
          </div>
        ) : (
          triggers.map((trigger) => (
            <div key={trigger.id} className={`trigger-item ${!trigger.is_active ? 'inactive' : ''}`}>
              <div className="trigger-header">
                <h3>{trigger.name}</h3>
                <div className="trigger-status">
                  <button
                    className={`status-toggle ${trigger.is_active ? 'active' : 'inactive'}`}
                    onClick={() => toggleActive(trigger)}
                    title={trigger.is_active ? 'Desactivar' : 'Activar'}
                  >
                    {trigger.is_active ? '✅' : '⏸️'}
                  </button>
                </div>
              </div>
              
              <div className="trigger-details">
                <div className="detail-row">
                  <span className="detail-label">Activo:</span>
                  <span className="detail-value">{trigger.symbol || trigger.asset_type || 'General'}</span>
                </div>
                
                <div className="detail-row">
                  <span className="detail-label">Trigger:</span>
                  <span className="detail-value">
                    {trigger.price_trigger_type === 'intraday_change' && `Cambio intradía: ±${trigger.price_threshold}%`}
                    {trigger.price_trigger_type === 'gap' && `Gap: ±${trigger.gap_threshold}%`}
                    {trigger.price_trigger_type === 'absolute' && `Precio: ${trigger.price_threshold}`}
                  </span>
                </div>
                
                <div className="detail-row">
                  <span className="detail-label">Noticias:</span>
                  <span className="detail-value">
                    {trigger.require_recent_news 
                      ? `Score ≥${trigger.news_relevance_threshold}, <${trigger.news_max_age_hours}h`
                      : 'No requeridas'}
                  </span>
                </div>
              </div>

              <div className="trigger-actions">
                <button className="edit-button" onClick={() => handleEdit(trigger)}>✏️ Editar</button>
                <button className="delete-button" onClick={() => handleDelete(trigger.id)}>🗑️ Eliminar</button>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}



