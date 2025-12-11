import { useState, useEffect } from 'react'
import { portfolioApi, PortfolioItem, RiskDashboard } from '../services/api'
import './PortfolioSummaryCard.css'

interface ProfessionalInsight {
  title: string
  explanation: string
}

interface PortfolioSummaryCardProps {
  refreshTrigger?: number
}

export default function PortfolioSummaryCard({ refreshTrigger }: PortfolioSummaryCardProps) {
  const [portfolioValue, setPortfolioValue] = useState<number>(0)
  const [cashAvailable, setCashAvailable] = useState<number | null>(null)
  const [topHolding, setTopHolding] = useState<{ name: string; symbol?: string; percentage: number; value: number } | null>(null)
  const [dataSource, setDataSource] = useState<string>('')
  const [lastUpdated, setLastUpdated] = useState<string>('')
  const [isLoading, setIsLoading] = useState(false)
  const [hasData, setHasData] = useState(false)
  const [professionalInsights, setProfessionalInsights] = useState<ProfessionalInsight[]>([])
  const [loadingInsights, setLoadingInsights] = useState(false)

  useEffect(() => {
    loadSummaryData()
  }, [refreshTrigger])

  const loadSummaryData = async () => {
    try {
      setIsLoading(true)
      const [items, dashboard] = await Promise.all([
        portfolioApi.list(),
        portfolioApi.getRiskDashboard(5)
      ])

      const totalValue = dashboard.portfolio_value || 0
      const topPositions = dashboard.top_concentrations || []
      
      setPortfolioValue(totalValue)
      setHasData(items.length > 0)
      
      // Obtener top holding
      if (topPositions.length > 0) {
        const top = topPositions[0]
        setTopHolding({
          name: top.name,
          symbol: top.symbol,
          percentage: top.percentage,
          value: top.value
        })
      } else {
        setTopHolding(null)
      }

      // Calcular efectivo disponible (buscar items de tipo "efectivo" o "cash" o "divisas")
      const cashItems = items.filter(item => 
        item.asset_type?.toLowerCase().includes('efectivo') || 
        item.asset_type?.toLowerCase().includes('cash') ||
        item.asset_type?.toLowerCase() === 'divisas'
      )
      
      let cash = 0
      cashItems.forEach(item => {
        if (item.total_value) {
          const value = parseFloat(item.total_value.replace(/,/g, '')) || 0
          cash += value
        }
      })
      
      setCashAvailable(cash > 0 ? cash : null)

      // Determinar fuente de datos
      const hasValues = items.some(item => item.total_value)
      setDataSource(hasValues ? 'Datos de cartera ingresados' : 'Estimaciones básicas')
      
      // Fecha de última actualización
      const mostRecentUpdate = items
        .map(item => item.updated_at ? new Date(item.updated_at).getTime() : 0)
        .reduce((max, date) => Math.max(max, date), 0)
      
      if (mostRecentUpdate > 0) {
        const updateDate = new Date(mostRecentUpdate)
        const now = new Date()
        const diffHours = Math.floor((now.getTime() - updateDate.getTime()) / (1000 * 60 * 60))
        
        if (diffHours < 1) {
          setLastUpdated('Actualizado hace menos de 1 hora')
        } else if (diffHours < 24) {
          setLastUpdated(`Actualizado hace ${diffHours} hora${diffHours > 1 ? 's' : ''}`)
        } else {
          const diffDays = Math.floor(diffHours / 24)
          setLastUpdated(`Actualizado hace ${diffDays} día${diffDays > 1 ? 's' : ''}`)
        }
      } else {
        setLastUpdated('Datos iniciales')
      }

      // Cargar insights profesionales si hay datos
      if (items.length > 0 && totalValue > 0) {
        loadProfessionalInsights()
      } else {
        setProfessionalInsights([])
      }

    } catch (err: any) {
      console.error('Error al cargar resumen de cartera:', err)
      setHasData(false)
    } finally {
      setIsLoading(false)
    }
  }

  const loadProfessionalInsights = async () => {
    try {
      setLoadingInsights(true)
      const data = await portfolioApi.getProfessionalInsights()
      setProfessionalInsights(data.insights || [])
    } catch (err: any) {
      console.error('Error al cargar insights profesionales:', err)
      setProfessionalInsights([])
    } finally {
      setLoadingInsights(false)
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

  if (isLoading) {
    return (
      <div className="portfolio-summary-card">
        <div className="summary-loading">Cargando resumen...</div>
      </div>
    )
  }

  if (!hasData) {
    return (
      <div className="portfolio-summary-card">
        <h3 className="summary-title">📊 Resumen de tu Cartera</h3>
        <div className="summary-empty">
          <p>No hay datos de cartera disponibles aún.</p>
          <p className="summary-hint">Agrega activos a tu cartera para ver un resumen personalizado.</p>
        </div>
      </div>
    )
  }

  return (
    <div className="portfolio-summary-card">
      <h3 className="summary-title">📊 Resumen de tu Cartera</h3>
      
      <div className="summary-content">
        <div className="summary-metric">
          <div className="metric-label">Valor Total</div>
          <div className="metric-value">{formatCurrency(portfolioValue)}</div>
          <div className="metric-note">Suma de todos tus activos</div>
        </div>

        <div className="summary-metric">
          <div className="metric-label">Efectivo Disponible</div>
          <div className="metric-value">
            {cashAvailable !== null ? formatCurrency(cashAvailable) : 'No especificado'}
          </div>
          <div className="metric-note">
            {cashAvailable !== null 
              ? `Liquidez para oportunidades o emergencias`
              : 'Agrega efectivo o divisas a tu cartera para ver este valor'}
          </div>
        </div>

        <div className="summary-metric">
          <div className="metric-label">Posición Principal</div>
          <div className="metric-value">
            {topHolding ? (
              <>
                {topHolding.name}
                {topHolding.symbol && <span className="holding-symbol"> ({topHolding.symbol})</span>}
              </>
            ) : 'N/A'}
          </div>
          <div className="metric-note">
            {topHolding 
              ? `${topHolding.percentage.toFixed(1)}% de tu cartera (${formatCurrency(topHolding.value)})`
              : 'No hay posiciones registradas'}
          </div>
        </div>

        <div className="summary-metric">
          <div className="metric-label">Fuente de Datos</div>
          <div className="metric-value-small">{dataSource}</div>
          <div className="metric-note">{lastUpdated}</div>
        </div>
      </div>

      {loadingInsights ? (
        <div className="summary-actions">
          <h4 className="actions-title">💡 A qué prestar atención</h4>
          <div className="insights-loading">Analizando cartera con IA...</div>
        </div>
      ) : professionalInsights.length > 0 ? (
        <div className="summary-actions">
          <h4 className="actions-title">💡 A qué prestar atención</h4>
          <ul className="actions-list">
            {professionalInsights.map((insight, index) => (
              <li key={index} className="action-item">
                <strong>{insight.title}</strong>
                <p className="insight-explanation">{insight.explanation}</p>
              </li>
            ))}
          </ul>
        </div>
      ) : hasData && (
        <div className="summary-actions">
          <h4 className="actions-title">💡 A qué prestar atención</h4>
          <div className="insights-empty">
            <p>Completa los datos de tu cartera para recibir análisis profesional personalizado.</p>
          </div>
        </div>
      )}
    </div>
  )
}

