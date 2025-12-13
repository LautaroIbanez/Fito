import './SensitiveAssetCard.css'

interface SensitiveAssetCardProps {
  asset: {
    identifier: string
    name?: string
    sensitivity: number
    confidence: number
    impact_description?: string
    asset_type?: string
  }
  rank: number
}

/**
 * Componente para mostrar un activo sensible con visualización mejorada,
 * etiquetas de accesibilidad y descriptor de impacto.
 */
export default function SensitiveAssetCard({ asset, rank }: SensitiveAssetCardProps) {
  const isPositive = asset.sensitivity > 0
  const isNegative = asset.sensitivity < 0
  const sensitivityPercent = Math.abs(asset.sensitivity * 100)
  const confidencePercent = asset.confidence * 100
  
  // Determinar color de confianza basado en el valor
  const getConfidenceColor = (conf: number): string => {
    if (conf >= 0.8) return 'high'
    if (conf >= 0.6) return 'medium'
    return 'low'
  }
  
  const confidenceLevel = getConfidenceColor(asset.confidence)
  
  // Texto de accesibilidad para la tendencia
  const trendAriaLabel = isPositive 
    ? `Tendencia alcista de ${sensitivityPercent.toFixed(0)} por ciento`
    : isNegative
    ? `Tendencia bajista de ${sensitivityPercent.toFixed(0)} por ciento`
    : 'Sin tendencia significativa'
  
  // Texto de accesibilidad para confianza
  const confidenceAriaLabel = `Confianza de ${confidencePercent.toFixed(0)} por ciento, nivel ${confidenceLevel === 'high' ? 'alto' : confidenceLevel === 'medium' ? 'medio' : 'bajo'}`
  
  return (
    <div className="sensitive-asset-card" role="listitem">
      {/* Rank */}
      <div className="asset-rank" aria-label={`Activo número ${rank}`}>
        <span className="rank-number">#{rank}</span>
      </div>
      
      {/* Información principal */}
      <div className="asset-main-info">
        <div className="asset-header">
          <h3 className="asset-name" id={`asset-name-${rank}`}>
            {asset.name || asset.identifier}
          </h3>
          {asset.asset_type && (
            <span className="asset-type-badge" aria-label={`Tipo de activo: ${asset.asset_type}`}>
              {asset.asset_type}
            </span>
          )}
        </div>
        
        {/* Sensibilidad con etiquetas de accesibilidad */}
        <div className="sensitivity-section">
          <div 
            className={`sensitivity-indicator ${isPositive ? 'positive' : isNegative ? 'negative' : 'neutral'}`}
            role="img"
            aria-label={trendAriaLabel}
            aria-describedby={`sensitivity-desc-${rank}`}
          >
            <span className="trend-icon" aria-hidden="true">
              {isPositive ? '📈' : isNegative ? '📉' : '➡️'}
            </span>
            <span className="sensitivity-value" id={`sensitivity-desc-${rank}`}>
              {sensitivityPercent.toFixed(0)}%
            </span>
          </div>
          <span className="sensitivity-label" aria-hidden="true">
            {isPositive ? 'Alcista' : isNegative ? 'Bajista' : 'Neutral'}
          </span>
        </div>
        
        {/* Descriptor de impacto (rationale) */}
        {asset.impact_description && (
          <div className="impact-rationale" role="note" aria-labelledby={`asset-name-${rank}`}>
            <span className="rationale-label">Por Qué Es Sensible Hoy:</span>
            <p className="rationale-text">{asset.impact_description}</p>
          </div>
        )}
      </div>
      
      {/* Confianza estandarizada */}
      <div className="confidence-section">
        <div 
          className={`confidence-badge confidence-${confidenceLevel}`}
          role="status"
          aria-label={confidenceAriaLabel}
          aria-live="polite"
        >
          <span className="confidence-label" aria-hidden="true">Confianza</span>
          <span className="confidence-value" aria-hidden="true">
            {confidencePercent.toFixed(0)}%
          </span>
          <span className="confidence-level-text" aria-hidden="true">
            {confidenceLevel === 'high' ? 'Alta' : confidenceLevel === 'medium' ? 'Media' : 'Baja'}
          </span>
        </div>
      </div>
    </div>
  )
}

