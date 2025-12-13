// Versión simplificada para depuración
import './App.css'

export default function AppSimple() {
  return (
    <div className="app">
      <header className="app-header">
        <h1>Faro</h1>
        <p>Confident Investment Intelligence</p>
      </header>
      <main className="app-main">
        <div style={{ 
          background: 'white', 
          padding: '40px', 
          borderRadius: '12px',
          color: '#0a1929',
          margin: '20px',
          boxShadow: '0 4px 12px rgba(0,0,0,0.1)'
        }}>
          <h2 style={{ marginBottom: '20px' }}>✅ Frontend Funcionando!</h2>
          <p>Si ves este mensaje, React está renderizando correctamente.</p>
          <p style={{ marginTop: '20px', color: '#666' }}>
            El problema podría estar en los componentes. Vamos a cargarlos uno por uno.
          </p>
        </div>
      </main>
    </div>
  )
}


