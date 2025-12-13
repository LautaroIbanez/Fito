# Sistema de Diagnóstico - Investigación de Carga Inicial

## Resumen

Se ha implementado un sistema completo de diagnóstico para identificar qué está bloqueando el render inicial de la página HOY (Asistente IA Proactivo + Escenarios).

## Componentes Implementados

### 1. Sistema de Diagnóstico (`frontend/src/utils/diagnostics.ts`)

Sistema centralizado que:
- Rastrea todas las llamadas HTTP (request/response)
- Mide tiempos de respuesta
- Detecta llamadas lentas (>5s) y fallidas
- Identifica llamadas pendientes que pueden estar bloqueando el render
- Registra estados de componentes
- Captura errores no manejados

### 2. Interceptores de Axios (`frontend/src/services/api.ts`)

Interceptores automáticos que:
- Registran cada llamada HTTP al inicio
- Registran cada respuesta HTTP al finalizar
- Miden duración de cada llamada
- Alertan sobre llamadas lentas o fallidas

### 3. Logging en Componentes

**HoyView:**
- Log del estado inicial del componente
- Identificación de bloqueos de render cuando `isLoading=true`
- Monitoreo periódico (cada 10s) de llamadas pendientes
- Log detallado de `loadHoyData`

**ProactiveAssistant:**
- Log del inicio de `generateSynthesis`
- Estado del componente durante la generación

**main.tsx:**
- Log de inicio de aplicación
- Resumen automático después de 5 segundos
- Alerta si hay llamadas pendientes

## Cómo Usar el Sistema de Diagnóstico

### 1. Abrir la Consola del Navegador

1. Abre la aplicación en el navegador
2. Presiona `F12` o `Ctrl+Shift+I` (Windows/Linux) o `Cmd+Option+I` (Mac)
3. Ve a la pestaña **Console**

### 2. Observar los Logs

Los logs aparecerán con colores:
- **Verde** (`#1f6b47`): Información normal, llamadas exitosas
- **Azul** (`#2563eb`): Requests HTTP
- **Naranja** (`#f59e0b`): Advertencias, llamadas lentas, bloqueos
- **Rojo** (`#dc2626`): Errores, llamadas fallidas

### 3. Comandos Útiles en Consola

```javascript
// Ver resumen de todas las llamadas HTTP
diagnostics.printSummary()

// Ver llamadas pendientes
diagnostics.getPendingCalls()

// Ver llamadas lentas (>5s)
diagnostics.getSlowCalls()

// Ver llamadas fallidas
diagnostics.getFailedCalls()

// Limpiar historial
diagnostics.clear()
```

## Qué Buscar

### 1. Llamadas HTTP Pendientes

Si ves mensajes como:
```
⚠️ Hay X llamada(s) HTTP pendiente(s) que pueden estar bloqueando el render
```

Esto indica que hay llamadas que no han completado y pueden estar bloqueando el render.

**Acción:** Revisar qué llamadas están pendientes y por qué no completan.

### 2. Llamadas Lentas

Si ves mensajes como:
```
⚠️ Llamada HTTP lenta detectada: POST /api/scenarios (15000ms)
```

Esto indica que una llamada está tardando más de 5 segundos.

**Acción:** Verificar si el backend está procesando correctamente o si hay un problema de red.

### 3. Errores HTTP

Si ves mensajes como:
```
❌ Error en llamada HTTP: GET /api/news/summary
```

Esto indica que una llamada falló.

**Acción:** Revisar el error específico y verificar el backend.

### 4. Bloqueos de Render

Si ves mensajes como:
```
⚠️ Render bloqueado en HoyView
```

Esto indica que el componente está esperando algo antes de renderizar.

**Acción:** Revisar qué estado está bloqueando (`isLoading`, `isGenerating`, etc.) y qué llamadas están pendientes.

## Flujo de Carga Esperado

1. **Inicio de aplicación** → Log: `[APP] 🚀 Iniciando Faro...`
2. **Render de React** → Log: `[APP] ✅ React renderizado`
3. **Montaje de HoyView** → Log: `[COMPONENT STATE] HoyView`
4. **Si hay llamadas HTTP** → Logs: `[HTTP REQUEST]` y `[HTTP RESPONSE]`
5. **Después de 5 segundos** → Resumen automático
6. **Cada 10 segundos** → Verificación de llamadas pendientes

## Puntos de Bloqueo Identificados

### 1. `HoyView` - Estado `isLoading`

**Ubicación:** `frontend/src/views/HoyView.tsx:257`

**Condición:** Si `isLoading === true`, el componente muestra "Cargando..." y no renderiza el contenido.

**Causas posibles:**
- `loadHoyData()` está ejecutándose y esperando respuestas de:
  - `newsApi.getSituationSummary()`
  - `portfolioApi.list()`
  - `scenariosApi.generate()`

**Diagnóstico:** El sistema detecta automáticamente cuando `isLoading=true` y muestra qué llamadas están pendientes.

### 2. `ProactiveAssistant` - Generación de Síntesis

**Ubicación:** `frontend/src/components/ProactiveAssistant.tsx:107`

**Condición:** Si `generateSynthesis()` está ejecutándose, puede tardar hasta 180 segundos.

**Causas posibles:**
- Esperando respuesta de `newsApi.getSituationSummary()` (timeout: 60s)
- Esperando respuesta de `scenariosApi.generate()` (timeout: 180s)

**Diagnóstico:** El sistema registra el inicio de `generateSynthesis` y todas las llamadas HTTP asociadas.

### 3. Escenarios - Estado Vacío

**Ubicación:** `frontend/src/views/HoyView.tsx:468`

**Condición:** Si `scenarios.length === 0`, muestra "Generando escenarios..."

**Causas posibles:**
- Los escenarios no se han generado aún
- Los escenarios se generaron pero no se actualizaron en el estado
- Error al generar escenarios

**Diagnóstico:** El sistema registra cuando se actualizan los escenarios y si hay errores.

## Evidencia Esperada

Después de implementar este sistema, deberías ver en la consola:

1. **Al cargar la página:**
   ```
   [APP] 🚀 Iniciando Faro...
   [APP] ✅ React renderizado
   [COMPONENT STATE] HoyView { isLoading: false, hasSynthesis: false, ... }
   ```

2. **Si hay llamadas HTTP:**
   ```
   [HTTP REQUEST] GET http://localhost:8001/api/portfolio
   [HTTP RESPONSE] GET http://localhost:8001/api/portfolio - HTTP 200 (45ms)
   ```

3. **Si hay problemas:**
   ```
   ⚠️ Hay 2 llamada(s) HTTP pendiente(s) después de 5s desde la carga
   [DIAGNOSTICS] Resumen de llamadas HTTP
   ```

## Próximos Pasos

1. **Recargar la aplicación** y abrir la consola del navegador
2. **Observar los logs** durante la carga inicial
3. **Identificar** qué llamadas están pendientes o fallando
4. **Documentar** los tiempos de respuesta y errores específicos
5. **Usar** `diagnostics.printSummary()` en la consola para ver un resumen completo

## Notas Técnicas

- El sistema de diagnóstico está **siempre activo en desarrollo** (`import.meta.env.DEV`)
- Puedes habilitarlo en producción con: `localStorage.setItem('enableDiagnostics', 'true')`
- Los logs usan `performance.now()` para medir tiempos precisos
- El sistema expone `window.diagnostics` para acceso desde la consola

