import { useState, useEffect, useRef } from 'react'
import { newsApi, scenariosApi, ScenarioData } from '../services/api'
import './ProactiveAssistant.css'

interface ProactiveAssistantProps {
  onUpdate?: (data?: { summary?: string; synthesis?: SynthesisData }) => void
  autoLoad?: boolean
}

interface SynthesisData {
  summary: string
  whyItMatters: string
  topAssets: Array<{
    identifier: string
    name?: string
    sensitivity: number
    confidence: number
  }>
  scenarios: ScenarioData[]
  generatedAt: string
  hasError?: boolean
  errorMessage?: string
}

export default function ProactiveAssistant({ onUpdate, autoLoad = true }: ProactiveAssistantProps) {
  const [synthesis, setSynthesis] = useState<SynthesisData | null>(null)
  const [isLoading, setIsLoading] = useState(autoLoad)
  const [error, setError] = useState<string | null>(null)
  const [isDegraded, setIsDegraded] = useState(false)
  const [isRecalculating, setIsRecalculating] = useState(false)
  const [progressMessage, setProgressMessage] = useState<string | null>(null)
  const [elapsedTime, setElapsedTime] = useState(0)
  const lastValidSynthesisRef = useRef<SynthesisData | null>(null)
  const progressIntervalRef = useRef<NodeJS.Timeout | null>(null)
  const startTimeRef = useRef<number | null>(null)
  const hasGeneratedRef = useRef(false) // Flag para prevenir múltiples generaciones
  const onUpdateTimeoutRef = useRef<NodeJS.Timeout | null>(null) // Para debounce de onUpdate
  const onUpdateCalledRef = useRef(false) // Flag para asegurar que onUpdate solo se llama una vez

  // Solo generar síntesis una vez al montar el componente
  useEffect(() => {
    if (autoLoad && !hasGeneratedRef.current) {
      hasGeneratedRef.current = true
      generateSynthesis()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []) // Array vacío para ejecutar solo una vez al montar

  // Limpiar intervalos de progreso
  const clearProgressTracking = () => {
    if (progressIntervalRef.current) {
      clearInterval(progressIntervalRef.current)
      progressIntervalRef.current = null
    }
    startTimeRef.current = null
    setElapsedTime(0)
    setProgressMessage(null)
  }

  // Iniciar seguimiento de progreso
  const startProgressTracking = () => {
    startTimeRef.current = Date.now()
    setElapsedTime(0)
    
    progressIntervalRef.current = setInterval(() => {
      if (startTimeRef.current) {
        const elapsed = Math.floor((Date.now() - startTimeRef.current) / 1000)
        setElapsedTime(elapsed)
        
        // Actualizar mensaje de progreso según el tiempo transcurrido
        if (elapsed > 60 && elapsed <= 90) {
          setProgressMessage('La generación está tomando más tiempo de lo esperado. Esto es normal cuando se estandarizan noticias...')
        } else if (elapsed > 90 && elapsed <= 150) {
          setProgressMessage('Procesando escenarios complejos. Esto puede tardar hasta 3 minutos...')
        } else if (elapsed > 150) {
          setProgressMessage('Casi terminando. El backend tiene hasta 3 minutos para completar...')
        }
      }
    }, 1000)
  }

  const generateSynthesis = async (isManual = false) => {
    try {
      if (isManual) {
        setIsRecalculating(true)
      } else {
        setIsLoading(true)
      }
      setError(null)
      setIsDegraded(false)
      clearProgressTracking()
      startProgressTracking()

      // Timeouts individuales alineados con el backend
      // Resumen: 60s (suele ser rápido)
      // Escenarios: 180s (coincide con SCENARIO_GENERATION_TIMEOUT del backend)
      const SUMMARY_TIMEOUT = 60000
      const SCENARIOS_TIMEOUT = 180000

      // Wrapper con timeout individual para resumen
      const safeGetSummary = async (): Promise<any> => {
        try {
          const timeoutPromise = new Promise<never>((_, reject) =>
            setTimeout(() => reject(new Error('Timeout: Resumen excedió 60 segundos')), SUMMARY_TIMEOUT)
          )
          const result = await Promise.race([
            newsApi.getSituationSummary(),
            timeoutPromise
          ])
          // Si el resumen llega rápido, actualizar progreso
          if (startTimeRef.current) {
            const elapsed = Math.floor((Date.now() - startTimeRef.current) / 1000)
            if (elapsed < 30) {
              setProgressMessage('Resumen obtenido. Generando escenarios...')
            }
          }
          return result
        } catch (err: any) {
          console.warn('Error obteniendo resumen de situación:', err)
          // Manejar errores 504 específicamente
          if (err.response?.status === 504) {
            throw new Error('Resumen: Timeout del servidor (504). El servidor tardó más de 60 segundos.')
          }
          const errorMsg = err.response?.data?.detail || err.message || 'Error desconocido'
          throw new Error(`Resumen: ${errorMsg}`)
        }
      }

      // Wrapper con timeout individual para escenarios (180s para coincidir con backend)
      const safeGenerateScenarios = async (): Promise<any> => {
        try {
          const timeoutPromise = new Promise<never>((_, reject) =>
            setTimeout(() => reject(new Error('Timeout: Escenarios excedieron 180 segundos')), SCENARIOS_TIMEOUT)
          )
          // Reducir max_drivers a 2 para acelerar la generación
          const result = await Promise.race([
            scenariosApi.generate({ max_drivers: 2, include_portfolio_mapping: true }),
            timeoutPromise
          ])
          return result
        } catch (err: any) {
          console.warn('Error generando escenarios:', err)
          // Manejar errores 504 específicamente
          if (err.response?.status === 504) {
            throw new Error('Escenarios: Timeout del servidor (504). El servidor tardó más de 180 segundos.')
          }
          const errorMsg = err.response?.data?.detail || err.message || 'Error desconocido'
          throw new Error(`Escenarios: ${errorMsg}`)
        }
      }

      // Ejecutar en paralelo con Promise.allSettled para manejar resultados parciales
      // NO usar Promise.race con timeout global - permitir que cada llamada tenga su propio timeout
      const result = await Promise.allSettled([
        safeGetSummary(),
        safeGenerateScenarios()
      ])
      
      clearProgressTracking()

      // Procesar resultados (ya son PromiseSettledResult)
      const summaryData = result[0]
      const scenariosData = result[1]

      let summary = ''
      let whyItMatters = ''
      let scenarios: ScenarioData[] = []
      let topAssets: Array<{
        identifier: string
        name?: string
        sensitivity: number
        confidence: number
      }> = []
      let hasPartialData = false

      // Procesar resumen de situación
      if (summaryData.status === 'fulfilled' && summaryData.value.has_content) {
        summary = summaryData.value.summary || ''
        const paragraphs = summary.split('\n').filter(p => p.trim())
        whyItMatters = paragraphs.slice(0, 2).join('\n\n')
      } else {
        console.warn('Resumen de situación no disponible:', summaryData.status === 'rejected' ? summaryData.reason : 'sin contenido')
        hasPartialData = true
      }

      // Procesar escenarios
      if (scenariosData.status === 'fulfilled' && scenariosData.value.drivers) {
        scenarios = scenariosData.value.drivers || []

        // Extraer top 3 activos más sensibles
        const allMappings = scenarios.flatMap(s => s.portfolio_mappings || [])
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

        topAssets = Array.from(uniqueAssets.values())
          .sort((a, b) => Math.abs(b.sensitivity) - Math.abs(a.sensitivity))
          .slice(0, 3)
      } else {
        console.warn('Escenarios no disponibles:', scenariosData.status === 'rejected' ? scenariosData.reason : 'sin drivers')
        hasPartialData = true
      }

      // Si ambos fallaron completamente, lanzar error con detalles
      if (!summary && scenarios.length === 0) {
        const errorDetails = []
        if (summaryData.status === 'rejected') {
          const reason = summaryData.reason
          const errorMsg = reason?.response?.data?.detail || reason?.message || 'Error desconocido'
          errorDetails.push(`Resumen: ${errorMsg}`)
        } else if (summaryData.status === 'fulfilled' && !summaryData.value.has_content) {
          errorDetails.push('Resumen: Sin contenido disponible')
        }
        
        if (scenariosData.status === 'rejected') {
          const reason = scenariosData.reason
          const errorMsg = reason?.response?.data?.detail || reason?.message || 'Error desconocido'
          errorDetails.push(`Escenarios: ${errorMsg}`)
        } else if (scenariosData.status === 'fulfilled' && (!scenariosData.value.drivers || scenariosData.value.drivers.length === 0)) {
          const warnings = scenariosData.value.warnings || []
          const warningMsg = warnings.length > 0 ? warnings.join('; ') : 'No se identificaron drivers temáticos'
          errorDetails.push(`Escenarios: ${warningMsg}`)
        }
        
        throw new Error(`No se pudo generar síntesis. ${errorDetails.join('; ')}`)
      }

      // Si solo uno falló, activar modo degradado pero continuar
      if (hasPartialData) {
        setIsDegraded(true)
        if (!summary && scenarios.length === 0) {
          setError('Datos parciales disponibles')
        } else if (!summary) {
          setError('Resumen no disponible. Mostrando escenarios.')
        } else if (scenarios.length === 0) {
          setError('Escenarios no disponibles. Mostrando resumen parcial.')
        }
      }

      // Crear síntesis (incluso si es parcial)
      const newSynthesis: SynthesisData = {
        summary,
        whyItMatters,
        topAssets,
        scenarios,
        generatedAt: new Date().toISOString()
      }

      // Actualizar síntesis si tenemos al menos algo (resumen o escenarios)
      // Esto permite mostrar resultados parciales en lugar de fallar completamente
      if (summary || scenarios.length > 0) {
        setSynthesis(newSynthesis)
        lastValidSynthesisRef.current = newSynthesis
        
        // Pasar datos al callback solo UNA VEZ cuando tenemos datos válidos
        // Usar debounce más largo y verificar que realmente hay datos nuevos
        if (onUpdate && (summary || scenarios.length > 0) && !onUpdateCalledRef.current) {
          // Limpiar timeout anterior si existe
          if (onUpdateTimeoutRef.current) {
            clearTimeout(onUpdateTimeoutRef.current)
          }
          
          // Usar setTimeout con delay más largo para evitar loops infinitos
          onUpdateTimeoutRef.current = setTimeout(() => {
            if (!onUpdateCalledRef.current) {
              console.log('[ProactiveAssistant] Llamando onUpdate con datos (primera vez):', {
                hasSummary: !!summary,
                scenariosCount: scenarios.length
              })
              onUpdateCalledRef.current = true // Marcar que ya llamamos a onUpdate
              onUpdate({ summary, synthesis: newSynthesis })
            } else {
              console.log('[ProactiveAssistant] Ignorando llamada a onUpdate - ya se llamó anteriormente')
            }
            onUpdateTimeoutRef.current = null
          }, 1000) // Aumentar delay a 1 segundo para evitar loops
        } else if (onUpdateCalledRef.current) {
          console.log('[ProactiveAssistant] No llamando onUpdate - ya se llamó anteriormente')
        }
      } else {
        // Solo lanzar error si realmente no hay nada
        throw new Error('No se pudo generar síntesis: datos insuficientes')
      }

    } catch (err: any) {
      console.error('Error generando síntesis:', err)
      clearProgressTracking()
      const errorMsg = err.message || 'Error al generar síntesis'
      setError(errorMsg)
      setIsDegraded(true)

      // Si hay último resultado válido, mantenerlo pero NO notificar (evitar loops)
      if (lastValidSynthesisRef.current) {
        const degradedSynthesis = {
          ...lastValidSynthesisRef.current,
          hasError: true,
          errorMessage: errorMsg
        }
        setSynthesis(degradedSynthesis)
        // NO llamar onUpdate en modo degradado para evitar loops infinitos
        // Los datos ya están disponibles en el componente
        console.log('[ProactiveAssistant] Modo degradado - no llamando onUpdate para evitar loops')
      }
    } finally {
      setIsLoading(false)
      setIsRecalculating(false)
      clearProgressTracking()
    }
  }

  // Limpiar intervalos y timeouts al desmontar
  useEffect(() => {
    return () => {
      clearProgressTracking()
      if (onUpdateTimeoutRef.current) {
        clearTimeout(onUpdateTimeoutRef.current)
        onUpdateTimeoutRef.current = null
      }
    }
  }, [])

  const handleManualRecalculate = () => {
    generateSynthesis(true)
  }

  // Mostrar último resultado válido si está disponible, incluso con errores
  const displaySynthesis = synthesis || lastValidSynthesisRef.current

  return (
    <div className={`proactive-assistant ${isDegraded ? 'degraded' : ''} ${error ? 'has-error' : ''}`}>
      <div className="assistant-header">
        <h2>🤖 Asistente IA Proactivo</h2>
        <div className="assistant-actions">
          {displaySynthesis && (
            <button
              onClick={handleManualRecalculate}
              disabled={isRecalculating || isLoading}
              className="recalculate-button"
              title="Recalcular síntesis"
            >
              {isRecalculating ? '⏳ Recalculando...' : '🔄 Recalcular'}
            </button>
          )}
        </div>
      </div>

      {/* Spinner mientras carga inicialmente */}
      {isLoading && !displaySynthesis && (
        <div className="assistant-loading">
          <div className="spinner">⏳</div>
          <p>Generando síntesis HOY...</p>
          <p className="loading-hint">Analizando noticias, escenarios y activos expuestos</p>
          {elapsedTime > 0 && (
            <div className="progress-info">
              <p className="elapsed-time">Tiempo transcurrido: {elapsedTime}s</p>
              {progressMessage && (
                <p className="progress-message">{progressMessage}</p>
              )}
              {elapsedTime > 60 && (
                <div className="progress-bar-container">
                  <div 
                    className="progress-bar" 
                    style={{ width: `${Math.min((elapsedTime / 180) * 100, 100)}%` }}
                  />
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Mensaje de error si falla y no hay datos previos */}
      {error && !displaySynthesis && (
        <div className="assistant-error">
          <div className="error-icon">⚠️</div>
          <div className="error-content">
            <h3>Error al generar síntesis</h3>
            <p>{error}</p>
            <button onClick={() => generateSynthesis(true)} className="retry-button">
              Reintentar
            </button>
          </div>
        </div>
      )}

      {/* Advertencia de modo degradado */}
      {isDegraded && displaySynthesis && (
        <div className="degraded-warning">
          <span>⚠️ Modo degradado:</span> {error || 'Algunos datos no están disponibles'}
          {displaySynthesis.hasError && (
            <span className="last-valid-indicator"> (Mostrando último resultado válido)</span>
          )}
        </div>
      )}

      {/* Síntesis generada */}
      {displaySynthesis && !isLoading && (
        <div className="assistant-content">
          {/* Resumen ejecutivo */}
          <section className="synthesis-section summary">
            <h3>📊 Resumen Ejecutivo</h3>
            {displaySynthesis.summary ? (
              <div className="summary-content">
                {displaySynthesis.summary.split('\n').slice(0, 4).map((p, idx) => (
                  p.trim() && <p key={idx}>{p}</p>
                ))}
              </div>
            ) : (
              <p className="empty-state">Resumen no disponible</p>
            )}
          </section>

          {/* Por qué importa */}
          {displaySynthesis.whyItMatters && (
            <section className="synthesis-section why-matters">
              <h3>💡 Por qué importa</h3>
              <div className="why-content">
                {displaySynthesis.whyItMatters.split('\n').map((p, idx) => (
                  p.trim() && <p key={idx}>{p}</p>
                ))}
              </div>
            </section>
          )}

          {/* Activos expuestos */}
          {displaySynthesis.topAssets.length > 0 && (
            <section className="synthesis-section exposed-assets">
              <h3>🎯 Activos Expuestos</h3>
              <div className="assets-grid">
                {displaySynthesis.topAssets.map((asset, idx) => (
                  <div key={asset.identifier} className="exposed-asset-card">
                    <div className="asset-rank">#{idx + 1}</div>
                    <div className="asset-details">
                      <strong>{asset.name || asset.identifier}</strong>
                      <div className="asset-metrics">
                        <span className={`sensitivity ${asset.sensitivity > 0 ? 'positive' : 'negative'}`}>
                          {asset.sensitivity > 0 ? '📈' : '📉'} {Math.abs(asset.sensitivity * 100).toFixed(0)}%
                        </span>
                        <span className="confidence">Confianza: {(asset.confidence * 100).toFixed(0)}%</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </section>
          )}

          {/* Escenarios conectados */}
          {displaySynthesis.scenarios.length > 0 && (
            <section className="synthesis-section scenarios">
              <h3>🔮 Escenarios Conectados</h3>
              <div className="scenarios-grid">
                {displaySynthesis.scenarios.slice(0, 2).map((scenario, idx) => (
                  <div key={idx} className="scenario-card">
                    <h4>{scenario.driver}</h4>
                    <p className="scenario-description">{scenario.driver_description}</p>
                    <div className="scenario-types-mini">
                      {scenario.scenarios.base && (
                        <span className="scenario-badge base">Base: {scenario.scenarios.base.title}</span>
                      )}
                      {scenario.scenarios.risk && (
                        <span className="scenario-badge risk">Riesgo: {scenario.scenarios.risk.title}</span>
                      )}
                      {scenario.scenarios.opportunity && (
                        <span className="scenario-badge opportunity">Oportunidad: {scenario.scenarios.opportunity.title}</span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </section>
          )}

          {/* Timestamp */}
          <div className="synthesis-footer">
            <span className="generated-at">
              Generado: {new Date(displaySynthesis.generatedAt).toLocaleString()}
            </span>
            {isRecalculating && (
              <span className="recalculating-indicator">⏳ Recalculando...</span>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
