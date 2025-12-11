import { useState, useEffect } from 'react'
import { alertsApi, AlertHistory } from '../services/api'
import './AlertHistory.css'

export default function AlertHistoryComponent() {
  const [alerts, setAlerts] = useState<AlertHistory[]>([])
  const [total, setTotal] = useState(0)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [skip, setSkip] = useState(0)
  const limit = 20

  useEffect(() => {
    loadAlerts()
  }, [skip])

  const loadAlerts = async () => {
    try {
      setIsLoading(true)
      setError(null)
      const data = await alertsApi.getAlertHistory(skip, limit)
      setAlerts(data.items)
      setTotal(data.total)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Error al cargar alertas')
    } finally {
      setIsLoading(false)
    }
  }

  const handleCheckTriggers = async () => {
    try {
      setIsLoading(true)
      setError(null)
      const data = await alertsApi.checkTriggers()
      if (data.total > 0) {
        loadAlerts() // Recargar para ver las nuevas alertas
      } else {
        alert('No se generaron nuevas alertas. Verifica que los triggers estén activos y que haya datos de precio disponibles.')
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Error al verificar triggers')
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

  if (isLoading && alerts.length === 0) {
    return (
      <div className="alert-history-container">
        <h2>📋 Historial de Alertas</h2>
        <div className="loading">Cargando...</div>
      </div>
    )
  }

  return (
    <div className="alert-history-container">
      <div className="history-header">
        <h2>📋 Historial de Alertas ({total})</h2>
        <button className="check-button" onClick={handleCheckTriggers} disabled={isLoading}>
          🔍 Verificar Triggers
        </button>
      </div>

      {error && (
        <div className="error-banner">
          <span>⚠️ {error}</span>
          <button onClick={() => setError(null)}>✕</button>
        </div>
      )}

      {alerts.length === 0 ? (
        <div className="empty-state">
          <p>No hay alertas registradas aún.</p>
          <p className="hint">
            Las alertas se generan cuando se cumplen las condiciones de precio y noticias.
            Usa "Verificar Triggers" para comprobar manualmente.
          </p>
          <p className="note">
            Nota: Para que las alertas se generen automáticamente, necesitas integrar una API de precios
            en tiempo real (Alpha Vantage, Yahoo Finance, etc.).
          </p>
        </div>
      ) : (
        <>
          <div className="alerts-list">
            {alerts.map((alert) => (
              <div key={alert.id} className="alert-item">
                <div className="alert-header">
                  <h3>{alert.trigger_name || `Trigger #${alert.trigger_id}`}</h3>
                  <span className="alert-date">{formatDate(alert.triggered_at)}</span>
                </div>

                <div className="alert-summary">
                  <p className="summary-text">{alert.alert_summary}</p>
                </div>

                <div className="alert-details">
                  <div className="detail-section">
                    <h4>Condiciones</h4>
                    <div className="condition-badges">
                      <span className={`badge ${alert.price_condition_met ? 'met' : 'not-met'}`}>
                        {alert.price_condition_met ? '✅' : '❌'} Precio
                      </span>
                      <span className={`badge ${alert.news_condition_met ? 'met' : 'not-met'}`}>
                        {alert.news_condition_met ? '✅' : '❌'} Noticias
                      </span>
                    </div>
                  </div>

                  {alert.symbol && (
                    <div className="detail-row">
                      <span className="detail-label">Activo:</span>
                      <span className="detail-value">{alert.symbol} - {alert.asset_name}</span>
                    </div>
                  )}

                  {alert.price_value !== undefined && (
                    <div className="detail-row">
                      <span className="detail-label">Precio:</span>
                      <span className="detail-value">${alert.price_value.toFixed(2)}</span>
                    </div>
                  )}

                  {alert.price_change_percent !== undefined && (
                    <div className="detail-row">
                      <span className="detail-label">Cambio:</span>
                      <span className={`detail-value ${alert.price_change_percent >= 0 ? 'positive' : 'negative'}`}>
                        {alert.price_change_percent >= 0 ? '+' : ''}{alert.price_change_percent.toFixed(2)}%
                      </span>
                    </div>
                  )}

                  {alert.gap_percent !== undefined && (
                    <div className="detail-row">
                      <span className="detail-label">Gap:</span>
                      <span className={`detail-value ${alert.gap_percent >= 0 ? 'positive' : 'negative'}`}>
                        {alert.gap_percent >= 0 ? '+' : ''}{alert.gap_percent.toFixed(2)}%
                      </span>
                    </div>
                  )}

                  <div className="detail-row">
                    <span className="detail-label">Noticias relevantes:</span>
                    <span className="detail-value">
                      {alert.relevant_news_count} (Score máx: {alert.highest_news_score?.toFixed(2)})
                    </span>
                  </div>
                </div>

                {alert.expected_impact && (
                  <div className="alert-impact">
                    <h4>Impacto Esperado</h4>
                    <p>{alert.expected_impact}</p>
                  </div>
                )}

                {alert.suggested_action && (
                  <div className="alert-action">
                    <h4>Acción Sugerida</h4>
                    <p>{alert.suggested_action}</p>
                  </div>
                )}
              </div>
            ))}
          </div>

          <div className="pagination">
            <button
              onClick={() => setSkip(Math.max(0, skip - limit))}
              disabled={skip === 0 || isLoading}
            >
              ← Anterior
            </button>
            <span>
              Página {Math.floor(skip / limit) + 1} de {Math.ceil(total / limit)}
            </span>
            <button
              onClick={() => setSkip(skip + limit)}
              disabled={skip + limit >= total || isLoading}
            >
              Siguiente →
            </button>
          </div>
        </>
      )}
    </div>
  )
}





