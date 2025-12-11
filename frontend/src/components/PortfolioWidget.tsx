import { useState, useEffect } from 'react'
import { portfolioApi, PortfolioItem, RiskDashboard } from '../services/api'
import './WidgetShared.css'
import './PortfolioWidget.css'

interface PortfolioWidgetProps {
  onUpdate?: () => void
  refreshTrigger?: number
  onViewDetail?: () => void
  onRebalance?: () => void
}

export default function PortfolioWidget({ onUpdate, refreshTrigger, onViewDetail, onRebalance }: PortfolioWidgetProps) {
  const [items, setItems] = useState<PortfolioItem[]>([])
  const [dashboard, setDashboard] = useState<RiskDashboard | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadData()
  }, [refreshTrigger])

  const loadData = async () => {
    try {
      setIsLoading(true)
      setError(null)
      const [portfolioData, dashboardData] = await Promise.all([
        portfolioApi.list(),
        portfolioApi.getRiskDashboard(5)
      ])
      setItems(portfolioData)
      setDashboard(dashboardData)
      onUpdate?.()
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Error al cargar la cartera')
    } finally {
      setIsLoading(false)
    }
  }

  const formatCurrency = (value: number, currency: string = 'USD') => {
    return new Intl.NumberFormat('es-ES', {
      style: 'currency',
      currency: currency,
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(value)
  }

  const formatPercentage = (value: number) => {
    return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`
  }

  const getRecentMovements = () => {
    return items
      .filter(item => {
        if (!item.updated_at) return false
        const updatedDate = new Date(item.updated_at)
        const daysDiff = (Date.now() - updatedDate.getTime()) / (1000 * 60 * 60 * 24)
        return daysDiff <= 7
      })
      .sort((a, b) => {
        const dateA = a.updated_at ? new Date(a.updated_at).getTime() : 0
        const dateB = b.updated_at ? new Date(b.updated_at).getTime() : 0
        return dateB - dateA
      })
      .slice(0, 3)
  }

  const formatDate = (dateString: string) => {
    const date = new Date(dateString)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24))
    
    if (diffDays === 0) return 'Hoy'
    if (diffDays === 1) return 'Ayer'
    if (diffDays < 7) return `Hace ${diffDays} días`
    return date.toLocaleDateString('es-ES', { day: 'numeric', month: 'short' })
  }

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

  if (error) {
    return (
      <div className="portfolio-widget" role="region" aria-label="Widget de Cartera">
        <div className="widget-header">
          <h2>💼 Mi Cartera</h2>
          <button 
            className="refresh-btn" 
            onClick={loadData}
            aria-label="Reintentar cargar cartera"
          >
            🔄
          </button>
        </div>
        <div className="error-message" role="alert" aria-live="assertive">{error}</div>
      </div>
    )
  }

  const portfolioValue = dashboard?.portfolio_value || 0
  const topPositions = dashboard?.top_concentrations || []
  const topSectors = dashboard?.exposure_by_sector || []
  const recentMovements = getRecentMovements()

  return (
    <div className="portfolio-widget" role="region" aria-label="Widget de Cartera">
      <div className="widget-header">
        <h2>💼 Mi Cartera</h2>
        <div className="widget-actions">
          <button 
            className="refresh-btn" 
            onClick={loadData} 
            title="Actualizar cartera"
            aria-label="Actualizar datos de la cartera"
          >
            🔄
          </button>
          {onViewDetail && (
            <button 
              className="action-btn" 
              onClick={onViewDetail} 
              title="Ver detalle completo"
              aria-label="Ver detalle completo de la cartera"
            >
              📊
            </button>
          )}
          {onRebalance && (
            <button 
              className="action-btn" 
              onClick={onRebalance} 
              title="Rebalancear cartera"
              aria-label="Rebalancear la cartera"
            >
              ⚖️
            </button>
          )}
        </div>
      </div>

      {portfolioValue === 0 ? (
        <div className="empty-state">
          <p>No hay activos en tu cartera.</p>
          <p className="hint">Agrega activos para ver métricas y análisis.</p>
        </div>
      ) : (
        <div className="widget-content">
          <div className="metrics-row">
            <div className="metric-card primary">
              <div className="metric-label">Valor Total</div>
              <div className="metric-value-large">{formatCurrency(portfolioValue)}</div>
              <div className="metric-subtitle">{items.length} activo{items.length !== 1 ? 's' : ''}</div>
            </div>
            <div className="metric-card">
              <div className="metric-label">Variación Diaria</div>
              <div className="metric-value">--</div>
              <div className="metric-subtitle">Estimada</div>
            </div>
            <div className="metric-card">
              <div className="metric-label">Variación MTD</div>
              <div className="metric-value">--</div>
              <div className="metric-subtitle">Mes actual</div>
            </div>
          </div>

          <div className="sections-grid">
            <div className="section-card">
              <h3>🎯 Top Posiciones</h3>
              {topPositions.length > 0 ? (
                <div className="positions-list">
                  {topPositions.map((pos, idx) => (
                    <div key={pos.id} className="position-item">
                      <div className="position-rank">#{idx + 1}</div>
                      <div className="position-info">
                        <div className="position-name">
                          {pos.name}
                          {pos.symbol && <span className="position-symbol"> ({pos.symbol})</span>}
                        </div>
                        <div className="position-type">{pos.asset_type}</div>
                      </div>
                      <div className="position-metrics">
                        <div className="position-pct">{formatPercentage(pos.percentage)}</div>
                        <div className="position-value">{formatCurrency(pos.value, pos.currency)}</div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="empty-section">No hay posiciones</div>
              )}
            </div>

            <div className="section-card">
              <h3>📈 Por Sector</h3>
              {topSectors.length > 0 ? (
                <div className="sectors-list">
                  {topSectors.slice(0, 3).map((sector) => (
                    <div key={sector.sector} className="sector-item">
                      <div className="sector-header">
                        <span className="sector-name">{sector.sector.toUpperCase()}</span>
                        <span className="sector-pct">{formatPercentage(sector.percentage)}</span>
                      </div>
                      <div className="sector-bar">
                        <div
                          className="sector-bar-fill"
                          style={{ width: `${sector.percentage}%` }}
                        />
                      </div>
                      <div className="sector-value">{formatCurrency(sector.value)}</div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="empty-section">No hay sectores</div>
              )}
            </div>
          </div>

          {recentMovements.length > 0 && (
            <div className="section-card movements-section">
              <h3>🕐 Movimientos Recientes</h3>
              <div className="movements-list">
                {recentMovements.map((item) => (
                  <div key={item.id} className="movement-item">
                    <div className="movement-name">{item.name}</div>
                    <div className="movement-date">{formatDate(item.updated_at)}</div>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="quick-links">
            {onViewDetail && (
              <button className="quick-link-btn" onClick={onViewDetail}>
                📊 Ver Detalle Completo
              </button>
            )}
            {onRebalance && (
              <button className="quick-link-btn" onClick={onRebalance}>
                ⚖️ Rebalancear Cartera
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

