# Análisis de Requisitos Mínimos de Datos - Carga Inicial

## Resumen Ejecutivo

Este documento analiza los requisitos mínimos de datos (noticias y activos de cartera) para que la página inicial renderice correctamente sin quedar bloqueada esperando datos.

## 1. Endpoints del Backend - Respuestas con Datos Vacíos

### 1.1 GET /api/news

**Ubicación:** `backend/app/routers/news.py:167-223`

**Comportamiento:**
- ✅ Retorna `200 OK` con lista vacía si no hay noticias
- ✅ Estructura: `{ items: [], total: 0 }`
- ✅ No lanza error HTTP, solo retorna lista vacía

**Código relevante:**
```python
total = db.query(NewsItem).count()
# ... procesamiento ...
return NewsListResponse(
    items=paginated_items,  # Puede ser []
    total=total  # Puede ser 0
)
```

**Conclusión:** ✅ El endpoint maneja correctamente listas vacías.

### 1.2 GET /api/news/summary

**Ubicación:** `backend/app/routers/news.py:341-408`

**Comportamiento:**
- ✅ Retorna `200 OK` con `has_content=False` si no hay noticias
- ✅ Estructura: `{ summary: "", meta_summary: "", has_content: false, news_count: 0, ... }`
- ✅ No lanza error HTTP, retorna respuesta vacía válida

**Código relevante:**
```python
if not news_items:
    return SituationSummaryResponse(
        summary="",
        meta_summary="",
        batch_summaries=[],
        news_count=0,
        recent_news_count=0,
        batches_processed=0,
        total_prompt_tokens=0,
        generated_at=datetime.now(timezone.utc).isoformat(),
        has_content=False,  # ← Clave: indica que no hay contenido
        tokens_used=None
    )
```

**Conclusión:** ✅ El endpoint maneja correctamente la ausencia de noticias.

### 1.3 GET /api/portfolio

**Ubicación:** `backend/app/routers/portfolio.py:78-98`

**Comportamiento:**
- ✅ Retorna `200 OK` con lista vacía si no hay items de cartera
- ✅ Estructura: `{ items: [], total: 0 }`
- ✅ No lanza error HTTP, solo retorna lista vacía

**Código relevante:**
```python
total = db.query(PortfolioItem).count()
items = db.query(PortfolioItem).order_by(desc(PortfolioItem.updated_at)).all()

return PortfolioListResponse(
    items=[...],  # Puede ser []
    total=total  # Puede ser 0
)
```

**Conclusión:** ✅ El endpoint maneja correctamente listas vacías.

### 1.4 POST /api/scenarios

**Ubicación:** `backend/app/routers/scenarios.py:25-210`

**Comportamiento:**
- ❌ **Lanza `400 Bad Request`** si no hay noticias
- ❌ Mensaje: `"No se encontraron noticias para analizar."`
- ⚠️ **No retorna respuesta vacía**, lanza excepción HTTP

**Código relevante:**
```python
if not news_items:
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="No se encontraron noticias para analizar."
    )
```

**Conclusión:** ❌ El endpoint **NO maneja** la ausencia de noticias. Requiere al menos 1 noticia.

**Requisito mínimo:** Al menos 1 noticia en la base de datos.

## 2. Comportamiento del Frontend con Datos Vacíos

### 2.1 ProactiveAssistant - Resumen

**Ubicación:** `frontend/src/components/ProactiveAssistant.tsx:211-234`

**Comportamiento con respuesta vacía:**
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
- ✅ Si `has_content === false`, marca `hasPartialData = true` pero continúa
- ✅ No bloquea el render, permite mostrar escenarios si están disponibles

**Conclusión:** ✅ Maneja correctamente respuestas vacías.

### 2.2 ProactiveAssistant - Escenarios

**Ubicación:** `frontend/src/components/ProactiveAssistant.tsx:237-267`

**Comportamiento con respuesta vacía:**
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
- ✅ Si `drivers === []` o `undefined`, marca `hasPartialData = true` pero continúa
- ⚠️ **Problema:** Si el backend lanza `400 Bad Request` (sin noticias), `scenariosData.status === 'rejected'`
- ✅ En ese caso, se maneja en el bloque `else` y no bloquea el render

**Conclusión:** ✅ Maneja correctamente respuestas vacías o errores.

### 2.3 ProactiveAssistant - Verificación de Datos Completamente Vacíos

**Ubicación:** `frontend/src/components/ProactiveAssistant.tsx:269-291`

**Comportamiento:**
```typescript
if (!summary && scenarios.length === 0) {
  throw new Error(`No se pudo generar síntesis. ${errorDetails.join('; ')}`)
}
```

**Análisis:**
- ✅ Si ambos están vacíos, lanza error
- ✅ El error se captura y se muestra al usuario
- ✅ `isLoading` se resetea a `false` (línea 382)
- ✅ Se muestra mensaje de error + último resultado válido (si existe)

**Conclusión:** ✅ Maneja correctamente la ausencia total de datos.

### 2.4 HoyView - Sección "Qué pasó hoy"

**Ubicación:** `frontend/src/views/HoyView.tsx:424-443`

**Comportamiento:**
```typescript
{summaryHints.length > 0 ? (
  <div className="summary-hints">...</div>
) : situationSummary ? (
  <div className="summary-text">...</div>
) : (
  <p className="empty-state">No hay noticias recientes</p>
)}
```

**Análisis:**
- ✅ Muestra estado vacío si no hay datos
- ✅ No bloquea el render
- ✅ Mensaje claro: "No hay noticias recientes"

**Conclusión:** ✅ Maneja correctamente la ausencia de datos.

### 2.5 HoyView - Sección Escenarios

**Ubicación:** `frontend/src/views/HoyView.tsx:432-468`

**Comportamiento:**
```typescript
{scenarios.length > 0 ? (
  <div className="scenarios-list">...</div>
) : (
  <p className="empty-state">Generando escenarios...</p>
)}
```

**Análisis:**
- ❌ **Problema:** No distingue entre "generando" y "completado sin datos"
- ❌ Muestra "Generando escenarios..." incluso cuando la generación completó sin escenarios
- ⚠️ Si el backend lanza `400 Bad Request` (sin noticias), el frontend debería mostrar un mensaje de error, pero actualmente muestra "Generando escenarios..."

**Conclusión:** ❌ No maneja correctamente la ausencia de escenarios.

### 2.6 HoyView - loadHoyData (Fallback)

**Ubicación:** `frontend/src/views/HoyView.tsx:224-254`

**Comportamiento con escenarios vacíos:**
```typescript
const [summaryData, portfolioData, scenariosData] = await Promise.allSettled([...])

if (scenariosData.status === 'fulfilled') {
  setScenarios(scenariosData.value.drivers || [])
  // ...
}
```

**Análisis:**
- ✅ Si `scenariosData.status === 'rejected'`, no actualiza `scenarios` (mantiene `[]`)
- ✅ Si `scenariosData.status === 'fulfilled'` pero `drivers === []`, establece `scenarios = []`
- ✅ No bloquea el render, continúa con otros datos

**Conclusión:** ✅ Maneja correctamente respuestas vacías o errores.

## 3. Migraciones y Seeders

### 3.1 Migraciones

**Ubicación:** `backend/app/migrations.py`

**Funciones de migración:**
1. `add_standardized_data_column()` - Agrega columna `standardized_data`
2. `add_score_columns()` - Agrega columnas `score`, `score_components`, `is_obsolete`
3. `add_sectors_and_catalog_tables()` - Crea tablas de sectores y catálogo
4. `init_catalog_data()` - Inicializa catálogo si está vacío

**Análisis:**
- ✅ Las migraciones crean la estructura de la BD
- ⚠️ **NO hay seeder** que pueble noticias iniciales
- ⚠️ **NO hay seeder** que pueble activos de cartera iniciales
- ✅ `init_catalog_data()` solo inicializa catálogo de sectores/activos, no noticias ni cartera

**Conclusión:** ❌ No hay seeders para datos iniciales. La BD puede estar completamente vacía.

### 3.2 Dependencias de Seed/Migración

**Estado actual:**
- ✅ Migraciones crean estructura de BD
- ❌ No hay seeders para noticias
- ❌ No hay seeders para cartera
- ⚠️ La aplicación puede iniciar con 0 noticias y 0 activos

**Impacto:**
- Si hay 0 noticias: `/api/scenarios` lanza `400 Bad Request`
- Si hay 0 noticias: `/api/news/summary` retorna `has_content=false`
- Si hay 0 activos: `/api/portfolio` retorna lista vacía (no hay problema)

## 4. Requisitos Mínimos de Datos

### 4.1 Para Renderizar la Página Inicial

| Componente | Requisito Mínimo | Estado Actual |
|------------|------------------|---------------|
| **HoyView (UI general)** | Ninguno | ✅ Renderiza sin datos |
| **"Qué pasó hoy"** | 0 noticias (muestra estado vacío) | ✅ Funciona |
| **"Por qué importa"** | 0 noticias (muestra estado vacío) | ✅ Funciona |
| **"Top 3 activos sensibles"** | 0 activos (muestra estado vacío) | ✅ Funciona |
| **Asistente IA Proactivo** | 0 noticias (muestra error o estado vacío) | ✅ Funciona |
| **Escenarios** | ⚠️ **Al menos 1 noticia** | ❌ Falla si 0 noticias |

### 4.2 Para Generar Escenarios

**Requisito absoluto:** Al menos 1 noticia en la base de datos.

**Razón:** El endpoint `/api/scenarios` lanza `400 Bad Request` si no hay noticias.

**Código:** `backend/app/routers/scenarios.py:63-67`

### 4.3 Para Generar Resumen de Situación

**Requisito:** 0 noticias es válido (retorna `has_content=false`).

**Razón:** El endpoint `/api/news/summary` retorna respuesta vacía válida si no hay noticias.

**Código:** `backend/app/routers/news.py:355-368`

### 4.4 Para Mostrar Activos Sensibles

**Requisito:** 0 activos es válido (muestra estado vacío).

**Razón:** El endpoint `/api/portfolio` retorna lista vacía sin error.

**Código:** `backend/app/routers/portfolio.py:86-92`

## 5. Simulación de Respuestas Vacías

### 5.1 Escenario 1: 0 Noticias, 0 Activos

**Backend:**
- `GET /api/news` → `200 OK` con `{ items: [], total: 0 }`
- `GET /api/news/summary` → `200 OK` con `{ has_content: false, summary: "", ... }`
- `GET /api/portfolio` → `200 OK` con `{ items: [], total: 0 }`
- `POST /api/scenarios` → `400 Bad Request` con `"No se encontraron noticias para analizar."`

**Frontend:**
- ✅ HoyView renderiza correctamente
- ✅ "Qué pasó hoy" muestra "No hay noticias recientes"
- ✅ "Por qué importa" muestra estado vacío
- ✅ "Top 3 activos" muestra "No hay activos sensibles identificados"
- ⚠️ **Escenarios:** Muestra "Generando escenarios..." indefinidamente (problema)
- ✅ Asistente IA: Muestra error "No se pudo generar síntesis. Escenarios: No se encontraron noticias para analizar."

**Conclusión:** ⚠️ La sección de escenarios no maneja correctamente el error 400.

### 5.2 Escenario 2: 1 Noticia, 0 Activos

**Backend:**
- `GET /api/news` → `200 OK` con `{ items: [{...}], total: 1 }`
- `GET /api/news/summary` → `200 OK` con `{ has_content: true, summary: "...", ... }`
- `GET /api/portfolio` → `200 OK` con `{ items: [], total: 0 }`
- `POST /api/scenarios` → `200 OK` con `{ drivers: [...], total_drivers: 1-2, ... }`

**Frontend:**
- ✅ Todo renderiza correctamente
- ✅ Escenarios se generan (aunque puede tardar 20-40s)

**Conclusión:** ✅ Funciona correctamente con 1 noticia.

### 5.3 Escenario 3: 0 Noticias, 5 Activos

**Backend:**
- `GET /api/news` → `200 OK` con `{ items: [], total: 0 }`
- `GET /api/news/summary` → `200 OK` con `{ has_content: false, ... }`
- `GET /api/portfolio` → `200 OK` con `{ items: [{...}, ...], total: 5 }`
- `POST /api/scenarios` → `400 Bad Request` con `"No se encontraron noticias para analizar."`

**Frontend:**
- ✅ HoyView renderiza correctamente
- ✅ "Top 3 activos" muestra activos (aunque sin sensibilidad de escenarios)
- ⚠️ **Escenarios:** Muestra "Generando escenarios..." indefinidamente (problema)

**Conclusión:** ⚠️ Mismo problema con escenarios.

## 6. Problemas Identificados

### 6.1 Problema 1: Sección Escenarios No Maneja Error 400

**Ubicación:** `frontend/src/views/HoyView.tsx:432-468`

**Problema:**
- Si `/api/scenarios` retorna `400 Bad Request` (sin noticias), el frontend no muestra el error
- Muestra "Generando escenarios..." indefinidamente
- No distingue entre "generando" y "error"

**Solución propuesta:**
1. Pasar estado de error desde `ProactiveAssistant` a `HoyView`
2. Mostrar mensaje de error en la sección de escenarios si `error && !isGenerating`
3. Mostrar "No se generaron escenarios" si `!isGenerating && scenarios.length === 0 && !error`

### 6.2 Problema 2: Falta Seeder de Datos Iniciales

**Problema:**
- No hay seeder que pueble noticias iniciales
- No hay seeder que pueble activos de cartera iniciales
- La aplicación puede iniciar completamente vacía

**Solución propuesta:**
1. Crear seeder opcional que pueble 3-5 noticias de ejemplo
2. Crear seeder opcional que pueble 2-3 activos de ejemplo
3. Documentar cómo poblar datos iniciales manualmente

## 7. Precondiciones Mínimas Documentadas

### 7.1 Para Renderizar la Página Inicial

**Requisito:** Ninguno (la página renderiza sin datos)

**Componentes que funcionan sin datos:**
- ✅ HoyView (estructura general)
- ✅ "Qué pasó hoy" (muestra estado vacío)
- ✅ "Por qué importa" (muestra estado vacío)
- ✅ "Top 3 activos sensibles" (muestra estado vacío)
- ✅ Asistente IA Proactivo (muestra botón de generación)

**Componentes que requieren datos:**
- ⚠️ Escenarios: Requiere al menos 1 noticia (actualmente muestra "Generando..." indefinidamente si falla)

### 7.2 Para Generar Escenarios

**Requisito absoluto:** Al menos 1 noticia en la base de datos.

**Razón técnica:** El endpoint `/api/scenarios` lanza `400 Bad Request` si `news_items` está vacío.

**Código:** `backend/app/routers/scenarios.py:63-67`

### 7.3 Para Generar Resumen de Situación

**Requisito:** 0 noticias es válido (retorna `has_content=false`).

**Comportamiento:** El endpoint retorna respuesta vacía válida, no lanza error.

### 7.4 Para Mostrar Activos Sensibles

**Requisito:** 0 activos es válido (muestra estado vacío).

**Comportamiento:** El endpoint retorna lista vacía sin error.

## 8. Recomendaciones

### 8.1 Corrección Inmediata (Alta Prioridad)

**Problema:** Sección escenarios no maneja error 400

**Solución:**
1. Pasar estado de error desde `ProactiveAssistant` a `HoyView`
2. Mostrar mensaje apropiado en la sección de escenarios según estado

**Archivo:** `frontend/src/views/HoyView.tsx:432-468`

### 8.2 Mejora Adicional (Media Prioridad)

**Problema:** Falta seeder de datos iniciales

**Solución:**
1. Crear script `backend/app/scripts/seed_initial_data.py`
2. Poblar 3-5 noticias de ejemplo
3. Poblar 2-3 activos de ejemplo
4. Documentar cómo ejecutar el seeder

### 8.3 Mejora de UX (Baja Prioridad)

**Problema:** Mensajes de estado vacío podrían ser más informativos

**Solución:**
- Agregar botones de acción en estados vacíos (ej: "Agregar primera noticia")
- Mejorar mensajes para guiar al usuario

## 9. Conclusión

### 9.1 Requisitos Mínimos Confirmados

| Funcionalidad | Requisito Mínimo | Estado |
|---------------|------------------|--------|
| Renderizar página inicial | 0 noticias, 0 activos | ✅ Funciona |
| Generar resumen | 0 noticias (retorna vacío) | ✅ Funciona |
| Generar escenarios | **Al menos 1 noticia** | ⚠️ Falla si 0 noticias |
| Mostrar activos sensibles | 0 activos (muestra vacío) | ✅ Funciona |

### 9.2 Problemas Críticos

1. ❌ **Sección escenarios no maneja error 400** - Muestra "Generando..." indefinidamente
2. ⚠️ **Falta seeder de datos iniciales** - La aplicación puede iniciar completamente vacía

### 9.3 Acciones Requeridas

1. **Alta prioridad:** Corregir manejo de error en sección escenarios
2. **Media prioridad:** Crear seeder de datos iniciales
3. **Baja prioridad:** Mejorar mensajes de estado vacío

## 10. Evidencia de Comportamiento

### 10.1 Backend - Respuestas Vacías

**GET /api/news (0 noticias):**
```json
{
  "items": [],
  "total": 0
}
```
✅ Retorna 200 OK

**GET /api/news/summary (0 noticias):**
```json
{
  "summary": "",
  "meta_summary": "",
  "has_content": false,
  "news_count": 0,
  "recent_news_count": 0,
  ...
}
```
✅ Retorna 200 OK

**GET /api/portfolio (0 activos):**
```json
{
  "items": [],
  "total": 0
}
```
✅ Retorna 200 OK

**POST /api/scenarios (0 noticias):**
```json
{
  "detail": "No se encontraron noticias para analizar."
}
```
❌ Retorna 400 Bad Request

### 10.2 Frontend - Comportamiento con Datos Vacíos

**HoyView:**
- ✅ Renderiza correctamente
- ✅ Muestra estados vacíos apropiados
- ⚠️ Escenarios muestra "Generando..." indefinidamente si hay error

**ProactiveAssistant:**
- ✅ Maneja correctamente respuestas vacías
- ✅ Muestra error si ambos (resumen y escenarios) fallan
- ✅ Cierra spinner correctamente

