import { useState, useEffect } from 'react'
import { decisionsApi, DecisionLog, DecisionLogCreate, DecisionStatistics, PortfolioItem } from '../services/api'
import { portfolioApi } from '../services/api'
import './DecisionLog.css'

export default function DecisionLogComponent() {
  const [decisions, setDecisions] = useState<DecisionLog[]>([])
  const [statistics, setStatistics] = useState<DecisionStatistics | null>(null)
  const [portfolioItems, setPortfolioItems] = useState<PortfolioItem[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [showForm, setShowForm] = useState(false)
  const [filters, setFilters] = useState<{
    status?: 'pending' | 'evaluated' | 'cancelled'
    signal_type?: string
    decision_type?: 'buy' | 'sell' | 'hold'
  }>({})
  
  const [formData, setFormData] = useState<DecisionLogCreate>({
    portfolio_item_id: 0,
    decision_type: 'hold',
    reason: '',
    signal_type: 'other',
    expected_direction: 'neutral',
    evaluation_window_days: 30,
  })

  useEffect(() => {
    loadPortfolioItems()
    loadDecisions()
    loadStatistics()
  }, [filters])

  const loadPortfolioItems = async () => {
    try {
      const items = await portfolioApi.list()
      setPortfolioItems(items)
      if (items.length > 0 && formData.portfolio_item_id === 0) {
        setFormData({ ...formData, portfolio_item_id: items[0].id })
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Error al cargar activos')
    }
  }

  const loadDecisions = async () => {
    try {
      setIsLoading(true)
      const data = await decisionsApi.list(filters)
      setDecisions(data.items)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Error al cargar decisiones')
    } finally {
      setIsLoading(false)
    }
  }

  const loadStatistics = async () => {
    try {
      const stats = await decisionsApi.getStatistics()
      setStatistics(stats)
    } catch (err: any) {
      console.error('Error al cargar estadísticas:', err)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (formData.reason.length < 20) {
      setError('El motivo debe tener al menos 20 caracteres')
      return
    }
    
    try {
      setIsLoading(true)
      setError(null)
      await decisionsApi.create(formData)
      await loadDecisions()
      await loadStatistics()
      setShowForm(false)
      setFormData({
        portfolio_item_id: portfolioItems[0]?.id || 0,
        decision_type: 'hold',
        reason: '',
        signal_type: 'other',
        expected_direction: 'neutral',
        evaluation_window_days: 30,
      })
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Error al crear decisión')
    } finally {
      setIsLoading(false)
    }
  }

  const handleEvaluateDecision = async (id: number, force: boolean = false) => {
    try {
      setIsLoading(true)
      await decisionsApi.evaluate(id, force)
      await loadDecisions()
      await loadStatistics()
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Error al evaluar decisión')
    } finally {
      setIsLoading(false)
    }
  }

  const handleEvaluateAllPending = async () => {
    try {
      setIsLoading(true)
      const result = await decisionsApi.evaluatePending(false)
      alert(`✅ ${result.message}`)
      await loadDecisions()
      await loadStatistics()
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Error al evaluar decisiones')
    } finally {
      setIsLoading(false)
    }
  }

  const formatDate = (dateString: string) => {
    const date = new Date(dateString)
    return new Intl.DateTimeFormat('es-ES', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    }).format(date)
  }

  const getDecisionTypeLabel = (type: string) => {
    const labels: Record<string, string> = {
      buy: '🟢 Comprar',
      sell: '🔴 Vender',
      hold: '⚪ Mantener'
    }
    return labels[type] || type
  }

  const getSignalTypeLabel = (type: string) => {
    const labels: Record<string, string> = {
      news: '📰 Noticia',
      price: '💰 Precio',
      both: '📰💰 Ambos',
      analysis: '📊 Análisis',
      other: '📝 Otro'
    }
    return labels[type] || type
  }

  const getResultBadge = (result?: string) => {
    if (!result) return null
    const badges: Record<string, { text: string; class: string }> = {
      hit: { text: '✅ ACIERTO', class: 'result-hit' },
      miss: { text: '❌ FALLO', class: 'result-miss' },
      partial: { text: '⚠️ PARCIAL', class: 'result-partial' }
    }
    const badge = badges[result] || { text: result, class: '' }
    return <span className={`result-badge ${badge.class}`}>{badge.text}</span>
  }

  return (
    <div className="decision-log-container">
      <div className="decision-log-header">
        <h2>📋 Log de Decisiones</h2>
        <div className="header-actions">
          <button
            className="evaluate-all-button"
            onClick={handleEvaluateAllPending}
            disabled={isLoading}
          >
            🔄 Evaluar Pendientes
          </button>
          <button
            className="add-decision-button"
            onClick={() => setShowForm(!showForm)}
          >
            {showForm ? '✕ Cancelar' : '➕ Nueva Decisión'}
          </button>
        </div>
      </div>

      {error && (
        <div className="error-banner">
          <span>⚠️ {error}</span>
          <button onClick={() => setError(null)}>✕</button>
        </div>
      )}

      {statistics && (
        <div className="statistics-panel">
          <h3>📊 Estadísticas</h3>
          <div className="stats-grid">
            <div className="stat-card">
              <div className="stat-label">Total Decisiones</div>
              <div className="stat-value">{statistics.overall.total_decisions}</div>
            </div>
            <div className="stat-card">
              <div className="stat-label">Tasa de Acierto</div>
              <div className="stat-value">{statistics.overall.overall_hit_rate.toFixed(1)}%</div>
            </div>
            <div className="stat-card">
              <div className="stat-label">Pendientes</div>
              <div className="stat-value">{statistics.overall.pending_decisions}</div>
            </div>
            <div className="stat-card">
              <div className="stat-label">Evaluadas</div>
              <div className="stat-value">{statistics.overall.evaluated_decisions}</div>
            </div>
          </div>

          {Object.keys(statistics.by_signal_type).length > 0 && (
            <div className="stats-by-type">
              <h4>Por Tipo de Señal</h4>
              <div className="stats-table">
                <table>
                  <thead>
                    <tr>
                      <th>Tipo</th>
                      <th>Total</th>
                      <th>Aciertos</th>
                      <th>Tasa</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(statistics.by_signal_type).map(([type, stats]) => (
                      <tr key={type}>
                        <td>{getSignalTypeLabel(type)}</td>
                        <td>{stats.total}</td>
                        <td>{stats.hits}</td>
                        <td>{stats.hit_rate.toFixed(1)}%</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}

      {showForm && (
        <div className="decision-form-panel">
          <h3>Nueva Decisión</h3>
          <form onSubmit={handleSubmit}>
            <div className="form-row">
              <div className="form-group">
                <label>Activo *</label>
                <select
                  value={formData.portfolio_item_id}
                  onChange={(e) => setFormData({ ...formData, portfolio_item_id: Number(e.target.value) })}
                  required
                >
                  <option value="0">-- Seleccionar --</option>
                  {portfolioItems.map(item => (
                    <option key={item.id} value={item.id}>
                      {item.symbol || item.name} ({item.asset_type})
                    </option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label>Tipo de Decisión *</label>
                <select
                  value={formData.decision_type}
                  onChange={(e) => setFormData({ ...formData, decision_type: e.target.value as any })}
                  required
                >
                  <option value="buy">🟢 Comprar</option>
                  <option value="sell">🔴 Vender</option>
                  <option value="hold">⚪ Mantener</option>
                </select>
              </div>
              <div className="form-group">
                <label>Tipo de Señal *</label>
                <select
                  value={formData.signal_type}
                  onChange={(e) => setFormData({ ...formData, signal_type: e.target.value as any })}
                  required
                >
                  <option value="news">📰 Noticia</option>
                  <option value="price">💰 Precio</option>
                  <option value="both">📰💰 Ambos</option>
                  <option value="analysis">📊 Análisis</option>
                  <option value="other">📝 Otro</option>
                </select>
              </div>
            </div>

            <div className="form-group">
              <label>Motivo * (mín. 20 caracteres)</label>
              <textarea
                value={formData.reason}
                onChange={(e) => setFormData({ ...formData, reason: e.target.value })}
                rows={4}
                placeholder="Describe el motivo de esta decisión..."
                required
              />
              <div className="char-count">{formData.reason.length}/20 mínimo</div>
            </div>

            <div className="form-row">
              <div className="form-group">
                <label>Referencia de Señal</label>
                <input
                  type="text"
                  value={formData.signal_reference || ''}
                  onChange={(e) => setFormData({ ...formData, signal_reference: e.target.value })}
                  placeholder="Ej: Noticia ID 123, Gap del 5%"
                />
              </div>
              <div className="form-group">
                <label>Dirección Esperada</label>
                <select
                  value={formData.expected_direction || 'neutral'}
                  onChange={(e) => setFormData({ ...formData, expected_direction: e.target.value as any })}
                >
                  <option value="up">📈 Subir</option>
                  <option value="down">📉 Bajar</option>
                  <option value="neutral">➡️ Neutral</option>
                </select>
              </div>
            </div>

            <div className="form-row">
              <div className="form-group">
                <label>Precio Objetivo</label>
                <input
                  type="text"
                  value={formData.expected_price || ''}
                  onChange={(e) => setFormData({ ...formData, expected_price: e.target.value })}
                  placeholder="Ej: $150.00"
                />
              </div>
              <div className="form-group">
                <label>Horizonte Temporal (días)</label>
                <input
                  type="number"
                  value={formData.expected_timeframe_days || ''}
                  onChange={(e) => setFormData({ ...formData, expected_timeframe_days: e.target.value ? Number(e.target.value) : undefined })}
                  min={1}
                />
              </div>
              <div className="form-group">
                <label>Ventana de Evaluación (días) *</label>
                <input
                  type="number"
                  value={formData.evaluation_window_days}
                  onChange={(e) => setFormData({ ...formData, evaluation_window_days: Number(e.target.value) })}
                  min={1}
                  required
                />
              </div>
            </div>

            <div className="form-group">
              <label>Expectativa Detallada</label>
              <textarea
                value={formData.expected_outcome || ''}
                onChange={(e) => setFormData({ ...formData, expected_outcome: e.target.value })}
                rows={3}
                placeholder="Describe en detalle qué esperas que suceda..."
              />
            </div>

            <div className="form-actions">
              <button type="submit" className="save-button" disabled={isLoading || formData.reason.length < 20}>
                💾 Guardar Decisión
              </button>
              <button type="button" className="cancel-button" onClick={() => setShowForm(false)}>
                ✕ Cancelar
              </button>
            </div>
          </form>
        </div>
      )}

      <div className="filters-panel">
        <label>
          <input
            type="checkbox"
            checked={filters.status === 'pending'}
            onChange={(e) => setFilters({ ...filters, status: e.target.checked ? 'pending' : undefined })}
          />
          Solo Pendientes
        </label>
        <label>
          <input
            type="checkbox"
            checked={filters.status === 'evaluated'}
            onChange={(e) => setFilters({ ...filters, status: e.target.checked ? 'evaluated' : undefined })}
          />
          Solo Evaluadas
        </label>
      </div>

      {isLoading && decisions.length === 0 ? (
        <div className="loading">Cargando decisiones...</div>
      ) : decisions.length === 0 ? (
        <div className="empty-state">
          <p>No hay decisiones registradas.</p>
          <p className="hint">Crea una nueva decisión para comenzar a trackear tus decisiones de trading.</p>
        </div>
      ) : (
        <div className="decisions-list">
          {decisions.map((decision) => (
            <div key={decision.id} className={`decision-card ${decision.status}`}>
              <div className="decision-header">
                <div className="decision-main-info">
                  <h3>
                    {decision.portfolio_item_symbol && (
                      <span className="symbol">{decision.portfolio_item_symbol}</span>
                    )}
                    {decision.portfolio_item_name || 'Activo'}
                  </h3>
                  <div className="decision-badges">
                    {getDecisionTypeLabel(decision.decision_type)}
                    {getSignalTypeLabel(decision.signal_type)}
                    {decision.status === 'pending' && <span className="status-badge pending">⏳ Pendiente</span>}
                    {decision.status === 'evaluated' && decision.evaluation && getResultBadge(decision.evaluation.result)}
                  </div>
                </div>
                <div className="decision-date">
                  {formatDate(decision.decided_at)}
                </div>
              </div>

              <div className="decision-content">
                <div className="decision-reason">
                  <strong>Motivo:</strong> {decision.reason}
                </div>

                {decision.expected_outcome && (
                  <div className="decision-expectation">
                    <strong>Expectativa:</strong> {decision.expected_outcome}
                  </div>
                )}

                <div className="decision-details">
                  {decision.expected_direction && (
                    <span>Dirección: {decision.expected_direction === 'up' ? '📈 Subir' : decision.expected_direction === 'down' ? '📉 Bajar' : '➡️ Neutral'}</span>
                  )}
                  {decision.expected_price && <span>Precio Objetivo: {decision.expected_price}</span>}
                  {decision.expected_timeframe_days && <span>Horizonte: {decision.expected_timeframe_days} días</span>}
                  <span>Ventana de Evaluación: {decision.evaluation_window_days} días</span>
                </div>

                {decision.evaluation && (
                  <div className="evaluation-details">
                    <h4>📊 Resultado de Evaluación</h4>
                    <div className="evaluation-metrics">
                      {decision.evaluation.price_at_decision && (
                        <span>Precio al Decidir: ${decision.evaluation.price_at_decision.toFixed(2)}</span>
                      )}
                      {decision.evaluation.price_at_evaluation && (
                        <span>Precio al Evaluar: ${decision.evaluation.price_at_evaluation.toFixed(2)}</span>
                      )}
                      {decision.evaluation.price_change_pct !== undefined && (
                        <span className={decision.evaluation.price_change_pct >= 0 ? 'positive' : 'negative'}>
                          Cambio: {decision.evaluation.price_change_pct >= 0 ? '+' : ''}{decision.evaluation.price_change_pct.toFixed(2)}%
                        </span>
                      )}
                    </div>
                    {decision.evaluation.evaluation_notes && (
                      <div className="evaluation-notes">
                        <strong>Notas:</strong> {decision.evaluation.evaluation_notes}
                      </div>
                    )}
                    {decision.evaluation.lessons_learned && (
                      <div className="lessons-learned">
                        <strong>Lecciones:</strong> {decision.evaluation.lessons_learned}
                      </div>
                    )}
                  </div>
                )}

                {decision.status === 'pending' && (
                  <div className="decision-actions">
                    <button
                      className="evaluate-button"
                      onClick={() => handleEvaluateDecision(decision.id, false)}
                      disabled={isLoading}
                    >
                      ✅ Evaluar (si cumplió ventana)
                    </button>
                    <button
                      className="force-evaluate-button"
                      onClick={() => handleEvaluateDecision(decision.id, true)}
                      disabled={isLoading}
                    >
                      🔄 Forzar Evaluación
                    </button>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}



