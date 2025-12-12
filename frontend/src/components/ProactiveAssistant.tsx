import { useState, useEffect, useRef } from 'react'
import { newsApi, scenariosApi, ScenarioData } from '../services/api'
import './ProactiveAssistant.css'

interface ProactiveAssistantProps {
  onUpdate?: () => void
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
  const lastValidSynthesisRef = useRef<SynthesisData | null>(null)

  useEffect(() => {
    if (autoLoad) {
      generateSynthesis()
    }
  }, [autoLoad])

  const generateSynthesis = async (isManual = false) => {
    try {
      if (isManual) {
        setIsRecalculating(true)
      } else {
        setIsLoading(true)
      }
      setError(null)
      setIsDegraded(false)

      // Cargar datos en paralelo con timeout
      const timeoutPromise = new Promise((_, reject) =>
        setTimeout(() => reject(new Error('Timeout: La generación excedió 30 segundos')), 30000)
      )

      const dataPromise = Promise.allSettled([
        newsApi.getSituationSummary(),
        scenariosApi.generate({ max_drivers: 3, include_portfolio_mapping: true })
      ])

      const result = await Promise.race([dataPromise, timeoutPromise]) as PromiseSettledResult<any>[]

      // Procesar resultados
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

      // Procesar resumen de situación
      if (summaryData.status === 'fulfilled' && summaryData.value.has_content) {
        summary = summaryData.value.summary
        const paragraphs = summary.split('\n').filter(p => p.trim())
        whyItMatters = paragraphs.slice(0, 2).join('\n\n')
      } else if (summaryData.status === 'rejected') {
        throw new Error('Error al obtener resumen de situación')
      }

      // Procesar escenarios
      if (scenariosData.status === 'fulfilled') {
        scenarios = scenariosData.value.drivers || []

        // Extraer top 3 activos más sensibles
        const allMappings = scenarios.flatMap(s => s.portfolio_mappings)
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
      } else if (scenariosData.status === 'rejected') {
        // Si fallan escenarios pero tenemos resumen, continuar en modo degradado
        setIsDegraded(true)
        setError('Escenarios no disponibles. Mostrando resumen parcial.')
      }

      // Crear síntesis
      const newSynthesis: SynthesisData = {
        summary,
        whyItMatters,
        topAssets,
        scenarios,
        generatedAt: new Date().toISOString()
      }

      // Solo actualizar si tenemos al menos resumen o escenarios
      if (summary || scenarios.length > 0) {
        setSynthesis(newSynthesis)
        lastValidSynthesisRef.current = newSynthesis
        onUpdate?.()
      } else {
        throw new Error('No se pudo generar síntesis: datos insuficientes')
      }

    } catch (err: any) {
      console.error('Error generando síntesis:', err)
      const errorMsg = err.message || 'Error al generar síntesis'
      setError(errorMsg)
      setIsDegraded(true)

      // Si hay último resultado válido, mantenerlo
      if (lastValidSynthesisRef.current) {
        setSynthesis({
          ...lastValidSynthesisRef.current,
          hasError: true,
          errorMessage: errorMsg
        })
      }
    } finally {
      setIsLoading(false)
      setIsRecalculating(false)
    }
  }

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
