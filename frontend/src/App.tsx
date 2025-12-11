import { useState, useEffect } from 'react'
import NewsWidget from './components/NewsWidget'
import AssistantWidget from './components/AssistantWidget'
import PortfolioWidget from './components/PortfolioWidget'
import { newsApi, NewsItem } from './services/api'
import './App.css'

function App() {
  const [newsItems, setNewsItems] = useState<NewsItem[]>([])
  const [portfolioRefreshTrigger, setPortfolioRefreshTrigger] = useState(0)
  const [newsRefreshTrigger, setNewsRefreshTrigger] = useState(0)

  // Cargar noticias al iniciar
  useEffect(() => {
    loadNews()
  }, [])

  const loadNews = async () => {
    try {
      const items = await newsApi.list('score')
      setNewsItems(items)
      setNewsRefreshTrigger(prev => prev + 1)
    } catch (err: any) {
      console.error('Error al cargar noticias:', err)
    }
  }

  return (
    <div className="app">
      <header className="app-header">
        <h1>📰 News Analyzer</h1>
        <p>Análisis de noticias con OpenAI</p>
      </header>

      <main className="app-main">
        <div className="widgets-grid">
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
  )
}

export default App

