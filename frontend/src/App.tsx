import { useState, Component, ReactNode } from 'react'
import Navigation, { View } from './components/Navigation'
import HoyView from './views/HoyView'
import SenalesView from './views/SenalesView'
import ActivoView from './views/ActivoView'
import NoticiasView from './views/NoticiasView'
import Modal from './components/Modal'
import NewsForm from './components/NewsForm'
import PortfolioForm from './components/PortfolioForm'
import { newsApi, portfolioApi, PortfolioItemCreate } from './services/api'
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
  const [currentView, setCurrentView] = useState<View>('hoy')
  const [isNewsModalOpen, setIsNewsModalOpen] = useState(false)
  const [isPortfolioModalOpen, setIsPortfolioModalOpen] = useState(false)
  const [isSubmittingNews, setIsSubmittingNews] = useState(false)
  const [isSubmittingPortfolio, setIsSubmittingPortfolio] = useState(false)

  const handleAddNews = () => {
    setIsNewsModalOpen(true)
  }

  const handleManagePortfolio = () => {
    setIsPortfolioModalOpen(true)
  }

  const handleNewsSubmit = async (title: string, body: string, source: string) => {
    setIsSubmittingNews(true)
    try {
      await newsApi.create({ title, body, source })
      setIsNewsModalOpen(false)
      // La vista HOY se actualizará automáticamente al recargar
    } catch (err: any) {
      throw new Error(err.message || 'Error al guardar la noticia')
    } finally {
      setIsSubmittingNews(false)
    }
  }

  const handlePortfolioSubmit = async (item: PortfolioItemCreate) => {
    setIsSubmittingPortfolio(true)
    try {
      await portfolioApi.create(item)
      setIsPortfolioModalOpen(false)
      // La vista HOY se actualizará automáticamente al recargar
    } catch (err: any) {
      throw new Error(err.message || 'Error al guardar el activo')
    } finally {
      setIsSubmittingPortfolio(false)
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
          <Navigation currentView={currentView} onViewChange={setCurrentView} />
          
          {currentView === 'hoy' && (
            <HoyView 
              onAddNews={handleAddNews}
              onManagePortfolio={handleManagePortfolio}
            />
          )}
          
          {currentView === 'senales' && <SenalesView />}
          
          {currentView === 'cartera' && <ActivoView />}
          
          {currentView === 'noticias' && <NoticiasView />}
        </main>

        {/* Modal para agregar noticia */}
        <Modal
          isOpen={isNewsModalOpen}
          onClose={() => setIsNewsModalOpen(false)}
          title="Agregar Noticia"
        >
          <NewsForm
            onSubmit={handleNewsSubmit}
            isSubmitting={isSubmittingNews}
          />
        </Modal>

        {/* Modal para gestionar cartera */}
        <Modal
          isOpen={isPortfolioModalOpen}
          onClose={() => setIsPortfolioModalOpen(false)}
          title="Agregar Activo a la Cartera"
        >
          <PortfolioForm
            onSubmit={handlePortfolioSubmit}
            onCancel={() => setIsPortfolioModalOpen(false)}
            isSubmitting={isSubmittingPortfolio}
          />
        </Modal>
      </div>
    </ErrorBoundary>
  )
}

export default App

