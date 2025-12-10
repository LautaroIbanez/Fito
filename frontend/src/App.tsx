import { useState, useEffect } from 'react'
import NewsForm from './components/NewsForm'
import NewsList from './components/NewsList'
import AnalysisView from './components/AnalysisView'
import PortfolioTable from './components/PortfolioTable'
import RiskDashboard from './components/RiskDashboard'
import AlertTriggers from './components/AlertTriggers'
import AlertHistory from './components/AlertHistory'
import BacktestManager from './components/BacktestManager'
import AssetSuggestions from './components/AssetSuggestions'
import AssetThesis from './components/AssetThesis'
import DynamicLimits from './components/DynamicLimits'
import DecisionLog from './components/DecisionLog'
import { newsApi, NewsItem, AnalysisResponse } from './services/api'
import './App.css'

type AppState = 'idle' | 'loading' | 'saving' | 'generating' | 'error'

function App() {
  const [newsItems, setNewsItems] = useState<NewsItem[]>([])
  const [analysis, setAnalysis] = useState<AnalysisResponse | null>(null)
  const [state, setState] = useState<AppState>('idle')
  const [error, setError] = useState<string | null>(null)
  const [successMessage, setSuccessMessage] = useState<string | null>(null)
  const [portfolioRefreshTrigger, setPortfolioRefreshTrigger] = useState(0)

  // Cargar noticias al iniciar
  useEffect(() => {
    loadNews()
  }, [])

  const loadNews = async () => {
    try {
      setState('loading')
      const items = await newsApi.list('score')  // Ordenar por score por defecto
      setNewsItems(items)
      setState('idle')
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Error al cargar noticias')
      setState('error')
    }
  }

  const handleNewsSubmit = async (title: string, body: string, source: string) => {
    try {
      setState('saving')
      setError(null)
      await newsApi.create({ title: title || undefined, body, source: source || undefined })
      await loadNews()
      setState('idle')
    } catch (err: any) {
      const errorMsg = err.response?.data?.detail || 'Error al guardar la noticia'
      setError(errorMsg)
      setState('error')
      throw new Error(errorMsg)
    }
  }

  const handleDeleteNews = async (id: number) => {
    try {
      setState('loading')
      await newsApi.delete(id)
      await loadNews()
      // Si había un análisis, limpiarlo ya que las noticias cambiaron
      setAnalysis(null)
      setState('idle')
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Error al eliminar la noticia')
      setState('error')
    }
  }

  const handleClearAllNews = async () => {
    if (!confirm('¿Estás seguro de limpiar todas las noticias? Esta acción no se puede deshacer.')) {
      return
    }

    try {
      setState('loading')
      setError(null)
      await newsApi.clearAll()
      setNewsItems([])
      // Limpiar análisis ya que no hay noticias
      setAnalysis(null)
      setSuccessMessage('✅ Todas las noticias han sido eliminadas correctamente.')
      setState('idle')
      
      // Ocultar mensaje de éxito después de 3 segundos
      setTimeout(() => {
        setSuccessMessage(null)
      }, 3000)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Error al limpiar las noticias')
      setState('error')
    }
  }

  const handleGenerateAnalysis = async () => {
    try {
      setState('generating')
      setError(null)
      const result = await newsApi.generateAnalysis()
      setAnalysis(result)
      setState('idle')
    } catch (err: any) {
      const errorMsg = err.response?.data?.detail || 'Error al generar el análisis'
      setError(errorMsg)
      setState('error')
    }
  }

  const canGenerateAnalysis = newsItems.length > 0 && state !== 'generating' && state !== 'saving'

  return (
    <div className="app">
      <header className="app-header">
        <h1>📰 News Analyzer</h1>
        <p>Análisis de noticias con OpenAI</p>
      </header>

      <main className="app-main">
        {error && (
          <div className="error-banner">
            <span>⚠️ {error}</span>
            <button onClick={() => setError(null)}>✕</button>
          </div>
        )}

        {successMessage && (
          <div className="success-banner">
            <span>{successMessage}</span>
            <button onClick={() => setSuccessMessage(null)}>✕</button>
          </div>
        )}

        <div className="app-content">
          <div className="left-panel">
            <PortfolioTable onUpdate={() => {
              // Si hay un análisis, limpiarlo cuando la cartera cambia
              if (analysis) {
                setAnalysis(null)
              }
              // Refrescar dashboard de riesgo
              setPortfolioRefreshTrigger(prev => prev + 1)
            }} />
            <RiskDashboard refreshTrigger={portfolioRefreshTrigger} />
            <AlertTriggers />
            <AlertHistory />
            <BacktestManager />
            <AssetSuggestions />
            <DynamicLimits />
            <DecisionLog />
            <AssetThesis onUpdate={() => {
              // Refrescar si es necesario
            }} />
            <NewsForm
              onSubmit={handleNewsSubmit}
              isSubmitting={state === 'saving'}
            />
            <NewsList
              items={newsItems}
              onDelete={handleDeleteNews}
              onClearAll={handleClearAllNews}
              isLoading={state === 'loading'}
            />
          </div>

          <div className="right-panel">
            <AnalysisView
              analysis={analysis}
              newsCount={newsItems.length}
              onGenerate={handleGenerateAnalysis}
              isGenerating={state === 'generating'}
              canGenerate={canGenerateAnalysis}
            />
          </div>
        </div>
      </main>
    </div>
  )
}

export default App

