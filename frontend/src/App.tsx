import { useState, useEffect, Component, ReactNode } from 'react'
import NewsWidget from './components/NewsWidget'
import AssistantWidget from './components/AssistantWidget'
import PortfolioWidget from './components/PortfolioWidget'
import PortfolioSummaryCard from './components/PortfolioSummaryCard'
import { newsApi, NewsItem } from './services/api'
import './App.css'

// Error Boundary para capturar errores de renderizado
interface ErrorBoundaryProps {
  children: ReactNode
}

interface ErrorBoundaryState {
  hasError: boolean
  error: Error | null
}

class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, errorInfo: any) {
    console.error('Error capturado por ErrorBoundary:', error, errorInfo)
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{ 
          background: 'white', 
          padding: '40px', 
          borderRadius: '12px',
          color: '#0a1929',
          margin: '20px',
          boxShadow: '0 4px 12px rgba(0,0,0,0.1)'
        }}>
          <h2 style={{ color: '#dc2626' }}>⚠️ Error al Renderizar</h2>
          <p><strong>Error:</strong> {this.state.error?.message}</p>
          <pre style={{ 
            marginTop: '10px', 
            padding: '10px', 
            background: '#f5f5f5', 
            borderRadius: '4px',
            fontSize: '12px',
            overflow: 'auto'
          }}>
            {this.state.error?.stack}
          </pre>
          <button 
            onClick={() => window.location.reload()}
            style={{
              marginTop: '20px',
              padding: '10px 20px',
              background: '#1f6b47',
              color: 'white',
              border: 'none',
              borderRadius: '6px',
              cursor: 'pointer'
            }}
          >
            Recargar Página
          </button>
        </div>
      )
    }

    return this.props.children
  }
}

function App() {
  const [newsItems, setNewsItems] = useState<NewsItem[]>([])
  const [portfolioRefreshTrigger, setPortfolioRefreshTrigger] = useState(0)
  const [newsRefreshTrigger, setNewsRefreshTrigger] = useState(0)
  const [error, setError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  // Cargar noticias al iniciar
  useEffect(() => {
    loadNews()
  }, [])

  const loadNews = async () => {
    try {
      setIsLoading(true)
      const items = await newsApi.list('score')
      setNewsItems(items)
      setNewsRefreshTrigger(prev => prev + 1)
    } catch (err: any) {
      console.error('Error al cargar noticias:', err)
      setError(`Error al conectar con el backend: ${err.message}`)
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <ErrorBoundary>
      <div className="app">
        <header className="app-header">
          <h1>Faro</h1>
          <p>Confident Investment Intelligence</p>
        </header>

        <main className="app-main">
          {error && (
            <div style={{ 
              background: '#fee2e2', 
              color: '#dc2626', 
              padding: '12px', 
              borderRadius: '8px',
              marginBottom: '20px'
            }}>
              ⚠️ {error}
            </div>
          )}
          {isLoading && (
            <div style={{ 
              background: 'white', 
              padding: '20px', 
              borderRadius: '8px',
              marginBottom: '20px',
              textAlign: 'center'
            }}>
              Cargando...
            </div>
          )}
          <div className="widgets-grid">
            <div className="summary-section">
              <PortfolioSummaryCard refreshTrigger={portfolioRefreshTrigger} />
            </div>
            
            <PortfolioWidget 
              onUpdate={() => {
                setPortfolioRefreshTrigger(prev => prev + 1)
              }}
              refreshTrigger={portfolioRefreshTrigger}
            />
            
            <NewsWidget
              refreshTrigger={newsRefreshTrigger}
              maxItems={10}
              sortBy="score"
              onUpdate={() => {
                setNewsRefreshTrigger(prev => prev + 1)
              }}
            />
            
            <AssistantWidget
              refreshTrigger={newsRefreshTrigger}
              maxItems={10}
              onUpdate={() => {
                // Actualizar cuando el asistente genera nuevos análisis
              }}
            />
          </div>
        </main>
      </div>
    </ErrorBoundary>
  )
}

export default App

