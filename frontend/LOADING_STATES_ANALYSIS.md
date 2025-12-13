# Análisis de Estados de Carga - Asistente IA Proactivo y Escenarios

## Resumen Ejecutivo

Este documento mapea los estados de carga/éxito/error en los componentes "Asistente IA Proactivo" y "Escenarios", identifica problemas con respuestas vacías, y documenta posibles bucles de re-fetch.

## 1. Mapeo de Estados de Componentes

### 1.1 ProactiveAssistant Component

**Ubicación:** `frontend/src/components/ProactiveAssistant.tsx`

#### Estados Principales

| Estado | Variable | Inicial | Descripción |
|--------|----------|---------|-------------|
| Carga inicial | `isLoading` | `false` | `true` si `autoLoad=true` | Indica si está generando síntesis inicial |
| Recalcular | `isRecalculating` | `false` | Indica si está recalculando síntesis manualmente |
| Error | `error` | `null` | Mensaje de error si falla la generación |
| Modo degradado | `isDegraded` | `false` | Indica si hay datos parciales disponibles |
| Síntesis | `synthesis` | `null` | Datos de síntesis generados (puede ser parcial) |
| Progreso | `progressMessage` | `null` | Mensaje de progreso durante generación |
| Tiempo transcurrido | `elapsedTime` | `0` | Segundos transcurridos desde inicio |

#### Flujo de Estados

```
INICIO
  ↓
[autoLoad=true] → setIsLoading(true) → generateSynthesis()
  ↓
Promise.allSettled([safeGetSummary(), safeGenerateScenarios()])
  ↓
┌─────────────────────────────────────────────────────────┐
│ Procesar resultados                                     │
│                                                         │
│ summaryData.status === 'fulfilled' &&                   │
│ summaryData.value.has_content → summary = ...           │
│                                                         │
│ scenariosData.status === 'fulfilled' &&                 │
│ scenariosData.value.drivers → scenarios = ...           │
└─────────────────────────────────────────────────────────┘
  ↓
┌─────────────────────────────────────────────────────────┐
│ Verificar si hay datos                                  │
│                                                         │
│ if (summary || scenarios.length > 0)                    │
│   → setSynthesis(newSynthesis)                         │
│   → setIsLoading(false) / setIsRecalculating(false)     │
│   → onUpdate({ summary, synthesis })                    │
│ else                                                    │
│   → throw Error('No se pudo generar síntesis...')      │
└─────────────────────────────────────────────────────────┘
  ↓
[ÉXITO] → synthesis !== null → Mostrar síntesis
  ↓
[ERROR] → error !== null → Mostrar error + último resultado válido (si existe)
```

### 1.2 HoyView Component - Sección Escenarios

**Ubicación:** `frontend/src/views/HoyView.tsx:432-468`

#### Estados Principales

| Estado | Variable | Inicial | Descripción |
|--------|----------|---------|-------------|
| Escenarios | `scenarios` | `[]` | Array de escenarios recibidos del asistente |
| Carga general | `isLoading` | `false` | Estado de carga general de la vista |
| Generando | `isGenerating` | `false` | Indica si el asistente está generando |

#### Renderizado de Escenarios

```typescript
{scenarios.length > 0 ? (
  // Mostrar escenarios
) : (
  <p className="empty-state">Generando escenarios...</p>
)}
```

**Problema identificado:** Si `scenarios.length === 0`, siempre muestra "Generando escenarios..." incluso si:
- La generación ya completó pero no hay escenarios
- El backend retornó 200 con `drivers: []`
- Hubo un error pero no se actualizó el estado

## 2. Manejo de Respuestas 200 con Payload Vacío

### 2.1 ProactiveAssistant - Resumen

**Ubicación:** `ProactiveAssistant.tsx:211-234`

```typescript
if (summaryData.status === 'fulfilled' && summaryData.value.has_content) {
  summary = summaryData.value.meta_summary || summaryData.value.summary || ''
  // ...
} else {
  console.warn('Resumen de situación no disponible:', ...)
  hasPartialData = true
}
```

**Análisis:**
- ✅ Verifica `has_content` antes de usar el resumen
- ✅ Si `status === 'fulfilled'` pero `has_content === false`, marca `hasPartialData = true`
- ✅ No lanza error, permite continuar con escenarios

**Estado resultante:**
- `summary = ''` (vacío)
- `hasPartialData = true`
- `isLoading` se resetea a `false` (línea 382)
- Se muestra síntesis parcial si hay escenarios

### 2.2 ProactiveAssistant - Escenarios

**Ubicación:** `ProactiveAssistant.tsx:237-267`

```typescript
if (scenariosData.status === 'fulfilled' && scenariosData.value.drivers) {
  scenarios = scenariosData.value.drivers || []
  // ...
} else {
  console.warn('Escenarios no disponibles:', ...)
  hasPartialData = true
}
```

**Análisis:**
- ✅ Verifica `drivers` antes de usar
- ⚠️ **PROBLEMA:** Si `status === 'fulfilled'` pero `drivers === []` o `drivers === undefined`, solo marca `hasPartialData = true`
- ✅ No lanza error, permite continuar con resumen

**Estado resultante:**
- `scenarios = []` (vacío)
- `hasPartialData = true`
- `isLoading` se resetea a `false` (línea 382)
- Se muestra síntesis parcial si hay resumen

### 2.3 Verificación de Datos Completamente Vacíos

**Ubicación:** `ProactiveAssistant.tsx:269-291`

```typescript
if (!summary && scenarios.length === 0) {
  // Construir mensaje de error detallado
  throw new Error(`No se pudo generar síntesis. ${errorDetails.join('; ')}`)
}
```

**Análisis:**
- ✅ Si ambos están vacíos, lanza error
- ✅ El error se captura en el `catch` (línea 354)
- ✅ Se resetea `isLoading` a `false` (línea 382)
- ✅ Se muestra error + último resultado válido (si existe)

**Conclusión:** ✅ El componente maneja correctamente respuestas 200 con payload vacío.

### 2.4 HoyView - Sección Escenarios

**Ubicación:** `HoyView.tsx:432-468`

```typescript
{scenarios.length > 0 ? (
  <div className="scenarios-list">
    {/* Mostrar escenarios */}
  </div>
) : (
  <p className="empty-state">Generando escenarios...</p>
)}
```

**Problema identificado:**
- ❌ **NO distingue entre:**
  - Escenarios aún generándose (`isGenerating === true`)
  - Escenarios completados pero vacíos (`isGenerating === false && scenarios.length === 0`)
  - Error al generar escenarios

**Impacto:** El usuario ve "Generando escenarios..." indefinidamente incluso cuando:
- La generación completó pero no hay escenarios
- El backend retornó 200 con `drivers: []`
- Hubo un error que no se propagó correctamente

## 3. Cierre del Spinner con Éxito Parcial

### 3.1 ProactiveAssistant

**Ubicación:** `ProactiveAssistant.tsx:293-303, 316-352, 382`

```typescript
// Si solo uno falló, activar modo degradado pero continuar
if (hasPartialData) {
  setIsDegraded(true)
  if (!summary && scenarios.length === 0) {
    setError('Datos parciales disponibles')
  } else if (!summary) {
    setError('Resumen no disponible. Mostrando escenarios.')
  } else if (scenarios.length === 0) {
    setError('Escenarios no disponibles. Mostrando resumen parcial.')
  }
}

// Actualizar síntesis si tenemos al menos algo
if (summary || scenarios.length > 0) {
  setSynthesis(newSynthesis)
  // ...
}

// En finally:
setIsLoading(false)
setIsRecalculating(false)
```

**Análisis:**
- ✅ **El spinner se cierra correctamente** con éxito parcial
- ✅ `isLoading` y `isRecalculating` se resetean a `false` en el `finally` (línea 382)
- ✅ Se muestra síntesis parcial si hay al menos resumen O escenarios
- ✅ Se activa modo degradado con mensaje apropiado

**Conclusión:** ✅ El componente cierra el spinner correctamente con éxito parcial.

### 3.2 HoyView - Sección Escenarios

**Problema:** La sección de escenarios no tiene acceso directo al estado `isGenerating` del asistente.

**Estado actual:**
- `scenarios` se actualiza desde `handleAssistantUpdate` (línea 136)
- `isGenerating` se resetea cuando el asistente completa (línea 340)
- Pero la sección de escenarios solo verifica `scenarios.length > 0`

**Solución necesaria:** Agregar verificación de `isGenerating` para distinguir entre:
- Generando: `isGenerating === true` → "Generando escenarios..."
- Completado sin datos: `isGenerating === false && scenarios.length === 0` → "No se generaron escenarios"
- Completado con datos: `scenarios.length > 0` → Mostrar escenarios

## 4. Bucles de Re-fetch

### 4.1 ProactiveAssistant - useEffect con autoLoad

**Ubicación:** `ProactiveAssistant.tsx:44-50`

```typescript
useEffect(() => {
  if (autoLoad && !hasGeneratedRef.current && !isLoading && !isRecalculating) {
    hasGeneratedRef.current = true
    generateSynthesis()
  }
}, [autoLoad]) // Depender de autoLoad
```

**Análisis:**
- ✅ Dependencia: Solo `[autoLoad]`
- ✅ Guarda: `!hasGeneratedRef.current && !isLoading && !isRecalculating`
- ✅ Flag: `hasGeneratedRef.current = true` previene múltiples ejecuciones
- ✅ **NO hay bucle:** El efecto solo se ejecuta cuando `autoLoad` cambia

**Conclusión:** ✅ No hay bucle de re-fetch en este useEffect.

### 4.2 ProactiveAssistant - useEffect con onGenerateRef

**Ubicación:** `ProactiveAssistant.tsx:54-73`

```typescript
useEffect(() => {
  if (onGenerateRef) {
    onGenerateRef.current = () => {
      if (!isLoading && !isRecalculating) {
        hasGeneratedRef.current = true
        generateSynthesis(true)
      }
    }
  }
  return () => {
    if (onGenerateRef) {
      onGenerateRef.current = null
    }
  }
}, []) // Ejecutar solo una vez al montar
```

**Análisis:**
- ✅ Dependencias: `[]` (solo al montar)
- ✅ Guarda: `!isLoading && !isRecalculating`
- ✅ **NO hay bucle:** El efecto solo se ejecuta una vez al montar
- ⚠️ **Nota:** El ref se actualiza pero no dispara re-renders

**Conclusión:** ✅ No hay bucle de re-fetch en este useEffect.

### 4.3 ProactiveAssistant - onUpdate Callback

**Ubicación:** `ProactiveAssistant.tsx:322-348`

```typescript
if (onUpdate && (summary || scenarios.length > 0)) {
  onUpdateTimeoutRef.current = setTimeout(() => {
    if (isManual || !onUpdateCalledRef.current) {
      if (!isManual) {
        onUpdateCalledRef.current = true
      }
      onUpdate({ summary, synthesis: newSynthesis })
    }
  }, 500)
}
```

**Análisis:**
- ✅ Debounce: 500ms para evitar llamadas múltiples
- ✅ Flag: `onUpdateCalledRef.current` previene múltiples llamadas en modo automático
- ✅ Guarda: Solo llama si `summary || scenarios.length > 0`
- ⚠️ **Riesgo:** Si `onUpdate` causa un re-render que cambia props, podría reiniciar el componente

**Verificación en HoyView:**

**Ubicación:** `HoyView.tsx:94-151`

```typescript
const handleAssistantUpdate = useCallback((assistantData?: { summary?: string; synthesis?: any }) => {
  if (isUpdatingFromAssistantRef.current) {
    return // Prevenir loops infinitos
  }
  isUpdatingFromAssistantRef.current = true
  // ... actualizar estados ...
  setTimeout(() => {
    isUpdatingFromAssistantRef.current = false
  }, 3000)
}, []) // Array vacío porque solo usamos refs y setters que son estables
```

**Análisis:**
- ✅ Guarda: `isUpdatingFromAssistantRef.current` previene loops
- ✅ Debounce: 3 segundos antes de permitir otra actualización
- ✅ Dependencias: `[]` (callback estable)
- ✅ **NO hay bucle:** El callback no causa re-renders que reinicien el asistente

**Conclusión:** ✅ No hay bucle de re-fetch causado por `onUpdate`.

### 4.4 HoyView - loadHoyData

**Ubicación:** `HoyView.tsx:153-254`

```typescript
const loadHoyData = async (force: boolean = false) => {
  if (!force) {
    if (assistantDataReceivedRef.current) return
    if (isGenerating) return
    if (hasSynthesis && (situationSummary || scenarios.length > 0)) return
  }
  // ... cargar datos ...
}
```

**Análisis:**
- ✅ Guardas múltiples previenen llamadas duplicadas
- ✅ Solo se llama manualmente (botón) o con `force=true`
- ✅ **NO hay useEffect** que llame automáticamente a `loadHoyData`

**Conclusión:** ✅ No hay bucle de re-fetch en `loadHoyData`.

### 4.5 Verificación de Dependencias en useEffect

**Búsqueda de useEffect con dependencias problemáticas:**

```typescript
// ProactiveAssistant.tsx
useEffect(() => {
  // ...
}, [autoLoad]) // ✅ Estable

useEffect(() => {
  // ...
}, []) // ✅ Sin dependencias

// HoyView.tsx
useEffect(() => {
  // Diagnóstico
}, []) // ✅ Sin dependencias

useEffect(() => {
  // Fallback timer (eliminado)
}, []) // ✅ Sin dependencias
```

**Conclusión:** ✅ No hay dependencias problemáticas que causen bucles.

## 5. Problemas Identificados

### 5.1 Problema 1: Sección Escenarios No Distingue Estados

**Ubicación:** `HoyView.tsx:432-468`

**Problema:**
```typescript
{scenarios.length > 0 ? (
  // Mostrar escenarios
) : (
  <p className="empty-state">Generando escenarios...</p>
)}
```

**Impacto:**
- Muestra "Generando escenarios..." incluso cuando la generación completó sin escenarios
- No distingue entre "generando" y "completado sin datos"

**Solución propuesta:**
```typescript
{scenarios.length > 0 ? (
  // Mostrar escenarios
) : isGenerating ? (
  <p className="empty-state">Generando escenarios...</p>
) : (
  <p className="empty-state">No se generaron escenarios</p>
)}
```

### 5.2 Problema 2: Falta Manejo de Error en Sección Escenarios

**Problema:**
- Si hay un error al generar escenarios, no se muestra en la sección de escenarios
- El error solo se muestra en el componente `ProactiveAssistant`

**Solución propuesta:**
- Pasar estado de error desde `ProactiveAssistant` a `HoyView`
- Mostrar mensaje de error en la sección de escenarios si `error && !isGenerating`

## 6. Resumen de Estados

### 6.1 ProactiveAssistant - Estados de Carga

| Condición | isLoading | isRecalculating | synthesis | error | UI Mostrada |
|-----------|-----------|-----------------|-----------|-------|-------------|
| Inicial | `false` | `false` | `null` | `null` | Botón "Generar Síntesis" |
| Generando (auto) | `true` | `false` | `null` | `null` | Spinner + progreso |
| Generando (manual) | `false` | `true` | `null` | `null` | Spinner + progreso |
| Éxito completo | `false` | `false` | `{...}` | `null` | Síntesis completa |
| Éxito parcial (solo resumen) | `false` | `false` | `{summary, scenarios: []}` | `"Escenarios no disponibles..."` | Síntesis parcial + advertencia |
| Éxito parcial (solo escenarios) | `false` | `false` | `{summary: "", scenarios: [...]}` | `"Resumen no disponible..."` | Síntesis parcial + advertencia |
| Error (con datos previos) | `false` | `false` | `{...}` (último válido) | `"Error..."` | Último resultado + error |
| Error (sin datos previos) | `false` | `false` | `null` | `"Error..."` | Mensaje de error |

### 6.2 HoyView - Sección Escenarios - Estados Actuales

| Condición | scenarios.length | isGenerating | UI Mostrada |
|-----------|------------------|--------------|-------------|
| Inicial | `0` | `false` | "Generando escenarios..." ❌ (incorrecto) |
| Generando | `0` | `true` | "Generando escenarios..." ✅ |
| Completado con datos | `> 0` | `false` | Escenarios ✅ |
| Completado sin datos | `0` | `false` | "Generando escenarios..." ❌ (incorrecto) |
| Error | `0` | `false` | "Generando escenarios..." ❌ (incorrecto) |

## 7. Recomendaciones

### 7.1 Corrección Inmediata (Alta Prioridad)

**Problema:** Sección escenarios no distingue estados

**Solución:**
1. Agregar verificación de `isGenerating` en renderizado de escenarios
2. Agregar estado de error para escenarios
3. Mostrar mensaje apropiado según estado

**Archivo:** `frontend/src/views/HoyView.tsx:432-468`

**Cambio propuesto:**
```typescript
{scenarios.length > 0 ? (
  <div className="scenarios-list">
    {/* Mostrar escenarios */}
  </div>
) : isGenerating ? (
  <p className="empty-state">Generando escenarios...</p>
) : (
  <p className="empty-state">No se generaron escenarios</p>
)}
```

### 7.2 Mejora Adicional (Media Prioridad)

**Problema:** Falta manejo de error en sección escenarios

**Solución:**
1. Pasar estado de error desde `ProactiveAssistant` a `HoyView`
2. Mostrar mensaje de error si existe

**Archivo:** `frontend/src/components/ProactiveAssistant.tsx` y `frontend/src/views/HoyView.tsx`

**Cambio propuesto:**
- Agregar `error` al objeto pasado en `onUpdate`
- En `HoyView`, mostrar error si `assistantError && !isGenerating`

## 8. Conclusión

### 8.1 Estados Correctamente Manejados

- ✅ ProactiveAssistant maneja correctamente respuestas 200 con payload vacío
- ✅ ProactiveAssistant cierra spinner con éxito parcial
- ✅ No hay bucles de re-fetch identificados
- ✅ Dependencias de useEffect son estables

### 8.2 Problemas Identificados

- ❌ Sección escenarios no distingue entre "generando" y "completado sin datos"
- ❌ Falta manejo de error en sección escenarios
- ⚠️ Mensaje "Generando escenarios..." se muestra indefinidamente en algunos casos

### 8.3 Acciones Requeridas

1. **Alta prioridad:** Corregir renderizado de sección escenarios para distinguir estados
2. **Media prioridad:** Agregar manejo de error en sección escenarios
3. **Baja prioridad:** Mejorar mensajes de estado vacío

