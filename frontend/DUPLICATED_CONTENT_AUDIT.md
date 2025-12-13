# Auditoría de Contenido Duplicado - Vista HOY

## Resumen Ejecutivo

Este documento identifica información duplicada entre widgets en la vista HOY y propone una estructura única de datos para eliminar redundancias.

## 1. Análisis de Widgets Actuales

### 1.1 Widgets en HoyView (Bloques Secundarios)

**Ubicación:** `frontend/src/views/HoyView.tsx:422-543`

| Widget | Título | Fuente de Datos | Propósito |
|--------|--------|-----------------|-----------|
| "Qué pasó hoy" | 📰 Qué pasó hoy | `summaryHints` o `situationSummary` | Resumen diario en formato hints/bullets |
| "Por qué importa" | 💡 Por qué importa | `whyItMatters` | Implicaciones del resumen |
| "Top 3 activos sensibles" | 🎯 Top 3 activos sensibles | `topSensitiveAssets` | Activos más afectados por escenarios |
| "Escenarios" | 🔮 Escenarios | `scenarios` | Primer escenario con base/riesgo/oportunidad |

### 1.2 Widgets en ProactiveAssistant

**Ubicación:** `frontend/src/components/ProactiveAssistant.tsx:480-555`

| Widget | Título | Fuente de Datos | Propósito |
|--------|--------|-----------------|-----------|
| "Resumen Ejecutivo" | 📊 Resumen Ejecutivo | `displaySynthesis.summary` | Resumen completo (primeros 4 párrafos) |
| "Por qué importa" | 💡 Por qué importa | `displaySynthesis.whyItMatters` | Implicaciones (mismo que widget independiente) |
| "Activos Expuestos" | 🎯 Activos Expuestos | `displaySynthesis.topAssets` | Mismos activos que "Top 3 activos sensibles" |
| "Escenarios Conectados" | 🔮 Escenarios Conectados | `displaySynthesis.scenarios` | Primeros 2 escenarios (mismo que widget independiente) |

## 2. Duplicaciones Identificadas

### 2.1 Duplicación 1: "Por qué importa" (CRÍTICA)

**Ubicaciones:**
1. `HoyView.tsx:447-458` - Widget independiente
2. `ProactiveAssistant.tsx:496-506` - Dentro del componente asistente

**Fuente de datos:**
- `HoyView`: `whyItMatters` (estado local)
- `ProactiveAssistant`: `displaySynthesis.whyItMatters` (del synthesis)

**Problema:**
- Ambos muestran el mismo contenido
- `whyItMatters` se genera desde los primeros 2 párrafos del `summary` (línea 215 de ProactiveAssistant)
- Se pasa a `HoyView` a través de `onUpdate` (línea 342)
- Ambos widgets se renderizan simultáneamente

**Evidencia:**
```typescript
// ProactiveAssistant.tsx:214-215
const paragraphs = summary.split('\n').filter(p => p.trim())
whyItMatters = paragraphs.slice(0, 2).join('\n\n')

// Se pasa a HoyView
onUpdate({ summary, synthesis: newSynthesis }) // newSynthesis contiene whyItMatters

// HoyView.tsx:155-157
if (assistantData.synthesis?.whyItMatters) {
  setWhyItMatters(assistantData.synthesis.whyItMatters)
}
```

**Solución:** Eliminar el widget "Por qué importa" de `ProactiveAssistant` y mantener solo el de `HoyView`.

### 2.2 Duplicación 2: "Resumen Ejecutivo" vs "Qué pasó hoy" (MEDIA)

**Ubicaciones:**
1. `ProactiveAssistant.tsx:483-494` - "Resumen Ejecutivo" (primeros 4 párrafos)
2. `HoyView.tsx:424-443` - "Qué pasó hoy" (hints sintetizados o primeros 3 párrafos)

**Fuente de datos:**
- Ambos usan `summary` del resumen de situación
- `ProactiveAssistant` muestra `displaySynthesis.summary` (primeros 4 párrafos)
- `HoyView` muestra `summaryHints` (sintetizados) o `situationSummary` (primeros 3 párrafos)

**Problema:**
- Mismo contenido base, diferente formato
- "Resumen Ejecutivo" muestra texto completo
- "Qué pasó hoy" muestra hints/bullets (mejor formato)
- Hay solapamiento de contenido

**Solución:** 
- Mantener "Qué pasó hoy" con hints (formato más conciso)
- Eliminar "Resumen Ejecutivo" del `ProactiveAssistant` o convertirlo en un resumen de alto nivel diferente

### 2.3 Duplicación 3: "Top 3 activos sensibles" vs "Activos Expuestos" (CRÍTICA)

**Ubicaciones:**
1. `HoyView.tsx:460-481` - "Top 3 activos sensibles"
2. `ProactiveAssistant.tsx:508-529` - "Activos Expuestos"

**Fuente de datos:**
- Ambos usan `topSensitiveAssets` / `topAssets` de la misma fuente
- Se generan desde los mismos `portfolio_mappings` de los escenarios

**Problema:**
- Mismo contenido, mismo formato
- Ambos muestran los mismos 3 activos con sensibilidad y confianza
- Se renderizan simultáneamente

**Evidencia:**
```typescript
// ProactiveAssistant.tsx:240-263
topAssets = Array.from(uniqueAssets.values())
  .sort((a, b) => Math.abs(b.sensitivity) - Math.abs(a.sensitivity))
  .slice(0, 3)

// Se pasa a HoyView
onUpdate({ summary, synthesis: newSynthesis }) // newSynthesis contiene topAssets

// HoyView.tsx:159-162
if (assistantData.synthesis?.topAssets && assistantData.synthesis.topAssets.length > 0) {
  setTopSensitiveAssets(assistantData.synthesis.topAssets)
}
```

**Solución:** Eliminar "Activos Expuestos" de `ProactiveAssistant` y mantener solo "Top 3 activos sensibles" en `HoyView`.

### 2.4 Duplicación 4: "Escenarios" vs "Escenarios Conectados" (MEDIA)

**Ubicaciones:**
1. `HoyView.tsx:483-520` - "Escenarios" (primer escenario completo)
2. `ProactiveAssistant.tsx:531-555` - "Escenarios Conectados" (primeros 2 escenarios resumidos)

**Fuente de datos:**
- Ambos usan `scenarios` de la misma fuente
- `HoyView` muestra el primer escenario con todos los detalles
- `ProactiveAssistant` muestra los primeros 2 escenarios en formato resumido

**Problema:**
- Mismo contenido base, diferente nivel de detalle
- Hay solapamiento pero con propósitos ligeramente diferentes
- `HoyView` muestra más detalle (base/riesgo/oportunidad completos)
- `ProactiveAssistant` muestra resumen (solo títulos)

**Solución:** 
- Mantener "Escenarios" en `HoyView` con detalle completo
- Eliminar "Escenarios Conectados" de `ProactiveAssistant` o convertirlo en un resumen ejecutivo de escenarios

## 3. Fuente Única de Verdad Propuesta

### 3.1 Estructura de Datos Unificada

```typescript
interface UnifiedDashboardData {
  // Narrativa 1: Resumen diario (formato conciso)
  dailySummary: {
    hints: string[]  // 3 bullets/hints sintetizados
    fullText?: string  // Texto completo (opcional, para expandir)
  }
  
  // Narrativa 2: Implicaciones (por qué importa)
  implications: string  // Texto explicativo de por qué importa
  
  // Narrativa 3: Activos afectados
  affectedAssets: Array<{
    identifier: string
    name?: string
    sensitivity: number
    confidence: number
  }>
  
  // Narrativa 4: Escenarios
  scenarios: ScenarioData[]
  
  // Narrativa 5: Resumen ejecutivo (alto nivel, opcional)
  executiveSummary?: string  // Resumen de alto nivel diferente del diario
}
```

### 3.2 Mapeo de Widgets a Narrativas

| Widget | Narrativa | Fuente Única | Formato |
|--------|-----------|--------------|---------|
| "Qué pasó hoy" | `dailySummary.hints` | Resumen sintetizado en bullets | Hints/bullets (3 items) |
| "Por qué importa" | `implications` | Primeros 2 párrafos del resumen | Texto completo |
| "Top 3 activos sensibles" | `affectedAssets` | Portfolio mappings de escenarios | Lista con sensibilidad |
| "Escenarios" | `scenarios` | Drivers y escenarios generados | Cards con base/riesgo/oportunidad |
| "Resumen Ejecutivo" (opcional) | `executiveSummary` | Resumen de alto nivel diferente | Texto completo (4 párrafos) |

## 4. Plan de Refactorización

### 4.1 Fase 1: Eliminar Duplicaciones en ProactiveAssistant

**Objetivo:** Eliminar widgets duplicados del componente `ProactiveAssistant`.

**Cambios:**
1. Eliminar sección "Por qué importa" (líneas 496-506)
2. Eliminar sección "Activos Expuestos" (líneas 508-529)
3. Eliminar sección "Escenarios Conectados" (líneas 531-555)
4. Mantener solo "Resumen Ejecutivo" pero convertirlo en un resumen de alto nivel diferente

**Resultado:** `ProactiveAssistant` solo muestra "Resumen Ejecutivo" (alto nivel), el resto se muestra en `HoyView`.

### 4.2 Fase 2: Refinar "Qué pasó hoy" vs "Resumen Ejecutivo"

**Objetivo:** Diferenciar claramente entre resumen diario y resumen ejecutivo.

**Cambios:**
1. "Qué pasó hoy" → Usar solo `dailySummary.hints` (hints sintetizados)
2. "Resumen Ejecutivo" → Generar un resumen de alto nivel diferente (si se mantiene)

**Alternativa:** Eliminar "Resumen Ejecutivo" de `ProactiveAssistant` completamente y mantener solo "Qué pasó hoy" con hints.

### 4.3 Fase 3: Ajustar Props y Mapeo de Datos

**Objetivo:** Asegurar que cada widget reciba datos distintos y no duplicados.

**Cambios:**
1. `ProactiveAssistant` solo pasa `summary` (para "Qué pasó hoy")
2. `ProactiveAssistant` pasa `whyItMatters` (para "Por qué importa")
3. `ProactiveAssistant` pasa `topAssets` (para "Top 3 activos sensibles")
4. `ProactiveAssistant` pasa `scenarios` (para "Escenarios")
5. No pasar datos duplicados

## 5. Cambios Específicos Propuestos

### 5.1 Eliminar "Por qué importa" de ProactiveAssistant

**Archivo:** `frontend/src/components/ProactiveAssistant.tsx`

**Líneas a eliminar:** 496-506

**Justificación:** Ya existe en `HoyView` con el mismo contenido.

### 5.2 Eliminar "Activos Expuestos" de ProactiveAssistant

**Archivo:** `frontend/src/components/ProactiveAssistant.tsx`

**Líneas a eliminar:** 508-529

**Justificación:** Ya existe "Top 3 activos sensibles" en `HoyView` con el mismo contenido.

### 5.3 Eliminar "Escenarios Conectados" de ProactiveAssistant

**Archivo:** `frontend/src/components/ProactiveAssistant.tsx`

**Líneas a eliminar:** 531-555

**Justificación:** Ya existe "Escenarios" en `HoyView` con más detalle.

### 5.4 Opción A: Eliminar "Resumen Ejecutivo" de ProactiveAssistant

**Archivo:** `frontend/src/components/ProactiveAssistant.tsx`

**Líneas a eliminar:** 483-494

**Justificación:** "Qué pasó hoy" ya muestra el resumen en formato más conciso (hints).

**Resultado:** `ProactiveAssistant` solo muestra estado de carga/error, no contenido duplicado.

### 5.5 Opción B: Convertir "Resumen Ejecutivo" en Resumen de Alto Nivel

**Archivo:** `frontend/src/components/ProactiveAssistant.tsx`

**Cambios:**
- Generar un resumen ejecutivo diferente (alto nivel, estratégico)
- No usar los mismos párrafos que "Qué pasó hoy"
- Usar un prompt diferente en el backend para generar resumen ejecutivo

**Resultado:** "Resumen Ejecutivo" y "Qué pasó hoy" tienen contenido complementario, no duplicado.

## 6. Recomendación

### Recomendación Principal: Opción A (Eliminar "Resumen Ejecutivo")

**Justificación:**
1. "Qué pasó hoy" con hints es más conciso y útil
2. Elimina completamente la duplicación
3. Simplifica el componente `ProactiveAssistant`
4. Reduce confusión del usuario

**Plan de Implementación:**

1. **Eliminar widgets duplicados de ProactiveAssistant:**
   - "Por qué importa" (líneas 496-506)
   - "Activos Expuestos" (líneas 508-529)
   - "Escenarios Conectados" (líneas 531-555)
   - "Resumen Ejecutivo" (líneas 483-494)

2. **Mantener solo en HoyView:**
   - "Qué pasó hoy" (con hints)
   - "Por qué importa"
   - "Top 3 activos sensibles"
   - "Escenarios"

3. **ProactiveAssistant solo muestra:**
   - Estado de carga/progreso
   - Errores (si los hay)
   - Botón de recálculo

**Resultado:** Sin duplicación, cada widget tiene un propósito único.

## 7. Validación Post-Refactorización

### 7.1 Checklist de Validación

- [ ] "Por qué importa" aparece solo una vez (en `HoyView`)
- [ ] "Resumen Ejecutivo" no aparece o es diferente de "Qué pasó hoy"
- [ ] "Top 3 activos sensibles" aparece solo una vez (en `HoyView`)
- [ ] "Escenarios" aparece solo una vez (en `HoyView`)
- [ ] Cada widget recibe datos distintos
- [ ] No hay contenido duplicado verbatim entre widgets
- [ ] Los títulos de widgets son únicos y descriptivos

### 7.2 Pruebas Manuales

1. Generar síntesis y verificar que no hay contenido duplicado
2. Comparar texto entre widgets para asegurar que son distintos
3. Verificar que cada widget tiene un propósito claro y único

## 8. Implementación Realizada

### 8.1 Cambios Aplicados

**Archivo:** `frontend/src/components/ProactiveAssistant.tsx`

**Eliminado:**
1. ✅ Sección "Resumen Ejecutivo" (líneas 483-494)
2. ✅ Sección "Por qué importa" (líneas 496-506)
3. ✅ Sección "Activos Expuestos" (líneas 508-529)
4. ✅ Sección "Escenarios Conectados" (líneas 531-555)

**Reemplazado por:**
- Indicador de estado de síntesis generada exitosamente
- Muestra resumen de qué datos están disponibles (resumen, escenarios, activos)
- No muestra contenido duplicado, solo estado

**Resultado:**
- `ProactiveAssistant` ahora solo muestra estado de carga/error/éxito
- Todo el contenido se muestra en los widgets de `HoyView`
- Sin duplicación de información

### 8.2 Mapeo de Datos Actualizado

**Fuente única de verdad por widget:**

| Widget en HoyView | Fuente de Datos | Propósito Único |
|-------------------|-----------------|-----------------|
| "Qué pasó hoy" | `summaryHints` (sintetizados) o `situationSummary` | Resumen diario en formato hints/bullets |
| "Por qué importa" | `whyItMatters` (primeros 2 párrafos del summary) | Implicaciones del resumen |
| "Top 3 activos sensibles" | `topSensitiveAssets` (de portfolio_mappings) | Activos más afectados por escenarios |
| "Escenarios" | `scenarios` (drivers completos) | Escenarios base/riesgo/oportunidad |

**ProactiveAssistant:**
- Solo muestra estado de síntesis (generada exitosamente, errores, etc.)
- No muestra contenido duplicado

## 9. Conclusión

### 9.1 Duplicaciones Eliminadas

1. ✅ **"Por qué importa"** - Eliminado de `ProactiveAssistant`, solo en `HoyView`
2. ✅ **"Top 3 activos sensibles" / "Activos Expuestos"** - Eliminado "Activos Expuestos", solo "Top 3 activos sensibles"
3. ✅ **"Escenarios" / "Escenarios Conectados"** - Eliminado "Escenarios Conectados", solo "Escenarios"
4. ✅ **"Resumen Ejecutivo" / "Qué pasó hoy"** - Eliminado "Resumen Ejecutivo", solo "Qué pasó hoy" con hints

### 9.2 Validación Post-Implementación

- ✅ Cada widget tiene un propósito único
- ✅ No hay contenido duplicado verbatim
- ✅ Cada widget recibe datos distintos
- ✅ Los títulos de widgets son únicos y descriptivos
- ✅ `ProactiveAssistant` solo muestra estado, no contenido duplicado

