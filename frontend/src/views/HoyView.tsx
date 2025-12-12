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

// Función para sintetizar resumen en formato de hints/bullets
function synthesizeSummaryHints(summary: string): string[] {
  if (!summary || !summary.trim()) {
    return []
  }
  
  // Dividir por párrafos y oraciones
  const paragraphs = summary.split('\n').filter(p => p.trim())
  const hints: string[] = []
  
  for (const paragraph of paragraphs.slice(0, 5)) { // Limitar a primeros 5 párrafos
    // Dividir párrafo en oraciones
    const sentences = paragraph.split(/[.!?]+/).filter(s => s.trim().length > 20)
    
    for (const sentence of sentences.slice(0, 2)) { // Máximo 2 oraciones por párrafo
      const trimmed = sentence.trim()
      if (trimmed.length > 0 && trimmed.length < 150) { // Filtrar oraciones muy largas
        hints.push(trimmed)
        if (hints.length >= 3) break // Máximo 3 hints
      }
    }
    
    if (hints.length >= 3) break
  }
  
  // Si no hay suficientes hints, crear algunos desde el resumen completo
  if (hints.length === 0 && summary.length > 50) {
    // Dividir el resumen en chunks y tomar los primeros 3
    const chunks = summary.split(/[.!?]+/).filter(s => s.trim().length > 30 && s.trim().length < 120)
    return chunks.slice(0, 3).map(c => c.trim())
  }
  
  return hints
}

export default function HoyView({ onAddNews, onManagePortfolio }: HoyViewProps) {
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  
  // Datos principales
  const [situationSummary, setSituationSummary] = useState<string | null>(null)
  const [summaryHints, setSummaryHints] = useState<string[]>([])
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
      // Usar timeout más corto para escenarios (60s) ya que el asistente maneja el timeout largo
      const [summaryData, portfolioData, scenariosData] = await Promise.allSettled([
        newsApi.getSituationSummary(),
        portfolioApi.list(),
        Promise.race([
          scenariosApi.generate({ max_drivers: 2, include_portfolio_mapping: true }),
          new Promise((_, reject) => 
            setTimeout(() => reject(new Error('Timeout escenarios')), 60000)
          )
        ]).catch(() => ({ drivers: [], total_drivers: 0, total_news_analyzed: 0, generated_at: new Date().toISOString(), partial_results: false, missing_fields: [], warnings: ['Timeout al generar escenarios'] }))
      ])
      
      // Procesar resumen de situación
      if (summaryData.status === 'fulfilled' && summaryData.value.has_content) {
        const summary = summaryData.value.summary
        setSituationSummary(summary)
        // Sintetizar en hints/bullets
        const hints = synthesizeSummaryHints(summary)
        setSummaryHints(hints)
        // Extraer "por qué importa" del resumen (primeros párrafos)
        const paragraphs = summary.split('\n').filter(p => p.trim())
        setWhyItMatters(paragraphs.slice(0, 2).join('\n\n'))
      } else if (summaryData.status === 'fulfilled' && !summaryData.value.has_content) {
        // Si no hay contenido pero la respuesta fue exitosa, mantener estado vacío
        setSituationSummary(null)
        setSummaryHints([])
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

  // Callback para recibir datos del asistente proactivo
  const handleAssistantUpdate = (assistantData?: { summary?: string; synthesis?: any }) => {
    // Si el asistente tiene datos, usarlos (incluso en modo degradado)
    if (assistantData?.summary) {
      const hints = synthesizeSummaryHints(assistantData.summary)
      setSummaryHints(hints)
      setSituationSummary(assistantData.summary)
      
      // Si también tiene "whyItMatters", usarlo
      if (assistantData.synthesis?.whyItMatters) {
        setWhyItMatters(assistantData.synthesis.whyItMatters)
      }
      
      // Si tiene top assets, usarlos también
      if (assistantData.synthesis?.topAssets && assistantData.synthesis.topAssets.length > 0) {
        setTopSensitiveAssets(assistantData.synthesis.topAssets)
      }
      
      // Si tiene escenarios, usarlos también
      if (assistantData.synthesis?.scenarios && assistantData.synthesis.scenarios.length > 0) {
        setScenarios(assistantData.synthesis.scenarios)
      }
    }
    // También recargar datos propios en paralelo (pero no bloquear si ya tenemos datos del asistente)
    if (!assistantData?.summary) {
      loadHoyData()
    }
  }

  return (
    <div className="hoy-view">
      {/* Asistente IA Proactivo - se carga automáticamente */}
      <ProactiveAssistant autoLoad={true} onUpdate={handleAssistantUpdate} />

      {/* Bloques secundarios en grid */}
      <div className="hoy-blocks-grid">
        {/* Qué pasó hoy */}
        <section className="hoy-block que-paso-hoy">
          <h2>📰 Qué pasó hoy</h2>
          {summaryHints.length > 0 ? (
            <div className="summary-hints">
              <ul className="hints-list">
                {summaryHints.map((hint, idx) => (
                  <li key={idx} className="hint-item">{hint}</li>
                ))}
              </ul>
            </div>
          ) : situationSummary ? (
            // Fallback: si no hay hints sintetizados, mostrar primeros párrafos
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
