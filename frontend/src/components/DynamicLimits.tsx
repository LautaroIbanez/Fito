import { useState, useEffect } from 'react'
import { limitsApi, DynamicLimit } from '../services/api'
import './DynamicLimits.css'

export default function DynamicLimits() {
  const [limits, setLimits] = useState<DynamicLimit[]>([])
  const [exceededCount, setExceededCount] = useState(0)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [showExceededOnly, setShowExceededOnly] = useState(false)

  useEffect(() => {
    loadLimits()
  }, [showExceededOnly])

  const loadLimits = async () => {
    try {
      setIsLoading(true)
      setError(null)
      const data = await limitsApi.list(showExceededOnly)
      setLimits(data.items)
      setExceededCount(data.exceeded_count)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Error al cargar límites')
    } finally {
      setIsLoading(false)
    }
  }

  const handleCalculate = async (force: boolean = false) => {
    try {
      setIsLoading(true)
      setError(null)
      const data = await limitsApi.calculate(force)
      setLimits(data.items)
      setExceededCount(data.exceeded_count)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Error al calcular límites')
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

  if (isLoading && limits.length === 0) {
    return (
      <div className="dynamic-limits-container">
        <h2>⚠️ Límites Dinámicos</h2>
        <div className="loading">Cargando...</div>
      </div>
    )
  }

  return (
    <div className="dynamic-limits-container">
      <div className="limits-header">
        <h2>⚠️ Límites Dinámicos</h2>
        <div className="header-actions">
          <button
            className="calculate-button"
            onClick={() => handleCalculate(false)}
            disabled={isLoading}
          >
            🔄 Calcular
          </button>
          <button
            className="force-calculate-button"
            onClick={() => handleCalculate(true)}
            disabled={isLoading}
            title="Forzar recálculo"
          >
            🔁 Forzar
          </button>
        </div>
      </div>

      {error && (
        <div className="error-banner">
          <span>⚠️ {error}</span>
          <button onClick={() => setError(null)}>✕</button>
        </div>
      )}

      {limits.length === 0 ? (
        <div className="empty-state">
          <p>No hay límites calculados.</p>
          <p className="hint">
            Haz clic en "Calcular" para analizar tu cartera y establecer límites basados en drawdown y volatilidad.
          </p>
          <button className="calculate-button" onClick={() => handleCalculate(false)}>
            🔄 Calcular Límites
          </button>
        </div>
      ) : (
        <>
          <div className="limits-summary">
            <div className="summary-item">
              <span className="summary-label">Total Activos:</span>
              <span className="summary-value">{limits.length}</span>
            </div>
            <div className="summary-item exceeded">
              <span className="summary-label">Límites Excedidos:</span>
              <span className="summary-value">{exceededCount}</span>
            </div>
            <div className="filter-toggle">
              <label>
                <input
                  type="checkbox"
                  checked={showExceededOnly}
                  onChange={(e) => setShowExceededOnly(e.target.checked)}
                />
                Solo excedidos
              </label>
            </div>
          </div>

          <div className="limits-list">
            {limits.map((limit) => (
              <div
                key={limit.id}
                className={`limit-card ${limit.is_exceeded ? 'exceeded' : 'within-limit'}`}
              >
                <div className="limit-card-header">
                  <div className="limit-asset-info">
                    <h3>
                      {limit.portfolio_item_symbol && (
                        <span className="symbol">{limit.portfolio_item_symbol}</span>
                      )}
                      {limit.portfolio_item_name || 'Activo'}
                    </h3>
                    {limit.is_exceeded && (
                      <span className="exceeded-badge">⚠️ LÍMITE EXCEDIDO</span>
                    )}
                  </div>
                </div>

                <div className="limit-metrics">
                  <div className="metric-row primary">
                    <div className="metric-item">
                      <span className="metric-label">Posición Actual</span>
                      <span className={`metric-value ${limit.is_exceeded ? 'exceeded-value' : ''}`}>
                        {limit.current_position_pct.toFixed(2)}%
                      </span>
                    </div>
                    <div className="metric-item">
                      <span className="metric-label">Límite Máximo</span>
                      <span className="metric-value limit-value">
                        {limit.max_position_pct.toFixed(2)}%
                      </span>
                    </div>
                    {limit.is_exceeded && (
                      <div className="metric-item exceeded-item">
                        <span className="metric-label">Exceso</span>
                        <span className="metric-value exceeded-value">
                          +{limit.excess_amount_pct.toFixed(2)}%
                        </span>
                      </div>
                    )}
                  </div>

                  <div className="metric-row">
                    {limit.recent_drawdown_pct !== undefined && limit.recent_drawdown_pct !== null && (
                      <div className="metric-item">
                        <span className="metric-label">Drawdown Reciente</span>
                        <span className="metric-value">{limit.recent_drawdown_pct.toFixed(2)}%</span>
                      </div>
                    )}
                    {limit.realized_volatility !== undefined && limit.realized_volatility !== null && (
                      <div className="metric-item">
                        <span className="metric-label">Vol. Realizada</span>
                        <span className="metric-value">{limit.realized_volatility.toFixed(2)}%</span>
                      </div>
                    )}
                    {limit.implied_volatility !== undefined && limit.implied_volatility !== null && (
                      <div className="metric-item">
                        <span className="metric-label">Vol. Implícita</span>
                        <span className="metric-value">{limit.implied_volatility.toFixed(2)}%</span>
                      </div>
                    )}
                    {limit.suggested_stop_loss_pct !== undefined && limit.suggested_stop_loss_pct !== null && (
                      <div className="metric-item">
                        <span className="metric-label">Stop Loss Sugerido</span>
                        <span className="metric-value stop-loss-value">
                          {limit.suggested_stop_loss_pct.toFixed(2)}%
                        </span>
                      </div>
                    )}
                  </div>
                </div>

                {limit.is_exceeded && (
                  <div className="exceeded-alert">
                    <div className="alert-header">
                      <h4>⚠️ Reducción Recomendada</h4>
                    </div>
                    <div className="alert-content">
                      <div className="reduction-suggestion">
                        <div className="suggestion-item">
                          <span className="suggestion-label">Reducción Sugerida:</span>
                          <span className="suggestion-value">
                            {limit.suggested_reduction_pct.toFixed(2)}%
                          </span>
                        </div>
                        {limit.current_value && (
                          <div className="suggestion-item">
                            <span className="suggestion-label">Valor a Reducir:</span>
                            <span className="suggestion-value">
                              ${(limit.current_value * (limit.suggested_reduction_pct / 100)).toLocaleString('es-ES', {
                                minimumFractionDigits: 2,
                                maximumFractionDigits: 2
                              })}
                            </span>
                          </div>
                        )}
                        <div className="suggestion-item">
                          <span className="suggestion-label">Tamaño Ajustado Recomendado:</span>
                          <span className="suggestion-value">
                            {limit.risk_adjusted_size_pct.toFixed(2)}%
                          </span>
                        </div>
                      </div>
                      <div className="alert-note">
                        <p>
                          <strong>Recomendación:</strong> Reduce tu posición en este activo en al menos{' '}
                          <strong>{limit.suggested_reduction_pct.toFixed(2)}%</strong> para volver dentro del límite
                          basado en drawdown y volatilidad.
                        </p>
                      </div>
                    </div>
                  </div>
                )}

                {!limit.is_exceeded && (
                  <div className="within-limit-info">
                    <div className="info-item">
                      <span className="info-label">Tamaño Ajustado por Riesgo:</span>
                      <span className="info-value">{limit.risk_adjusted_size_pct.toFixed(2)}%</span>
                    </div>
                  </div>
                )}

                <div className="limit-footer">
                  <span className="calculation-date">
                    Calculado: {formatDate(limit.calculated_at)}
                  </span>
                  {limit.next_calculation_at && (
                    <span className="next-calculation">
                      Próximo: {formatDate(limit.next_calculation_at)}
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  )
}





