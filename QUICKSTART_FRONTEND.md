# Iniciar Frontend de Faro

El backend ya está corriendo en el puerto 8001. Ahora necesitas iniciar el frontend.

## Pasos para iniciar el frontend:

1. **Abre una nueva terminal** (deja el backend corriendo en la terminal actual)

2. **Navega al directorio del frontend:**
   ```powershell
   cd C:\Users\lauta\OneDrive\Desktop\Trading\Fito\news-analyzer\frontend
   ```

3. **Instala las dependencias** (solo la primera vez):
   ```powershell
   npm install
   ```

4. **Inicia el servidor de desarrollo:**
   ```powershell
   npm run dev
   ```

5. **Abre tu navegador** en:
   ```
   http://localhost:3001
   ```

## Solución de problemas:

### Si ves errores de compilación:

1. **Verifica que design-tokens.css existe:**
   ```powershell
   dir src\design-tokens.css
   ```

2. **Si falta, verifica la importación en index.css:**
   - Debe tener: `@import './design-tokens.css';`

3. **Limpia y reinstala:**
   ```powershell
   rm -r node_modules
   npm install
   ```

### Si no ves nada en el navegador:

1. **Abre la consola del navegador** (F12) y revisa errores
2. **Verifica que el backend esté corriendo** en http://localhost:8001
3. **Verifica la URL del frontend** en http://localhost:3001

### Si hay errores de CORS:

El frontend está configurado para hacer proxy a `/api` hacia `http://localhost:8001`, así que no debería haber problemas de CORS.

## Estructura esperada:

```
frontend/
├── src/
│   ├── design-tokens.css  ← Debe existir
│   ├── index.css          ← Importa design-tokens.css
│   ├── App.tsx
│   └── ...
├── package.json
└── vite.config.ts
```

## Comandos útiles:

- `npm run dev` - Inicia servidor de desarrollo
- `npm run build` - Construye para producción
- `npm run preview` - Previsualiza build de producción
