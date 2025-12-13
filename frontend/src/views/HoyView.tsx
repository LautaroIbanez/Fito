import { useState, useEffect, useRef, useCallback } from 'react'
import { newsApi, portfolioApi, scenariosApi, ScenarioData } from '../services/api'
import ProactiveAssistant from '../components/ProactiveAssistant'
import { diagnostics } from '../utils/diagnostics'
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
  // Inicializar isLoading en false ya que no cargamos datos automáticamente
  // Solo se activa cuando el usuario solicita datos de respaldo manualmente
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  
  // Diagnóstico: Log del estado inicial del componente
  useEffect(() => {
    diagnostics.logComponentState('HoyView', {
      isLoading,
      hasSynthesis,
      isGenerating,
      scenariosCount: scenarios.length,
      hasSummary: !!situationSummary,
      hasHints: summaryHints.length > 0
    })
    
    // Imprimir resumen de llamadas HTTP cada 10 segundos si hay llamadas pendientes
    const interval = setInterval(() => {
      const pending = diagnostics.getPendingCalls()
      if (pending.length > 0) {
        console.warn(
          `%c[DIAGNOSTICS] ⚠️ Hay ${pending.length} llamada(s) HTTP pendiente(s) después de ${Math.floor((Date.now() - performance.timeOrigin) / 1000)}s desde la carga`,
          'color: #f59e0b; font-weight: bold; font-size: 14px'
        )
        diagnostics.printSummary()
      }
    }, 10000)
    
    return () => clearInterval(interval)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])
  
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
  
  // NO cargar datos automáticamente - el asistente proactivo los proporcionará
  // Solo cargar datos de respaldo manualmente si el usuario lo solicita
  const hasLoadedRef = useRef(false)
  const assistantDataReceivedRef = useRef(false)
  const [showFallbackOption, setShowFallbackOption] = useState(false)

  // Callback para recibir datos del asistente proactivo
  // TODOS LOS HOOKS DEBEN ESTAR ANTES DE LOS RETURNS CONDICIONALES
  const isUpdatingFromAssistantRef = useRef(false)
  const generateSynthesisRef = useRef<(() => void) | null>(null)
  const [isGenerating, setIsGenerating] = useState(false)
  const [hasSynthesis, setHasSynthesis] = useState(false)
  
  const handleAssistantUpdate = useCallback((assistantData?: { summary?: string; synthesis?: any }) => {
    // Prevenir loops infinitos
    if (isUpdatingFromAssistantRef.current) {
      console.log('[HoyView] Ignorando actualización del asistente - ya procesando')
      return
    }
    
    isUpdatingFromAssistantRef.current = true
    
    assistantDataReceivedRef.current = true // Marcar que recibimos datos del asistente
    setShowFallbackOption(false) // Ocultar opción de fallback si tenemos datos del asistente
    
    console.log('[HoyView] Recibiendo datos del asistente:', {
      hasSummary: !!assistantData?.summary,
      hasSynthesis: !!assistantData?.synthesis,
      hasScenarios: !!(assistantData?.synthesis?.scenarios?.length),
      scenariosCount: assistantData?.synthesis?.scenarios?.length || 0,
      scenarios: assistantData?.synthesis?.scenarios?.map(s => ({ driver: s.driver, hasScenarios: !!s.scenarios })) || []
    })
    
    // Si el asistente tiene datos, usarlos (incluso en modo degradado)
    // Esto evita que el fallback haga llamadas duplicadas
    if (assistantData?.summary || assistantData?.synthesis) {
      // Priorizar meta_summary si está disponible (procesamiento por lotes), sino usar summary (compatibilidad)
      // El summary ya viene con meta_summary aplicado desde ProactiveAssistant
      const summaryToUse = assistantData.summary || ''
      if (summaryToUse) {
        const hints = synthesizeSummaryHints(summaryToUse)
        setSummaryHints(hints)
        setSituationSummary(summaryToUse)
      }
      
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
        console.log('[HoyView] Actualizando escenarios:', assistantData.synthesis.scenarios.length, 'escenarios recibidos')
        setScenarios(assistantData.synthesis.scenarios)
      } else {
        console.log('[HoyView] No hay escenarios en los datos del asistente:', {
          hasSynthesis: !!assistantData.synthesis,
          scenarios: assistantData.synthesis?.scenarios,
          scenariosLength: assistantData.synthesis?.scenarios?.length
        })
      }
      
      // Marcar que ya no estamos cargando y que tenemos síntesis
      setIsLoading(false)
      setHasSynthesis(true)
      setIsGenerating(false)
      setShowFallbackOption(false) // Ocultar opción de fallback
      
      // Prevenir que loadHoyData se ejecute si ya tenemos datos del asistente
      hasLoadedRef.current = false // Permitir recarga manual si el usuario lo desea
    }
    
    // Resetear el flag después de un breve delay
    setTimeout(() => {
      isUpdatingFromAssistantRef.current = false
    }, 3000) // Aumentar a 3 segundos para evitar loops
  }, []) // Array vacío porque solo usamos refs y setters que son estables

  const loadHoyData = async (force: boolean = false) => {
    // Guardas: no cargar si el asistente ya tiene datos o está generando (a menos que sea forzado)
    if (!force) {
      if (assistantDataReceivedRef.current) {
        console.log('[HoyView] Ignorando loadHoyData - asistente ya proporcionó datos')
        return
      }
      if (isGenerating) {
        console.log('[HoyView] Ignorando loadHoyData - asistente está generando síntesis')
        return
      }
      if (hasSynthesis && (situationSummary || scenarios.length > 0)) {
        console.log('[HoyView] Ignorando loadHoyData - ya hay datos de síntesis disponibles')
        return
      }
    }
    
    try {
      console.log('[HoyView] Iniciando loadHoyData', { force, timestamp: new Date().toISOString() })
      diagnostics.logComponentState('HoyView.loadHoyData', { 
        force, 
        isGenerating, 
        hasSynthesis,
        assistantDataReceived: assistantDataReceivedRef.current
      })
      
      setIsLoading(true)
      setError(null)
      hasLoadedRef.current = true // Marcar que ya cargamos datos de respaldo
      
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

  // Ahora sí podemos hacer returns condicionales después de todos los hooks
  if (isLoading) {
    // Diagnóstico: Identificar qué está bloqueando el render
    const pendingCalls = diagnostics.getPendingCalls()
    if (pendingCalls.length > 0) {
      diagnostics.logRenderBlock('HoyView', 'isLoading=true', {
        pendingCalls: pendingCalls.map(c => ({ url: c.url, elapsed: `${c.elapsed.toFixed(0)}ms` })),
        isLoading,
        isGenerating,
        hasSynthesis
      })
    }
    
    return (
      <div className="hoy-view loading">
        <div className="loading-spinner">⏳ Cargando...</div>
        {pendingCalls.length > 0 && (
          <div style={{ marginTop: '10px', fontSize: '12px', color: '#666' }}>
            Esperando {pendingCalls.length} llamada(s) HTTP...
          </div>
        )}
      </div>
    )
  }

  if (error) {
    return (
      <div className="hoy-view error">
        <div className="error-message">⚠️ {error}</div>
        <button onClick={() => loadHoyData(true)} className="retry-button">
          Reintentar
        </button>
      </div>
    )
  }

  const handleGenerateSynthesis = () => {
    if (!isGenerating) {
      setIsGenerating(true)
      // Usar setTimeout para asegurar que el componente ProactiveAssistant se monte primero
      setTimeout(() => {
        if (generateSynthesisRef.current) {
          generateSynthesisRef.current()
        } else {
          console.error('[HoyView] generateSynthesisRef.current no está disponible')
          setIsGenerating(false)
        }
      }, 100) // Pequeño delay para asegurar que el componente se monte
    }
  }

  return (
    <div className="hoy-view">
      {/* Botón para generar síntesis manualmente */}
      {!hasSynthesis && !isGenerating && (
        <div className="generate-synthesis-prompt">
          <div className="prompt-content">
            <h2>🤖 Asistente IA Proactivo</h2>
            <p>Genera una síntesis completa de la situación actual del mercado, escenarios y activos expuestos.</p>
            <div className="prompt-actions">
              <button 
                onClick={handleGenerateSynthesis} 
                className="generate-button"
                disabled={isGenerating}
              >
                🚀 Generar Síntesis HOY
              </button>
              {!assistantDataReceivedRef.current && !hasLoadedRef.current && (
                <button 
                  onClick={() => {
                    setShowFallbackOption(true)
                    loadHoyData(false) // No forzar, pero permitir si no hay datos del asistente
                  }}
                  className="fallback-button"
                  disabled={isLoading || isGenerating}
                >
                  📊 Cargar Datos de Respaldo
                </button>
              )}
            </div>
            {showFallbackOption && !assistantDataReceivedRef.current && (
              <p className="fallback-hint">
                ℹ️ Cargando datos directamente sin síntesis del asistente. 
                Puedes generar la síntesis completa más tarde.
              </p>
            )}
          </div>
        </div>
      )}

      {/* Indicador de generación en progreso */}
      {isGenerating && (
        <div className="generating-indicator">
          <div className="spinner">⏳</div>
          <p>Generando síntesis... Esto puede tardar hasta 3 minutos.</p>
          {!assistantDataReceivedRef.current && (
            <button 
              onClick={() => {
                setShowFallbackOption(true)
                loadHoyData(false) // No forzar, pero permitir si no hay datos del asistente
              }}
              className="fallback-button-small"
              disabled={isLoading}
            >
              📊 Cargar datos de respaldo mientras tanto
            </button>
          )}
        </div>
      )}

      {/* Asistente IA Proactivo - siempre montado pero solo visible cuando hay síntesis o se está generando */}
      {/* Montarlo siempre asegura que el ref esté disponible cuando se necesite */}
      <div style={{ display: (hasSynthesis || isGenerating) ? 'block' : 'none' }}>
        <ProactiveAssistant 
          autoLoad={false} 
          onUpdate={(data) => {
            // Siempre resetear isGenerating cuando se complete (éxito o error)
            setIsGenerating(false)
            if (data?.summary || data?.synthesis) {
              setHasSynthesis(true)
              handleAssistantUpdate(data)
            } else {
              // Si no hay datos pero se llamó onUpdate, fue un error - mantener el componente visible para mostrar el error
              setHasSynthesis(true)
            }
          }}
          onGenerateRef={generateSynthesisRef}
        />
      </div>

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
          <button onClick={() => loadHoyData(true)} className="action-button">
            🔄 Actualizar vista
          </button>
        </div>
      </section>
    </div>
  )
}
