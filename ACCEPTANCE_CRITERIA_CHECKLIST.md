# Checklist de Criterios de Aceptación

## ✅ 1. Botón visible en widget de detalle

**Estado:** ✅ COMPLETADO

**Implementación:**
- Botón "📈 Actualizar Precio/Volumen" visible en `ActivoView.tsx` (línea 244-249)
- Ubicado en `details-header` junto al selector de período
- Deshabilitado durante carga (`isLoadingPrice`) o si no hay símbolo
- Tooltip descriptivo: "Actualizar precio y volumen desde Yahoo Finance"

**Archivos:**
- `frontend/src/views/ActivoView.tsx` (líneas 229-249)

---

## ✅ 2. Obtención de precios/volumen con estados de carga y errores

**Estado:** ✅ COMPLETADO

**Implementación:**
- Función `handleLoadPriceData` maneja la obtención de datos (líneas 100-118)
- Estados implementados:
  - `isLoadingPrice`: Muestra spinner durante carga
  - `priceError`: Muestra mensaje de error con botón de reintento
  - `priceData`: Almacena datos obtenidos exitosamente
- Manejo de errores:
  - Captura errores de red/API
  - Muestra mensaje descriptivo al usuario
  - Botón "Reintentar" disponible
- Selector de período (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y) para controlar rango de datos

**Archivos:**
- `frontend/src/views/ActivoView.tsx` (líneas 100-118, 280-310)

---

## ✅ 3. Gráfico actualizado sin recargar página con fallback seguro

**Estado:** ✅ COMPLETADO

**Implementación:**
- Gráfico se actualiza dinámicamente cuando `priceData` cambia
- No requiere recarga de página (React state management)
- Fallback seguro implementado:
  - Si `priceError`: Muestra mensaje de error con botón de reintento
  - Si `priceData.data.length === 0`: Muestra mensaje "No se encontraron datos"
  - Si `isLoadingPrice`: Muestra spinner de carga
- Limpieza automática de datos cuando cambia el activo seleccionado (useEffect línea 120-123)

**Archivos:**
- `frontend/src/views/ActivoView.tsx` (líneas 280-310, 120-123)
- `frontend/src/components/PriceChart.tsx` (componente completo)

---

## ✅ 4. Marcadores buy/sell basados en SMA 5/15, RSI y MACD

**Estado:** ✅ COMPLETADO

**Implementación:**
- Función `detectSignals` detecta señales de trading (líneas 220-259):
  - **SMA 5/15 Cross**: Buy cuando SMA5 cruza por encima de SMA15, Sell cuando cruza por debajo
  - **RSI Overbought/Oversold**: Buy cuando RSI < 30, Sell cuando RSI > 70
  - **MACD Signal Cross**: Buy cuando MACD cruza por encima de Signal, Sell cuando cruza por debajo
- Señales se dibujan como flechas en el gráfico (líneas 500-550)
- Cada señal incluye: tipo (buy/sell), razón, precio, fecha

**Archivos:**
- `frontend/src/components/PriceChart.tsx` (líneas 220-259, 500-550)

---

## ✅ 5. Indicadores activables/desactivables

**Estado:** ✅ COMPLETADO

**Implementación:**
- Estados para cada indicador (líneas 41-47):
  - `showSMA5`, `showSMA15`, `showSMA50`, `showEMA20`, `showRSI`, `showMACD`, `showSignals`
- Leyenda interactiva con checkboxes (líneas 650-750):
  - Cada indicador tiene checkbox para activar/desactivar
  - Contador de señales detectadas
  - Resumen de señales (últimas 5)
- Renderizado condicional en canvas basado en estados `show*` (líneas 366-369, 400-450)

**Archivos:**
- `frontend/src/components/PriceChart.tsx` (líneas 41-47, 366-369, 400-450, 650-750)

---

## ✅ 6. Salida de datos técnicos para asistente IA

**Estado:** ✅ COMPLETADO

**Implementación:**
- Función `formatTechnicalDataForAI` genera formato compacto (líneas 262-296)
- Datos expuestos en múltiples formas:
  1. **Callback `onTechnicalDataReady`**: Pasa datos estructurados al componente padre
  2. **`window.lastTechnicalData`**: Disponible globalmente para acceso externo
  3. **Utilidad `technical-data-export.ts`**: Funciones helper para obtener y formatear datos
- Estructura de datos documentada:
  - Interface `TechnicalDataExport` en `technical-data-export.ts`
  - Incluye: símbolo, precio actual, indicadores (SMA5, SMA15, RSI, MACD), señales, resumen formateado
- Formato compacto incluye:
  - Precio actual y valores de indicadores
  - Últimas 5 señales con razón y precio
  - Timestamp para referencia temporal

**Archivos:**
- `frontend/src/components/PriceChart.tsx` (líneas 262-296, 344-362)
- `frontend/src/utils/technical-data-export.ts` (completo)
- `frontend/src/views/ActivoView.tsx` (líneas 329-333)

---

## ✅ 7. Flujo de prompts optimizado

**Estado:** ✅ COMPLETADO

**Implementación:**

### 7.1 Separación contexto fijo/payload variable
- **`PromptTemplateService`**: Separa contextos del sistema (fijos) de datos variables
- Contextos fijos definidos en `SYSTEM_CONTEXTS`:
  - `situation_summary`, `scenario_generation`, `portfolio_analysis`, `technical_analysis`
- Plantillas construyen prompts combinando contexto fijo + datos truncados

### 7.2 Control de longitud/tokens
- Límites configurables en `LENGTH_LIMITS`:
  - `news_item`: 500 caracteres
  - `news_list`: 10 noticias máximo
  - `price_points`: 50 puntos máximo
  - `total_prompt_chars`: 8000 caracteres totales
- Truncamiento automático:
  - Noticias: `truncate_news_list()` limita cantidad y longitud
  - Precios: `truncate_price_data()` mantiene últimos N puntos
  - Señales: `truncate_signals()` mantiene últimas N señales
- Validación de longitud antes de enviar a OpenAI
- Truncamiento agresivo si aún excede límites

### 7.3 Caché de datos estáticos
- **`PromptCacheService`**: Cachea respuestas basadas en contexto estático
- TTLs configurables:
  - `static`: 24 horas
  - `dynamic`: 5 minutos
  - `scenarios`: 30 minutos
  - `summary`: 10 minutos
- Invalidación automática cuando cambian datos variables (hash comparison)
- Limpieza automática de entradas expiradas

### 7.4 Condiciones de salida explícitas
- Validación de datos mínimos antes de llamar a API
- Validación de longitud de prompt (cancela si excede límites)
- Verificación de caché (retorna sin llamar si hay respuesta válida)
- Mensajes claros explicando por qué no se hace la llamada

### 7.5 Logging de tokens
- **`TokenLogger`**: Registra tokens por cada paso
- Calcula costo estimado en USD
- Resúmenes por paso y sesión total
- Endpoints para consultar estadísticas:
  - `GET /api/token-stats`: Estadísticas de tokens
  - `GET /api/cache-stats`: Estadísticas de caché
  - `POST /api/cache/clear`: Limpiar caché

**Archivos:**
- `backend/app/services/prompt_template_service.py` (completo)
- `backend/app/services/prompt_cache_service.py` (completo)
- `backend/app/services/token_logger.py` (completo)
- `backend/app/services/prompt_optimization_service.py` (completo)
- `backend/app/services/situation_summary_service.py` (actualizado)
- `backend/app/services/scenario_generation_service.py` (actualizado)
- `backend/app/main.py` (endpoints agregados)

---

## Resumen de Estado

| Criterio | Estado | Archivos Principales |
|----------|--------|---------------------|
| 1. Botón visible | ✅ | `ActivoView.tsx` |
| 2. Estados carga/error | ✅ | `ActivoView.tsx` |
| 3. Gráfico dinámico + fallback | ✅ | `ActivoView.tsx`, `PriceChart.tsx` |
| 4. Marcadores buy/sell | ✅ | `PriceChart.tsx` |
| 5. Indicadores toggleables | ✅ | `PriceChart.tsx` |
| 6. Salida datos técnicos IA | ✅ | `PriceChart.tsx`, `technical-data-export.ts` |
| 7. Flujo prompts optimizado | ✅ | Múltiples servicios backend |

**Estado General:** ✅ **TODOS LOS CRITERIOS COMPLETADOS**
