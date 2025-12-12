import { useState, useEffect } from 'react'
import { newsApi, portfolioApi, scenariosApi, ScenarioData } from '../services/api'
import ProactiveAssistant from '../components/ProactiveAssistant'
import './HoyView.css'

interface ScenarioData {
  driver: string
  driver_description: string
  scenarios: {
    base?: { title: string; description: string; confidence: number }
    risk?: { title: string; description: string; confidence: number }
    opportunity?: { title: string; description: string; confidence: number }
  }
  portfolio_mappings: Array<{
    asset_type: string
    identifier: string
    name?: string
    sensitivity: number
    confidence: number
  }>
}

interface HoyViewProps {
  onAddNews?: () => void
  onManagePortfolio?: () => void
}

export default function HoyView({ onAddNews, onManagePortfolio }: HoyViewProps) {
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  
  // Datos principales
  const [situationSummary, setSituationSummary] = useState<string | null>(null)
  const [whyItMatters, setWhyItMatters] = useState<string | null>(null)
  const [topSensitiveAssets, setTopSensitiveAssets] = useState<Array<{
    identifier: string
    name?: string
    sensitivity: number
    confidence: number
  }>>([])
  const [scenarios, setScenarios] = useState<ScenarioData[]>([])
  
  useEffect(() => {
    loadHoyData()
  }, [])

  const loadHoyData = async () => {
    try {
      setIsLoading(true)
      setError(null)
      
      // Cargar datos en paralelo para respuesta rápida
      const [summaryData, portfolioData, scenariosData] = await Promise.allSettled([
        newsApi.getSituationSummary(),
        portfolioApi.list(),
        scenariosApi.generate({ max_drivers: 3, include_portfolio_mapping: true })
      ])
      
      // Procesar resumen de situación
      if (summaryData.status === 'fulfilled' && summaryData.value.has_content) {
        setSituationSummary(summaryData.value.summary)
        // Extraer "por qué importa" del resumen (primeros párrafos)
        const paragraphs = summaryData.value.summary.split('\n').filter(p => p.trim())
        setWhyItMatters(paragraphs.slice(0, 2).join('\n\n'))
      }
      
      // Procesar escenarios y extraer top activos sensibles
      if (scenariosData.status === 'fulfilled') {
        setScenarios(scenariosData.value.drivers || [])
        
        // Extraer top 3 activos más sensibles
        const allMappings = (scenariosData.value.drivers || []).flatMap(s => s.portfolio_mappings)
        const uniqueAssets = new Map<string, {
          identifier: string
          name?: string
          sensitivity: number
          confidence: number
        }>()
        
        allMappings.forEach(m => {
          const key = m.identifier
          if (!uniqueAssets.has(key) || uniqueAssets.get(key)!.confidence < m.confidence) {
            uniqueAssets.set(key, {
              identifier: m.identifier,
              name: m.name,
              sensitivity: m.sensitivity,
              confidence: m.confidence
            })
          }
        })
        
        const sortedAssets = Array.from(uniqueAssets.values())
          .sort((a, b) => Math.abs(b.sensitivity) - Math.abs(a.sensitivity))
          .slice(0, 3)
        
        setTopSensitiveAssets(sortedAssets)
      }
      
    } catch (err: any) {
      console.error('Error cargando datos de HOY:', err)
      setError(err.message || 'Error al cargar datos')
    } finally {
      setIsLoading(false)
    }
  }

  if (isLoading) {
    return (
      <div className="hoy-view loading">
        <div className="loading-spinner">⏳ Cargando...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="hoy-view error">
        <div className="error-message">⚠️ {error}</div>
        <button onClick={loadHoyData} className="retry-button">
          Reintentar
        </button>
      </div>
    )
  }

  return (
    <div className="hoy-view">
      {/* Asistente IA Proactivo - se carga automáticamente */}
      <ProactiveAssistant autoLoad={true} onUpdate={() => loadHoyData()} />

      {/* Bloques secundarios en grid */}
      <div className="hoy-blocks-grid">
        {/* Qué pasó hoy */}
        <section className="hoy-block que-paso-hoy">
          <h2>📰 Qué pasó hoy</h2>
          {situationSummary ? (
            <div className="summary-text">
              {situationSummary.split('\n').slice(0, 3).map((p, idx) => (
                p.trim() && <p key={idx}>{p}</p>
              ))}
            </div>
          ) : (
            <p className="empty-state">No hay noticias recientes</p>
          )}
        </section>

        {/* Por qué importa */}
        <section className="hoy-block por-que-importa">
          <h2>💡 Por qué importa</h2>
          {whyItMatters ? (
            <div className="why-text">
              {whyItMatters.split('\n').map((p, idx) => (
                p.trim() && <p key={idx}>{p}</p>
              ))}
            </div>
          ) : (
            <p className="empty-state">Analizando relevancia...</p>
          )}
        </section>

        {/* Top 3 activos sensibles */}
        <section className="hoy-block top-activos">
          <h2>🎯 Top 3 activos sensibles</h2>
          {topSensitiveAssets.length > 0 ? (
            <div className="assets-list">
              {topSensitiveAssets.map((asset, idx) => (
                <div key={asset.identifier} className="asset-item">
                  <span className="asset-rank">#{idx + 1}</span>
                  <div className="asset-info">
                    <strong>{asset.name || asset.identifier}</strong>
                    <span className={`sensitivity ${asset.sensitivity > 0 ? 'positive' : 'negative'}`}>
                      {asset.sensitivity > 0 ? '📈' : '📉'} {Math.abs(asset.sensitivity * 100).toFixed(0)}%
                    </span>
                  </div>
                  <span className="confidence">Confianza: {(asset.confidence * 100).toFixed(0)}%</span>
                </div>
              ))}
            </div>
          ) : (
            <p className="empty-state">No hay activos sensibles identificados</p>
          )}
        </section>

        {/* Escenarios */}
        <section className="hoy-block escenarios">
          <h2>🔮 Escenarios</h2>
          {scenarios.length > 0 ? (
            <div className="scenarios-list">
              {scenarios.slice(0, 1).map((scenario, idx) => (
                <div key={idx} className="scenario-driver">
                  <h3>{scenario.driver}</h3>
                  <p className="driver-description">{scenario.driver_description}</p>
                  
                  <div className="scenario-types">
                    {scenario.scenarios.base && (
                      <div className="scenario-card base">
                        <h4>Base</h4>
                        <p>{scenario.scenarios.base.title}</p>
                        <span className="confidence">{(scenario.scenarios.base.confidence * 100).toFixed(0)}%</span>
                      </div>
                    )}
                    {scenario.scenarios.risk && (
                      <div className="scenario-card risk">
                        <h4>Riesgo</h4>
                        <p>{scenario.scenarios.risk.title}</p>
                        <span className="confidence">{(scenario.scenarios.risk.confidence * 100).toFixed(0)}%</span>
                      </div>
                    )}
                    {scenario.scenarios.opportunity && (
                      <div className="scenario-card opportunity">
                        <h4>Oportunidad</h4>
                        <p>{scenario.scenarios.opportunity.title}</p>
                        <span className="confidence">{(scenario.scenarios.opportunity.confidence * 100).toFixed(0)}%</span>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="empty-state">Generando escenarios...</p>
          )}
        </section>
      </div>

      {/* Acciones rápidas */}
      <section className="hoy-block acciones-rapidas">
        <h2>⚡ Acciones rápidas</h2>
        <div className="actions-grid">
          <button onClick={onAddNews} className="action-button">
            ➕ Agregar noticia
          </button>
          <button onClick={onManagePortfolio} className="action-button">
            💼 Gestionar cartera
          </button>
          <button onClick={loadHoyData} className="action-button">
            🔄 Actualizar vista
          </button>
        </div>
      </section>
    </div>
  )
}
