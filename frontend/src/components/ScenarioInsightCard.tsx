import './ScenarioInsightCard.css'

interface ScenarioInsightCardProps {
  scenario: {
    title: string
    description: string
    confidence: number
    assumptions?: Array<{ description: string; probability?: number; timeframe?: string }>
    risks?: Array<{ description: string; severity?: string; mitigation?: string }>
    invalidators?: Array<{ condition: string; description: string }>
    timeframe?: string
    market_impact?: string
    suggested_actions?: string[]
    triggers?: string[]
  } | null | undefined
  type: 'base' | 'risk' | 'opportunity'
  typeLabel: string
}

/**
 * Convierte un párrafo largo en bullets para mejor legibilidad
 */
function paragraphToBullets(text: string): string[] {
  if (!text || !text.trim()) return []
  
  // Dividir por párrafos
  const paragraphs = text.split('\n').filter(p => p.trim())
  const bullets: string[] = []
  
  for (const paragraph of paragraphs) {
    // Si el párrafo es corto (< 100 chars), agregarlo como bullet único
    if (paragraph.length < 100) {
      bullets.push(paragraph.trim())
    } else {
      // Dividir párrafo largo en oraciones
      const sentences = paragraph.split(/[.!?]+/).filter(s => s.trim().length > 20)
      bullets.push(...sentences.map(s => s.trim()).filter(s => s.length > 0))
    }
  }
  
  // Limitar a 5 bullets máximo para mantener concisión
  return bullets.slice(0, 5)
}

/**
 * Extrae el key takeaway del escenario (título o primera frase de la descripción)
 */
function extractKeyTakeaway(scenario: ScenarioInsightCardProps['scenario']): string {
  // Usar el título como key takeaway principal
  if (scenario.title) {
    return scenario.title
  }
  
  // Fallback: primera frase de la descripción
  if (scenario.description) {
    const firstSentence = scenario.description.split(/[.!?]+/)[0].trim()
    return firstSentence.length > 0 ? firstSentence : scenario.description.substring(0, 100)
  }
  
  return 'Escenario sin información disponible'
}

export default function ScenarioInsightCard({ scenario, type, typeLabel }: ScenarioInsightCardProps) {
  if (!scenario) {
    return null
  }
  
  const keyTakeaway = extractKeyTakeaway(scenario)
  // Limitar descripción a 2-3 bullets clave más una oración descriptiva corta
  const descriptionBullets = paragraphToBullets(scenario.description || '').slice(0, 3)
  const hasAssumptions = scenario.assumptions && scenario.assumptions.length > 0
  const hasRisks = scenario.risks && scenario.risks.length > 0
  const hasInvalidators = scenario.invalidators && scenario.invalidators.length > 0
  const hasMarketImpact = scenario.market_impact && scenario.market_impact.trim().length > 0
  const hasSuggestedActions = scenario.suggested_actions && scenario.suggested_actions.length > 0
  const hasTriggers = scenario.triggers && scenario.triggers.length > 0
  
  return (
    <div className={`scenario-insight-card ${type}`}>
      {/* Header con tipo y confianza */}
      <div className="scenario-header">
        <h4 className="scenario-type-label">{typeLabel}</h4>
        <span className="confidence-badge">
          {(scenario.confidence * 100).toFixed(0)}% confianza
        </span>
      </div>
      
      {/* Key Takeaway - Prominente */}
      <div className="key-takeaway">
        <span className="takeaway-icon">💡</span>
        <p className="takeaway-text">{keyTakeaway}</p>
      </div>
      
      {/* Context - Descripción en bullets */}
      {descriptionBullets.length > 0 && (
        <div className="insight-section context">
          <h5 className="section-heading">CONTEXTO</h5>
          <ul className="insight-bullets">
            {descriptionBullets.map((bullet, idx) => (
              <li key={idx} className="bullet-item">{bullet}</li>
            ))}
          </ul>
        </div>
      )}
      
      {/* Market Impact - Impacto esperado en el mercado */}
      {hasMarketImpact && (
        <div className="insight-section market-impact">
          <h5 className="section-heading">IMPACTO ESPERADO</h5>
          <p className="impact-description">{scenario.market_impact}</p>
        </div>
      )}
      
      {/* Impact - Supuestos y Riesgos (compacto, máximo 2 items cada uno) */}
      {(hasAssumptions || hasRisks) && (
        <div className="insight-section impact">
          <h5 className="section-heading">Análisis</h5>
          
          {hasAssumptions && (
            <div className="subsection">
              <h6 className="subsection-heading">Supuestos Clave:</h6>
              <ul className="insight-bullets">
                {scenario.assumptions!.slice(0, 2).map((assumption, idx) => (
                  <li key={idx} className="bullet-item">
                    {assumption.description}
                    {assumption.probability && (
                      <span className="bullet-meta"> (Prob: {(assumption.probability * 100).toFixed(0)}%)</span>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          )}
          
          {hasRisks && (
            <div className="subsection">
              <h6 className="subsection-heading">Riesgos:</h6>
              <ul className="insight-bullets">
                {scenario.risks!.slice(0, 2).map((risk, idx) => (
                  <li key={idx} className="bullet-item">
                    {risk.description}
                    {risk.severity && (
                      <span className={`bullet-meta severity-${risk.severity.toLowerCase()}`}>
                        {' '}• {risk.severity}
                      </span>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
      
      {/* Suggested Actions - Acciones sugeridas */}
      {hasSuggestedActions && (
        <div className="insight-section suggested-actions">
          <h5 className="section-heading">ACCIONES SUGERIDAS</h5>
          <ul className="insight-bullets compact">
            {scenario.suggested_actions!.slice(0, 3).map((action, idx) => (
              <li key={idx} className="bullet-item action-item">
                <span className="action-icon">⚡</span>
                {action}
              </li>
            ))}
          </ul>
        </div>
      )}
      
      {/* Triggers - Condiciones trigger o eventos a monitorear */}
      {hasTriggers && (
        <div className="insight-section triggers">
          <h5 className="section-heading">EVENTOS A MONITOREAR</h5>
          <ul className="insight-bullets compact">
            {scenario.triggers!.slice(0, 3).map((trigger, idx) => (
              <li key={idx} className="bullet-item trigger-item">
                <span className="trigger-icon">📅</span>
                {trigger}
              </li>
            ))}
          </ul>
        </div>
      )}
      
      {/* Next Steps - Invalidadores y Timeframe (compacto) */}
      {(hasInvalidators || scenario.timeframe) && (
        <div className="insight-section next-steps">
          <h5 className="section-heading">TIMELINE</h5>
          
          {scenario.timeframe && (
            <div className="timeframe-info">
              <span className="timeframe-label">Horizonte:</span>
              <span className="timeframe-value">{scenario.timeframe}</span>
            </div>
          )}
          
          {hasInvalidators && (
            <div className="subsection">
              <h6 className="subsection-heading">Invalidadores:</h6>
              <ul className="insight-bullets compact">
                {scenario.invalidators!.slice(0, 2).map((invalidator, idx) => (
                  <li key={idx} className="bullet-item">
                    <strong>{invalidator.condition}:</strong> {invalidator.description}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

