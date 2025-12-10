import { useState, useEffect } from 'react'
import { portfolioApi, RiskDashboard as RiskDashboardData } from '../services/api'
import './RiskDashboard.css'

interface RiskDashboardProps {
  onUpdate?: () => void
  refreshTrigger?: number
}

export default function RiskDashboard({ onUpdate, refreshTrigger }: RiskDashboardProps) {
  const [dashboard, setDashboard] = useState<RiskDashboardData | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadDashboard()
  }, [refreshTrigger])

  const loadDashboard = async () => {
    try {
      setIsLoading(true)
      setError(null)
      const data = await portfolioApi.getRiskDashboard(5)
      setDashboard(data)
      onUpdate?.()
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Error al cargar el dashboard de riesgo')
    } finally {
      setIsLoading(false)
    }
  }

  const formatCurrency = (value: number, currency: string = 'USD') => {
    return new Intl.NumberFormat('es-ES', {
      style: 'currency',
      currency: currency,
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(value)
  }

  const formatPercentage = (value: number) => {
    return `${value.toFixed(2)}%`
  }

  if (isLoading) {
    return (
      <div className="risk-dashboard-container">
        <div className="dashboard-header">
          <h2>📊 Dashboard de Riesgo</h2>
          <button className="refresh-button" onClick={loadDashboard} disabled>
            🔄 Actualizando...
          </button>
        </div>
        <div className="loading">Cargando métricas de riesgo...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="risk-dashboard-container">
        <div className="dashboard-header">
          <h2>📊 Dashboard de Riesgo</h2>
          <button className="refresh-button" onClick={loadDashboard}>
            🔄 Actualizar
          </button>
        </div>
        <div className="error-message">{error}</div>
      </div>
    )
  }

  if (!dashboard || dashboard.portfolio_value === 0) {
    return (
      <div className="risk-dashboard-container">
        <div className="dashboard-header">
          <h2>📊 Dashboard de Riesgo</h2>
          <button className="refresh-button" onClick={loadDashboard}>
            🔄 Actualizar
          </button>
        </div>
        <div className="empty-state">
          <p>No hay datos de cartera para calcular métricas de riesgo.</p>
          <p className="hint">Agrega activos a tu cartera para ver el análisis de riesgo.</p>
        </div>
      </div>
    )
  }

  return (
    <div className="risk-dashboard-container">
      <div className="dashboard-header">
        <h2>📊 Dashboard de Riesgo</h2>
        <button className="refresh-button" onClick={loadDashboard}>
          🔄 Actualizar
        </button>
      </div>

      <div className="dashboard-content">
        {/* Valor total del portafolio */}
        <div className="metric-card portfolio-value-card">
          <h3>💼 Valor Total del Portafolio</h3>
          <div className="metric-value-large">
            {formatCurrency(dashboard.portfolio_value)}
          </div>
        </div>

        {/* Top Concentraciones */}
        <div className="metric-card">
          <h3>🎯 Top 5 Concentraciones</h3>
          <div className="concentrations-list">
            {dashboard.top_concentrations.map((asset, idx) => (
              <div key={asset.id} className="concentration-item">
                <div className="concentration-rank">#{idx + 1}</div>
                <div className="concentration-details">
                  <div className="concentration-name">
                    {asset.name}
                    {asset.symbol && <span className="concentration-symbol"> ({asset.symbol})</span>}
                  </div>
                  <div className="concentration-type">{asset.asset_type}</div>
                </div>
                <div className="concentration-metrics">
                  <div className="concentration-percentage">{formatPercentage(asset.percentage)}</div>
                  <div className="concentration-value">{formatCurrency(asset.value, asset.currency)}</div>
                </div>
                <div className="concentration-bar">
                  <div
                    className="concentration-bar-fill"
                    style={{ width: `${asset.percentage}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Exposición por Sector */}
        <div className="metric-card">
          <h3>📈 Exposición por Sector</h3>
          <div className="sector-list">
            {dashboard.exposure_by_sector.map((sector) => (
              <div key={sector.sector} className="sector-item">
                <div className="sector-header">
                  <span className="sector-name">{sector.sector.toUpperCase()}</span>
                  <span className="sector-count">{sector.asset_count} activo{sector.asset_count !== 1 ? 's' : ''}</span>
                </div>
                <div className="sector-bar">
                  <div
                    className="sector-bar-fill"
                    style={{ width: `${sector.percentage}%` }}
                  />
                </div>
                <div className="sector-metrics">
                  <span className="sector-percentage">{formatPercentage(sector.percentage)}</span>
                  <span className="sector-value">{formatCurrency(sector.value)}</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Métricas de Riesgo: Volatilidad */}
        <div className="metric-card risk-metrics-card">
          <h3>📉 Volatilidad Estimada</h3>
          <div className="volatility-grid">
            <div className="volatility-item">
              <div className="volatility-label">30 Días</div>
              <div className="volatility-value">{formatPercentage(dashboard.volatility.volatility_30d)}</div>
            </div>
            <div className="volatility-item">
              <div className="volatility-label">90 Días</div>
              <div className="volatility-value">{formatPercentage(dashboard.volatility.volatility_90d)}</div>
            </div>
            <div className="volatility-item">
              <div className="volatility-label">Anual</div>
              <div className="volatility-value">{formatPercentage(dashboard.volatility.annual_volatility)}</div>
            </div>
          </div>
        </div>

        {/* Métricas de Riesgo: VaR */}
        <div className="metric-card risk-metrics-card">
          <h3>⚠️ Value at Risk (VaR)</h3>
          <div className="var-grid">
            <div className="var-section">
              <h4>30 Días</h4>
              <div className="var-item">
                <span className="var-label">95% Confianza:</span>
                <span className="var-value var-warning">
                  {formatCurrency(dashboard.var.var_30d_95)}
                </span>
              </div>
              <div className="var-item">
                <span className="var-label">99% Confianza:</span>
                <span className="var-value var-danger">
                  {formatCurrency(dashboard.var.var_30d_99)}
                </span>
              </div>
            </div>
            <div className="var-section">
              <h4>90 Días</h4>
              <div className="var-item">
                <span className="var-label">95% Confianza:</span>
                <span className="var-value var-warning">
                  {formatCurrency(dashboard.var.var_90d_95)}
                </span>
              </div>
              <div className="var-item">
                <span className="var-label">99% Confianza:</span>
                <span className="var-value var-danger">
                  {formatCurrency(dashboard.var.var_90d_99)}
                </span>
              </div>
            </div>
          </div>
          <div className="var-note">
            <small>⚠️ VaR representa la pérdida máxima estimada en el período indicado con el nivel de confianza dado.</small>
          </div>
        </div>
      </div>
    </div>
  )
}

