import { useState, useEffect, useMemo } from 'react'
import { newsApi, portfolioApi, scenariosApi, NewsItem, NewsSummary, PortfolioImpact, ScenarioData } from '../services/api'
import SignalCard from '../components/SignalCard'
import './SenalesView.css'

interface SignalData {
  news: NewsItem
  summary?: NewsSummary
  impact?: PortfolioImpact
  affectedAssets: string[]
  confidence: number
  directionality: 'positive' | 'negative' | 'neutral'
  invalidators: string[]
}

export default function SenalesView() {
  const [signals, setSignals] = useState<SignalData[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedAsset, setSelectedAsset] = useState<string>('all')
  const [portfolioItems, setPortfolioItems] = useState<Array<{ symbol?: string; name: string }>>([])

  useEffect(() => {
    loadSignals()
  }, [])

  const loadSignals = async () => {
    try {
      setIsLoading(true)
      setError(null)
      
      // Cargar cartera, noticias y escenarios en paralelo
      const [portfolioData, summariesData, scenariosData] = await Promise.allSettled([
        portfolioApi.list(),
        newsApi.getNewsSummaries(50), // Obtener más noticias para filtrar mejor
        scenariosApi.generate({ max_drivers: 5, include_portfolio_mapping: true })
      ])
      
      const portfolio = portfolioData.status === 'fulfilled' ? portfolioData.value : []
      const summaries = summariesData.status === 'fulfilled' ? summariesData.value : { summaries: [], portfolio_impacts: [] }
      const scenarios = scenariosData.status === 'fulfilled' ? scenariosData.value.drivers || [] : []
      
      setPortfolioItems(portfolio.map(item => ({
        symbol: item.symbol,
        name: item.name
      })))
      
      // Obtener noticias con scoring
      const newsItems = await newsApi.list('score')
      
      // Crear mapa de summaries por news_id
      const summariesMap = new Map<number, NewsSummary>()
      summaries.summaries.forEach(summary => {
        summariesMap.set(summary.news_id, summary)
      })
      
      // Crear mapa de impacts por news_id (si hay)
      const impactsMap = new Map<number, PortfolioImpact>()
      summaries.portfolio_impacts.forEach((impact, idx) => {
        // Asumimos que los impacts están en el mismo orden que summaries
        const summary = summaries.summaries[idx]
        if (summary) {
          impactsMap.set(summary.news_id, impact)
        }
      })
      
      // Crear mapa de invalidadores por news_id desde escenarios
      const invalidatorsMap = new Map<number, string[]>()
      scenarios.forEach((scenario: ScenarioData) => {
        scenario.related_news_ids.forEach(newsId => {
          const invalidators: string[] = []
          // Agregar invalidadores de todos los tipos de escenarios
          // Los escenarios tienen estructura: { base: { invalidators: [{ condition, description }] } }
          const baseScenario = scenario.scenarios.base as any
          const riskScenario = scenario.scenarios.risk as any
          const oppScenario = scenario.scenarios.opportunity as any
          
          if (baseScenario?.invalidators && Array.isArray(baseScenario.invalidators)) {
            baseScenario.invalidators.forEach((inv: any) => {
              if (inv.condition) invalidators.push(inv.condition)
            })
          }
          if (riskScenario?.invalidators && Array.isArray(riskScenario.invalidators)) {
            riskScenario.invalidators.forEach((inv: any) => {
              if (inv.condition) invalidators.push(inv.condition)
            })
          }
          if (oppScenario?.invalidators && Array.isArray(oppScenario.invalidators)) {
            oppScenario.invalidators.forEach((inv: any) => {
              if (inv.condition) invalidators.push(inv.condition)
            })
          }
          
          // Si ya hay invalidadores para este news_id, combinar
          if (invalidators.length > 0) {
            const existing = invalidatorsMap.get(newsId) || []
            invalidatorsMap.set(newsId, [...existing, ...invalidators])
          }
        })
      })
      
      // Crear señales solo para noticias con match en cartera
      const signalsData: SignalData[] = []
      
      for (const news of newsItems) {
        // Filtrar noticias sin match con cartera (score bajo o sin tickers/categorías)
        const hasMatch = news.score_components && (
          (news.score_components.ticker_matches > 0) ||
          (news.score_components.category_matches > 0) ||
          (news.score && news.score > 2.0) // Score mínimo para considerar relevante
        )
        
        if (!hasMatch) continue
        
        const summary = summariesMap.get(news.id)
        const impact = impactsMap.get(news.id)
        
        // Extraer activos afectados
        const affectedAssets: string[] = []
        if (news.score_components?.ticker_matches > 0) {
          // Extraer tickers mencionados del body/title
          portfolio.forEach(item => {
            if (item.symbol && (
              news.body?.toUpperCase().includes(item.symbol.toUpperCase()) ||
              news.title?.toUpperCase().includes(item.symbol.toUpperCase())
            )) {
              affectedAssets.push(item.symbol)
            }
          })
        }
        
        // Determinar direccionalidad basada en sentimiento
        const sentiment = news.score_components?.sentiment_type || 'neutral'
        const directionality: 'positive' | 'negative' | 'neutral' = 
          sentiment === 'positive' ? 'positive' :
          sentiment === 'negative' ? 'negative' : 'neutral'
        
        // Calcular confianza basada en score y componentes
        const confidence = Math.min(1.0, Math.max(0.0, 
          (news.score || 0) / 20.0 + // Normalizar score (0-20) a 0-1
          (news.score_components?.ticker_matches > 0 ? 0.3 : 0) +
          (news.score_components?.category_matches > 0 ? 0.2 : 0)
        ))
        
        // Invalidadores desde escenarios
        const invalidators = invalidatorsMap.get(news.id) || []
        
        signalsData.push({
          news,
          summary,
          impact,
          affectedAssets,
          confidence,
          directionality,
          invalidators
        })
      }
      
      // Ordenar por impacto (score × frescura × direccionalidad)
      signalsData.sort((a, b) => {
        const scoreA = (a.news.score || 0) * a.confidence * (a.directionality !== 'neutral' ? 1.2 : 1.0)
        const scoreB = (b.news.score || 0) * b.confidence * (b.directionality !== 'neutral' ? 1.2 : 1.0)
        return scoreB - scoreA
      })
      
      setSignals(signalsData)
    } catch (err: any) {
      console.error('Error cargando señales:', err)
      setError(err.message || 'Error al cargar señales')
    } finally {
      setIsLoading(false)
    }
  }
  
  // Filtrar señales por activo seleccionado
  const filteredSignals = useMemo(() => {
    if (selectedAsset === 'all') {
      return signals
    }
    return signals.filter(signal => 
      signal.affectedAssets.includes(selectedAsset)
    )
  }, [signals, selectedAsset])

  // Obtener lista única de activos para el filtro
  const availableAssets = useMemo(() => {
    const assets = new Set<string>()
    signals.forEach(signal => {
      signal.affectedAssets.forEach(asset => assets.add(asset))
    })
    return Array.from(assets).sort()
  }, [signals])

  if (isLoading) {
    return (
      <div className="senales-view loading">
        <div className="loading-spinner">⏳ Cargando señales...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="senales-view error">
        <div className="error-message">⚠️ {error}</div>
        <button onClick={loadSignals} className="retry-button">
          Reintentar
        </button>
      </div>
    )
  }

  return (
    <div className="senales-view">
      <header className="senales-header">
        <div>
          <h1>🔔 Señales por Impacto</h1>
          <p className="subtitle">Ordenadas por impacto en tu cartera (exposición × frescura × direccionalidad)</p>
        </div>
        <button onClick={loadSignals} className="refresh-button">
          🔄 Actualizar
        </button>
      </header>

      {/* Filtro por activo */}
      {availableAssets.length > 0 && (
        <div className="asset-filter">
          <label htmlFor="asset-filter-select">Filtrar por activo:</label>
          <select
            id="asset-filter-select"
            value={selectedAsset}
            onChange={(e) => setSelectedAsset(e.target.value)}
            className="filter-select"
          >
            <option value="all">Todos los activos</option>
            {availableAssets.map(asset => (
              <option key={asset} value={asset}>{asset}</option>
            ))}
          </select>
        </div>
      )}

      {filteredSignals.length === 0 ? (
        <div className="empty-state">
          <p>
            {selectedAsset === 'all' 
              ? 'No hay señales relevantes para tu cartera'
              : `No hay señales para ${selectedAsset}`
            }
          </p>
          <p className="hint">
            Las señales se muestran solo cuando hay match con activos en tu cartera
          </p>
        </div>
      ) : (
        <>
          <div className="signals-stats">
            <span>Mostrando {filteredSignals.length} señal{filteredSignals.length !== 1 ? 'es' : ''}</span>
            {selectedAsset !== 'all' && (
              <span className="filter-indicator">Filtrado por: {selectedAsset}</span>
            )}
          </div>
          <div className="signals-list">
            {filteredSignals.map((signal) => (
              <SignalCard
                key={signal.news.id}
                news={signal.news}
                summary={signal.summary}
                impact={signal.impact}
                affectedAssets={signal.affectedAssets}
                confidence={signal.confidence}
                directionality={signal.directionality}
                invalidators={signal.invalidators}
              />
            ))}
          </div>
        </>
      )}
    </div>
  )
}

