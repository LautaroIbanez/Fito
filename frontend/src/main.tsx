import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './index.css'

// Verificar que el elemento root existe
const rootElement = document.getElementById('root')
if (!rootElement) {
  throw new Error('No se encontró el elemento #root en el DOM')
}

console.log('🚀 Iniciando Faro...')

ReactDOM.createRoot(rootElement).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)

console.log('✅ React renderizado')





