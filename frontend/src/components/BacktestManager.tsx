import { useState, useEffect } from 'react'
import { backtestApi, BacktestRule, BacktestRuleCreate, BacktestResult } from '../services/api'
import './BacktestManager.css'
import BacktestResults from './BacktestResults'

export default function BacktestManager() {
  const [rules, setRules] = useState<BacktestRule[]>([])
  const [selectedRuleId, setSelectedRuleId] = useState<number | null>(null)
  const [results, setResults] = useState<BacktestResult[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [showForm, setShowForm] = useState(false)
  const [initialCapital, setInitialCapital] = useState(10000)
  
  const [formData, setFormData] = useState<BacktestRuleCreate>({
    name: '',
    description: '',
    news_sentiment_required: 'positive',
    news_min_score: 2.0,
    news_max_age_hours: 24,
    price_change_condition: 'drop_before',
    price_change_threshold: 5.0,
    hold_period_days: 1,
    position_size_pct: 100.0,
    start_date: '',
    end_date: '',
  })

  useEffect(() => {
    loadRules()
    loadResults()
  }, [])

  useEffect(() => {
    if (selectedRuleId) {
      loadResults(selectedRuleId)
    } else {
      loadResults()
    }
  }, [selectedRuleId])

  const loadRules = async () => {
    try {
      setIsLoading(true)
      setError(null)
      const data = await backtestApi.listRules()
      setRules(data)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Error al cargar reglas')
    } finally {
      setIsLoading(false)
    }
  }

  const loadResults = async (ruleId?: number) => {
    try {
      const data = await backtestApi.listResults(ruleId)
      setResults(data.items)
    } catch (err: any) {
      console.error('Error al cargar resultados:', err)
    }
  }

  const resetForm = () => {
    setFormData({
      name: '',
      description: '',
      news_sentiment_required: 'positive',
      news_min_score: 2.0,
      news_max_age_hours: 24,
      price_change_condition: 'drop_before',
      price_change_threshold: 5.0,
      hold_period_days: 1,
      position_size_pct: 100.0,
      start_date: '',
      end_date: '',
    })
    setShowForm(false)
  }

  const handleSave = async () => {
    try {
      setIsLoading(true)
      setError(null)
      
      const payload: any = { ...formData }
      if (!payload.description || payload.description.trim() === '') delete payload.description
      if (!payload.start_date || payload.start_date.trim() === '') delete payload.start_date
      if (!payload.end_date || payload.end_date.trim() === '') delete payload.end_date
      if (payload.price_change_condition === 'none') {
        delete payload.price_change_threshold
      }
      
      await backtestApi.createRule(payload)
      resetForm()
      loadRules()
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Error al guardar regla')
    } finally {
      setIsLoading(false)
    }
  }

  const handleExecute = async (ruleId: number) => {
    try {
      setIsLoading(true)
      setError(null)
      const result = await backtestApi.executeBacktest(ruleId, initialCapital)
      await loadResults(ruleId)
      setSelectedRuleId(ruleId)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Error al ejecutar backtest')
    } finally {
      setIsLoading(false)
    }
  }

  const handleDelete = async (id: number) => {
    if (!confirm('¿Estás seguro de eliminar esta regla?')) return
    
    try {
      setIsLoading(true)
      setError(null)
      await backtestApi.deleteRule(id)
      loadRules()
      if (selectedRuleId === id) {
        setSelectedRuleId(null)
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Error al eliminar regla')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="backtest-manager-container">
      <div className="backtest-header">
        <h2>📊 Backtesting de Estrategias</h2>
        <button className="add-button" onClick={() => setShowForm(true)}>
          ➕ Nueva Regla
        </button>
      </div>

      {error && (
        <div className="error-banner">
          <span>⚠️ {error}</span>
          <button onClick={() => setError(null)}>✕</button>
        </div>
      )}

      {showForm && (
        <div className="backtest-form-card">
          <h3>➕ Nueva Regla de Backtesting</h3>
          
          <div className="form-grid">
            <div className="form-group full-width">
              <label>Nombre de la Regla *</label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                placeholder="Ej: Comprar en caída + noticia positiva"
              />
            </div>

            <div className="form-group full-width">
              <label>Descripción (opcional)</label>
              <textarea
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                placeholder="Descripción de la estrategia..."
                rows={3}
              />
            </div>

            <div className="form-group">
              <label>Sentimiento de Noticia Requerido *</label>
              <select
                value={formData.news_sentiment_required}
                onChange={(e) => setFormData({ ...formData, news_sentiment_required: e.target.value as any })}
              >
                <option value="positive">Positivo</option>
                <option value="negative">Negativo</option>
                <option value="any">Cualquiera</option>
              </select>
            </div>

            <div className="form-group">
              <label>Score Mínimo de Noticias</label>
              <input
                type="number"
                step="0.1"
                value={formData.news_min_score}
                onChange={(e) => setFormData({ ...formData, news_min_score: parseFloat(e.target.value) })}
              />
            </div>

            <div className="form-group">
              <label>Antigüedad Máx. Noticias (horas)</label>
              <input
                type="number"
                value={formData.news_max_age_hours}
                onChange={(e) => setFormData({ ...formData, news_max_age_hours: parseInt(e.target.value) })}
              />
            </div>

            <div className="form-group">
              <label>Condición de Precio</label>
              <select
                value={formData.price_change_condition}
                onChange={(e) => setFormData({ ...formData, price_change_condition: e.target.value as any })}
              >
                <option value="drop_before">Caída Previa</option>
                <option value="rise_before">Subida Previa</option>
                <option value="none">Sin Condición</option>
              </select>
            </div>

            {formData.price_change_condition !== 'none' && (
              <div className="form-group">
                <label>Umbral de Cambio (%)</label>
                <input
                  type="number"
                  step="0.1"
                  value={formData.price_change_threshold}
                  onChange={(e) => setFormData({ ...formData, price_change_threshold: parseFloat(e.target.value) })}
                  placeholder="5.0"
                />
              </div>
            )}

            <div className="form-group">
              <label>Período de Hold (días)</label>
              <input
                type="number"
                value={formData.hold_period_days}
                onChange={(e) => setFormData({ ...formData, hold_period_days: parseInt(e.target.value) })}
              />
            </div>

            <div className="form-group">
              <label>Tamaño de Posición (%)</label>
              <input
                type="number"
                step="1"
                min="1"
                max="100"
                value={formData.position_size_pct}
                onChange={(e) => setFormData({ ...formData, position_size_pct: parseFloat(e.target.value) })}
              />
            </div>

            <div className="form-group">
              <label>Fecha Inicio (opcional)</label>
              <input
                type="date"
                value={formData.start_date}
                onChange={(e) => setFormData({ ...formData, start_date: e.target.value })}
              />
            </div>

            <div className="form-group">
              <label>Fecha Fin (opcional)</label>
              <input
                type="date"
                value={formData.end_date}
                onChange={(e) => setFormData({ ...formData, end_date: e.target.value })}
              />
            </div>
          </div>

          <div className="form-actions">
            <button className="save-button" onClick={handleSave} disabled={!formData.name || isLoading}>
              💾 Guardar Regla
            </button>
            <button className="cancel-button" onClick={resetForm}>✕ Cancelar</button>
          </div>
        </div>
      )}

      <div className="rules-section">
        <h3>Reglas Configuradas</h3>
        {rules.length === 0 ? (
          <div className="empty-state">
            <p>No hay reglas configuradas.</p>
            <p className="hint">Crea una regla para ejecutar backtests.</p>
          </div>
        ) : (
          <div className="rules-list">
            {rules.map((rule) => (
              <div key={rule.id} className="rule-item">
                <div className="rule-header">
                  <h4>{rule.name}</h4>
                  <div className="rule-actions">
                    <button
                      className="execute-button"
                      onClick={() => handleExecute(rule.id)}
                      disabled={isLoading}
                    >
                      ▶️ Ejecutar
                    </button>
                    <button
                      className="delete-button"
                      onClick={() => handleDelete(rule.id)}
                      disabled={isLoading}
                    >
                      🗑️
                    </button>
                  </div>
                </div>
                
                <div className="rule-details">
                  <div className="detail-item">
                    <span className="label">Sentimiento:</span>
                    <span className="value">{rule.news_sentiment_required === 'positive' ? 'Positivo' : rule.news_sentiment_required === 'negative' ? 'Negativo' : 'Cualquiera'}</span>
                  </div>
                  <div className="detail-item">
                    <span className="label">Score min:</span>
                    <span className="value">{rule.news_min_score}</span>
                  </div>
                  {rule.price_change_condition && rule.price_change_condition !== 'none' && (
                    <div className="detail-item">
                      <span className="label">Precio:</span>
                      <span className="value">
                        {rule.price_change_condition === 'drop_before' ? 'Caída' : 'Subida'} {rule.price_change_threshold}%
                      </span>
                    </div>
                  )}
                  <div className="detail-item">
                    <span className="label">Hold:</span>
                    <span className="value">{rule.hold_period_days} día(s)</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="execution-section">
        <div className="execution-controls">
          <label>
            Capital Inicial:
            <input
              type="number"
              value={initialCapital}
              onChange={(e) => setInitialCapital(parseFloat(e.target.value) || 10000)}
              min="1"
              step="100"
            />
          </label>
        </div>
      </div>

      {selectedRuleId && (
        <div className="results-section">
          <h3>Resultados del Backtest</h3>
          <BacktestResults results={results} ruleId={selectedRuleId} />
        </div>
      )}
    </div>
  )
}


