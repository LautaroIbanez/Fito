import './Navigation.css'

export type View = 'hoy' | 'senales' | 'activo'

interface NavigationProps {
  currentView: View
  onViewChange: (view: View) => void
}

export default function Navigation({ currentView, onViewChange }: NavigationProps) {
  return (
    <nav className="main-navigation">
      <button
        className={`nav-button ${currentView === 'hoy' ? 'active' : ''}`}
        onClick={() => onViewChange('hoy')}
      >
        📅 HOY
      </button>
      <button
        className={`nav-button ${currentView === 'senales' ? 'active' : ''}`}
        onClick={() => onViewChange('senales')}
      >
        🔔 SEÑALES
      </button>
      <button
        className={`nav-button ${currentView === 'activo' ? 'active' : ''}`}
        onClick={() => onViewChange('activo')}
      >
        💼 ACTIVO
      </button>
    </nav>
  )
}
