// Versión de depuración para identificar el problema
import { useState, useEffect } from 'react'
import './App.css'

function AppDebug() {
  const [status, setStatus] = useState('Cargando...')

  useEffect(() => {
    // Verificar que React funciona
    setStatus('React está funcionando!')
    
    // Intentar cargar componentes
    try {
      import('./components/NewsWidget').then(() => {
        setStatus(prev => prev + ' | NewsWidget OK')
      }).catch(err => {
        setStatus(prev => prev + ' | NewsWidget ERROR: ' + err.message)
      })
    } catch (err: any) {
      setStatus('Error al importar componentes: ' + err.message)
    }
  }, [])

  return (
    <div className="app">
      <header className="app-header">
        <h1>Faro - Debug Mode</h1>
        <p>Status: {status}</p>
      </header>

      <main className="app-main">
        <div style={{ 
          background: 'white', 
          padding: '20px', 
          borderRadius: '8px',
          color: '#333'
        }}>
          <h2>Información de Depuración</h2>
          <ul>
            <li>React: Funcionando ✓</li>
            <li>CSS: Cargado (fondo azul visible)</li>
            <li>Status: {status}</li>
          </ul>
          
          <h3>Próximos pasos:</h3>
          <ol>
            <li>Abre la consola del navegador (F12)</li>
            <li>Revisa si hay errores en rojo</li>
            <li>Comparte los errores que veas</li>
          </ol>
        </div>
      </main>
    </div>
  )
}

export default AppDebug
