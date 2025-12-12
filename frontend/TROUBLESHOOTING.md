# Solución de Problemas - Frontend en Blanco

## Síntoma
Ves una página completamente azul oscuro (fondo del gradiente) pero sin contenido en `localhost:3001`.

## Pasos de Diagnóstico

### 1. Verifica que el frontend esté corriendo

Abre una **nueva terminal** y ejecuta:

```powershell
cd C:\Users\lauta\OneDrive\Desktop\Trading\Fito\news-analyzer\frontend
npm run dev
```

Deberías ver algo como:
```
  VITE v5.x.x  ready in xxx ms

  ➜  Local:   http://localhost:3001/
  ➜  Network: use --host to expose
```

### 2. Abre la Consola del Navegador

1. Presiona **F12** en tu navegador
2. Ve a la pestaña **Console**
3. Busca errores en **rojo**

### 3. Errores Comunes y Soluciones

#### Error: "Failed to fetch" o "Network Error"
- **Causa**: El backend no está corriendo o hay problema de CORS
- **Solución**: Verifica que el backend esté en `http://localhost:8001`

#### Error: "Cannot find module" o errores de importación
- **Causa**: Dependencias faltantes o rutas incorrectas
- **Solución**: 
  ```powershell
  cd frontend
  npm install
  ```

#### Error: "design-tokens.css not found"
- **Causa**: El archivo de tokens no existe
- **Solución**: Verifica que `src/design-tokens.css` exista

#### Error: "Port is already in use"
- **Causa**: El puerto 3001 está ocupado
- **Solución**: Vite te sugerirá otro puerto, úsalo

### 4. Verificación Rápida

Ejecuta estos comandos para verificar:

```powershell
# Verificar que design-tokens.css existe
dir src\design-tokens.css

# Verificar que node_modules existe
dir node_modules

# Limpiar e instalar de nuevo
rm -r node_modules
npm install
npm run dev
```

### 5. Si Nada Funciona

Crea un archivo `src/App-simple.tsx` temporal:

```tsx
import './App.css'

export default function App() {
  return (
    <div className="app">
      <header className="app-header">
        <h1>Faro</h1>
        <p>Confident Investment Intelligence</p>
      </header>
      <main className="app-main">
        <div style={{ background: 'white', padding: '20px', color: '#333' }}>
          <h2>Frontend Funcionando!</h2>
          <p>Si ves esto, React está funcionando correctamente.</p>
        </div>
      </main>
    </div>
  )
}
```

Y cambia `main.tsx` temporalmente:
```tsx
import App from './App-simple'
```

Si esto funciona, el problema está en los componentes. Si no funciona, el problema es más básico (React, Vite, etc.).

## Información para Compartir

Si sigues teniendo problemas, comparte:

1. **Errores de la consola del navegador** (F12 → Console)
2. **Salida de `npm run dev`** en la terminal
3. **Versión de Node**: `node --version`
4. **Versión de npm**: `npm --version`

