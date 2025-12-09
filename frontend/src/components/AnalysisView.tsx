import { AnalysisResponse } from '../services/api'
import './AnalysisView.css'

interface AnalysisViewProps {
  analysis: AnalysisResponse | null
  newsCount: number
  onGenerate: () => void
  isGenerating: boolean
  canGenerate: boolean
}

export default function AnalysisView({
  analysis,
  newsCount,
  onGenerate,
  isGenerating,
  canGenerate,
}: AnalysisViewProps) {
  const formatDate = (dateString: string) => {
    const date = new Date(dateString)
    return new Intl.DateTimeFormat('es-ES', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    }).format(date)
  }

  const handleCopy = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text)
      alert('Análisis copiado al portapapeles')
    } catch (err) {
      console.error('Error al copiar:', err)
    }
  }

  const handleDownload = () => {
    if (!analysis) return
    
    const content = `ANÁLISIS DE NOTICIAS
Generado: ${formatDate(analysis.generated_at)}
Versión: ${analysis.version}
Noticias analizadas: ${analysis.news_count}
Modelo: ${analysis.analysis.model_used}

${analysis.analysis.raw}
`
    const blob = new Blob([content], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `analisis-noticias-${analysis.version}.txt`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  return (
    <div className="analysis-view-container">
      <div className="analysis-header">
        <h2>🔍 Análisis Consolidado</h2>
        <button
          className="generate-button"
          onClick={onGenerate}
          disabled={!canGenerate || isGenerating}
        >
          {isGenerating ? '⏳ Generando análisis...' : '🚀 Generar Análisis'}
        </button>
      </div>

      {newsCount === 0 && (
        <div className="empty-state">
          <p>Se requiere al menos una noticia para generar el análisis.</p>
        </div>
      )}

      {isGenerating && (
        <div className="generating-state">
          <div className="spinner"></div>
          <p>Generando análisis con OpenAI...</p>
          <p className="hint">Esto puede tardar unos momentos.</p>
        </div>
      )}

      {analysis && !isGenerating && (
        <div className="analysis-content">
          <div className="analysis-meta">
            <div className="meta-item">
              <strong>Generado:</strong> {formatDate(analysis.generated_at)}
            </div>
            <div className="meta-item">
              <strong>Versión:</strong> {analysis.version}
            </div>
            <div className="meta-item">
              <strong>Noticias analizadas:</strong> {analysis.news_count}
            </div>
            <div className="meta-item">
              <strong>Items en cartera:</strong> {analysis.portfolio_count || 0}
            </div>
            <div className="meta-item">
              <strong>Modelo:</strong> {analysis.analysis.model_used}
            </div>
            {analysis.analysis.tokens_used && (
              <div className="meta-item">
                <strong>Tokens usados:</strong> {analysis.analysis.tokens_used}
              </div>
            )}
          </div>

          <div className="analysis-actions">
            <button
              className="action-button copy-button"
              onClick={() => handleCopy(analysis.analysis.raw)}
            >
              📋 Copiar Análisis
            </button>
            <button
              className="action-button download-button"
              onClick={handleDownload}
            >
              💾 Descargar
            </button>
          </div>

          <div className="analysis-sections">
            {analysis.analysis.structured.resumen_ejecutivo && (
              <section className="analysis-section">
                <h3>📊 Resumen Ejecutivo</h3>
                <div className="section-content">
                  {analysis.analysis.structured.resumen_ejecutivo}
                </div>
              </section>
            )}

            {analysis.analysis.structured.riesgos_identificados && (
              <section className="analysis-section">
                <h3>⚠️ Riesgos Identificados</h3>
                <div className="section-content">
                  {analysis.analysis.structured.riesgos_identificados}
                </div>
              </section>
            )}

            {analysis.analysis.structured.actores_clave && (
              <section className="analysis-section">
                <h3>👥 Actores Clave</h3>
                <div className="section-content">
                  {analysis.analysis.structured.actores_clave}
                </div>
              </section>
            )}

            {analysis.analysis.structured.senales_tempranas && (
              <section className="analysis-section">
                <h3>🔔 Señales Tempranas</h3>
                <div className="section-content">
                  {analysis.analysis.structured.senales_tempranas}
                </div>
              </section>
            )}

            {analysis.analysis.structured.recomendaciones_cartera && (
              <section className="analysis-section portfolio-recommendations">
                <h3>💼 Recomendaciones de Cartera</h3>
                <div className="section-content">
                  {analysis.analysis.structured.recomendaciones_cartera}
                </div>
              </section>
            )}

            {analysis.analysis.structured.conclusiones_accionables && (
              <section className="analysis-section">
                <h3>✅ Conclusiones Accionables</h3>
                <div className="section-content">
                  {analysis.analysis.structured.conclusiones_accionables}
                </div>
              </section>
            )}

            <section className="analysis-section full-analysis">
              <h3>📄 Análisis Completo</h3>
              <div className="section-content full-text">
                {analysis.analysis.raw}
              </div>
            </section>
          </div>
        </div>
      )}
    </div>
  )
}

