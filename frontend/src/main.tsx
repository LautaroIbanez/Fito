import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import { diagnostics } from './utils/diagnostics'
import './index.css'

// Verificar que el elemento root existe
const rootElement = document.getElementById('root')
if (!rootElement) {
  throw new Error('No se encontró el elemento #root en el DOM')
}

console.log('%c[APP] 🚀 Iniciando Faro...', 'color: #1f6b47; font-weight: bold; font-size: 16px', {
  timestamp: new Date().toISOString(),
  userAgent: navigator.userAgent
})

ReactDOM.createRoot(rootElement).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)

console.log('%c[APP] ✅ React renderizado', 'color: #1f6b47; font-weight: bold')

// Imprimir resumen de diagnóstico después de 5 segundos
setTimeout(() => {
  diagnostics.printSummary()
  
  // Verificar si hay llamadas pendientes que puedan estar bloqueando
  const pending = diagnostics.getPendingCalls()
  if (pending.length > 0) {
    console.warn(
      `%c[APP] ⚠️ ADVERTENCIA: ${pending.length} llamada(s) HTTP aún pendiente(s) después de 5 segundos`,
      'color: #f59e0b; font-weight: bold; font-size: 14px',
      pending.map(c => ({ url: c.url, elapsed: `${c.elapsed.toFixed(0)}ms` }))
    )
  }
}, 5000)





