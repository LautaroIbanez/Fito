# Análisis de Performance - Generación de Escenarios

## Resumen Ejecutivo

Este documento analiza el flujo de generación de escenarios en la carga inicial, identifica cuellos de botella, mide tiempos de respuesta y propone opciones de mitigación para mejorar la experiencia del usuario.

## 1. Flujo de Generación de Escenarios

### 1.1 Endpoint Principal
**Ubicación:** `backend/app/routers/scenarios.py:25`

**Endpoint:** `POST /api/scenarios`

**Timeout configurado:** 180 segundos (3 minutos)

### 1.2 Proceso Completo

El flujo de generación sigue estos pasos:

```
1. Obtención de noticias (líneas 44-61)
   ├─ Filtrado por IDs específicos O
   └─ Obtención de noticias recientes (límite: 20)
      ├─ Prioriza noticias ya estandarizadas
      └─ Si < 10 estandarizadas, agrega hasta 10 sin estandarizar

2. Estandarización de noticias (líneas 69-130)
   ├─ Limita a 5 noticias por llamada para evitar timeouts
   └─ Guarda datos estandarizados en BD

3. Generación de escenarios (líneas 149-183)
   └─ Ejecuta ScenarioEngineService.generate_scenarios()
      ├─ Paso 1: Identificar drivers (ScenarioDriverService)
      ├─ Paso 2: Generar escenarios por driver (ScenarioGenerationService)
      └─ Paso 3: Mapear a cartera (ScenarioPortfolioMappingService)
```

### 1.3 Servicios Involucrados

#### ScenarioEngineService (`scenario_engine_service.py`)
- **Función:** Orquesta el proceso completo
- **Tiempo estimado:** Variable según número de drivers

#### ScenarioDriverService (`scenario_driver_service.py`)
- **Función:** Identifica drivers temáticos (1 llamada a OpenAI)
- **Timeout:** 60 segundos (línea 73)
- **Tiempo típico:** 3-5 segundos según logs

#### ScenarioGenerationService (`scenario_generation_service.py`)
- **Función:** Genera escenarios base/riesgo/oportunidad por driver
- **Timeout:** 90 segundos (línea 80)
- **Tiempo típico:** 10-15 segundos por driver según logs
- **Ejecución:** Secuencial (un driver a la vez)

#### ScenarioPortfolioMappingService (`scenario_portfolio_mapping_service.py`)
- **Función:** Mapea escenarios a activos de cartera
- **Timeout:** 60 segundos (estimado)
- **Tiempo típico:** 5-10 segundos por driver según logs
- **Ejecución:** Secuencial (un driver a la vez)

## 2. Medición de Tiempos

### 2.1 Tiempos por Etapa (Basado en Logs)

Según los logs del backend proporcionados:

```
Ciclo completo de generación (3 drivers):
├─ Identificación de drivers: ~4-5 segundos
├─ Generación escenarios driver 1: ~13 segundos
├─ Mapeo cartera driver 1: ~9 segundos
├─ Generación escenarios driver 2: ~15 segundos
├─ Mapeo cartera driver 2: ~6 segundos
├─ Generación escenarios driver 3: ~12 segundos
└─ Mapeo cartera driver 3: ~5 segundos

TOTAL: ~64-71 segundos para 3 drivers
```

**Desglose por driver:**
- Driver 1: ~22 segundos (13s escenarios + 9s mapeo)
- Driver 2: ~21 segundos (15s escenarios + 6s mapeo)
- Driver 3: ~17 segundos (12s escenarios + 5s mapeo)

### 2.2 Comparación con Timeouts

| Etapa | Timeout Backend | Timeout Frontend | Tiempo Típico | Margen |
|-------|----------------|------------------|---------------|--------|
| Identificación drivers | 60s | N/A | 4-5s | ✅ Amplio |
| Generación escenarios/driver | 90s | N/A | 10-15s | ✅ Amplio |
| Mapeo cartera/driver | 60s (est) | N/A | 5-10s | ✅ Amplio |
| **Total (3 drivers)** | **180s** | **180s** | **64-71s** | ✅ Adecuado |

**Conclusión:** Los timeouts están bien configurados. El problema no es el timeout, sino el tiempo total de procesamiento.

### 2.3 Tiempo Total por Número de Drivers

| Drivers | Tiempo Estimado | Tiempo Máximo (con margen) |
|---------|-----------------|----------------------------|
| 1 | ~20-25s | ~30s |
| 2 | ~40-50s | ~60s |
| 3 | ~64-71s | ~90s |
| 4 | ~85-95s | ~120s |
| 5 | ~105-120s | ~150s |

**Nota:** Con `max_drivers=2` (configuración actual del frontend), el tiempo esperado es ~40-50 segundos.

## 3. Verificación de Llamadas Duplicadas

### 3.1 Análisis del Frontend

**Ubicación:** `frontend/src/components/ProactiveAssistant.tsx:173`

```typescript
const result = await Promise.allSettled([
  safeGetSummary(),      // GET /api/news/summary
  safeGenerateScenarios() // POST /api/scenarios
])
```

**Conclusión:** El frontend hace **una sola llamada** a `/api/scenarios` por generación de síntesis.

### 3.2 Análisis del Backend

**Ubicación:** `backend/app/routers/scenarios.py:25`

El endpoint no tiene cache ni verificación de llamadas concurrentes. Cada llamada:
1. Obtiene noticias de la BD
2. Estandariza noticias si es necesario
3. Genera escenarios desde cero

**Riesgo:** Si el usuario hace clic múltiples veces en "Generar Síntesis", se pueden disparar múltiples llamadas concurrentes.

### 3.3 Verificación de Llamadas Concurrentes

**Evidencia de logs:**
```
2025-12-12 20:09:57 - Generando escenarios: 10 noticias, 5 items de cartera, timeout=180s
2025-12-12 20:11:41 - Generando escenarios: 10 noticias, 5 items de cartera, timeout=180s
```

**Conclusión:** Se observan llamadas casi simultáneas (diferencia de ~1 minuto 44 segundos), pero no son exactamente duplicadas. Podrían ser:
- Usuario haciendo clic múltiples veces
- Recarga de página
- Llamadas desde diferentes componentes

## 4. Limitaciones y Paginación

### 4.1 Limitación de Noticias

**Ubicación:** `backend/app/routers/scenarios.py:50-54`

```python
# Limitar a 20 noticias para evitar timeouts
news_items = db.query(NewsItem).filter(
    NewsItem.standardized_data.isnot(None)
).order_by(desc(NewsItem.created_at)).limit(20).all()
```

**Conclusión:** ✅ Ya existe limitación a 20 noticias.

### 4.2 Limitación de Estandarización

**Ubicación:** `backend/app/routers/scenarios.py:92-100`

```python
# Limitar cuántas noticias estandarizamos en una sola llamada
items_to_standardize = needs_standardization[:5]
```

**Conclusión:** ✅ Ya existe limitación a 5 noticias por estandarización.

### 4.3 Limitación de Drivers

**Ubicación:** `backend/app/routers/scenarios.py:168`

```python
scenario_request.max_drivers  # Viene del request del frontend
```

**Frontend:** `frontend/src/components/ProactiveAssistant.tsx:155`

```typescript
scenariosApi.generate({ max_drivers: 2, include_portfolio_mapping: true })
```

**Conclusión:** ✅ Ya existe limitación a 2 drivers en el frontend.

## 5. Opciones de Mitigación (Propuestas)

### 5.1 Opción 1: Cache de Últimos Escenarios Generados

**Descripción:**
- Almacenar en BD o cache (Redis) los últimos escenarios generados
- Si las noticias no han cambiado significativamente, retornar escenarios cacheados
- Invalidar cache cuando se agreguen nuevas noticias o pasen X horas

**Ventajas:**
- Respuesta instantánea si hay cache válido
- Reduce carga en OpenAI
- Reduce costos de API

**Desventajas:**
- Complejidad adicional (gestión de cache, invalidación)
- Puede mostrar datos obsoletos si no se invalida correctamente
- Requiere almacenamiento adicional

**Implementación estimada:**
- Backend: 2-3 horas
- Testing: 1 hora
- **Total: 3-4 horas**

**Impacto esperado:**
- Primera carga: Sin cambio (64-71s)
- Cargas subsecuentes: <1 segundo (si cache válido)

### 5.2 Opción 2: Placeholder Rápido + Actualización en Segundo Plano

**Descripción:**
- Retornar inmediatamente un placeholder con estructura básica
- Generar escenarios reales en segundo plano (background job)
- Actualizar UI cuando los escenarios reales estén listos (WebSocket o polling)

**Ventajas:**
- UI no queda bloqueada esperando
- Usuario ve contenido inmediatamente
- Escenarios se actualizan progresivamente

**Desventajas:**
- Complejidad alta (background jobs, WebSocket/polling)
- Requiere sistema de colas (Celery, RQ, etc.)
- UX puede ser confusa si los placeholders no son claros

**Implementación estimada:**
- Backend: 4-6 horas (sistema de colas, endpoints de estado)
- Frontend: 2-3 horas (WebSocket/polling, actualización progresiva)
- Testing: 2 horas
- **Total: 8-11 horas**

**Impacto esperado:**
- Tiempo inicial: <1 segundo (placeholder)
- Tiempo real: 64-71s (en segundo plano)
- Actualización: Progresiva cuando esté listo

### 5.3 Opción 3: Desacoplar Generación de Renderización Inicial

**Descripción:**
- La carga inicial NO espera escenarios
- Mostrar UI inmediatamente con datos disponibles (resumen, noticias)
- Botón separado "Generar Escenarios" que el usuario puede activar manualmente
- O generar escenarios automáticamente después de mostrar la UI inicial

**Ventajas:**
- Implementación más simple
- UI carga inmediatamente
- Usuario tiene control sobre cuándo generar escenarios
- No requiere infraestructura adicional

**Desventajas:**
- Escenarios no están disponibles inmediatamente
- Requiere acción manual del usuario (o espera automática en segundo plano)

**Implementación estimada:**
- Backend: Sin cambios (ya existe endpoint)
- Frontend: 1-2 horas (separar lógica de carga inicial)
- Testing: 1 hora
- **Total: 2-3 horas**

**Impacto esperado:**
- Tiempo inicial: <1 segundo (sin escenarios)
- Tiempo de escenarios: 64-71s (cuando se generen)
- UX: Usuario ve contenido inmediatamente, escenarios aparecen después

### 5.4 Opción 4: Generación Incremental (Streaming de Drivers)

**Descripción:**
- Retornar cada driver tan pronto como se genera (Server-Sent Events o WebSocket)
- Mostrar drivers progresivamente en la UI
- No esperar a que todos los drivers estén listos

**Ventajas:**
- Usuario ve contenido progresivamente
- No hay espera de "todo o nada"
- Mejor percepción de velocidad

**Desventajas:**
- Complejidad alta (streaming, manejo de estado parcial)
- Requiere cambios significativos en frontend y backend
- Manejo de errores más complejo

**Implementación estimada:**
- Backend: 6-8 horas (Server-Sent Events, refactor de servicios)
- Frontend: 3-4 horas (manejo de streaming, actualización progresiva)
- Testing: 2-3 horas
- **Total: 11-15 horas**

**Impacto esperado:**
- Primer driver: ~20-25s
- Drivers subsecuentes: ~20-25s cada uno
- Percepción: Mejor (contenido aparece progresivamente)

### 5.5 Opción 5: Reducir max_drivers a 1 en Carga Inicial

**Descripción:**
- Cambiar `max_drivers=2` a `max_drivers=1` en la carga inicial
- Permitir al usuario solicitar más drivers manualmente después

**Ventajas:**
- Implementación trivial (cambio de 1 línea)
- Reduce tiempo a la mitad (~20-25s en lugar de 40-50s)
- Mantiene funcionalidad completa

**Desventajas:**
- Menos información inicial
- Usuario debe hacer clic para más drivers

**Implementación estimada:**
- Backend: Sin cambios
- Frontend: 5 minutos (cambiar `max_drivers: 2` a `max_drivers: 1`)
- Testing: 15 minutos
- **Total: 20 minutos**

**Impacto esperado:**
- Tiempo inicial: ~20-25s (en lugar de 40-50s)
- Reducción: ~50%

## 6. Recomendación

### Recomendación Principal: Opción 3 + Opción 5 (Combinada)

**Implementar:**
1. **Opción 5 (rápida):** Reducir `max_drivers=1` en carga inicial
2. **Opción 3 (media):** Desacoplar generación de renderización inicial

**Justificación:**
- **Opción 5** proporciona mejora inmediata con esfuerzo mínimo
- **Opción 3** resuelve el problema de raíz sin complejidad excesiva
- Combinadas, proporcionan la mejor relación esfuerzo/beneficio

**Plan de Implementación:**

**Fase 1 (20 minutos):**
- Cambiar `max_drivers: 2` a `max_drivers: 1` en `ProactiveAssistant.tsx`
- Impacto: Reducción inmediata de ~50% en tiempo de generación

**Fase 2 (2-3 horas):**
- Modificar `HoyView` para no esperar escenarios en carga inicial
- Mostrar UI inmediatamente con resumen y noticias
- Generar escenarios automáticamente en segundo plano después de mostrar UI
- Actualizar UI cuando escenarios estén listos

**Resultado esperado:**
- Tiempo de carga inicial: <1 segundo (UI visible inmediatamente)
- Tiempo de escenarios: ~20-25s (en segundo plano)
- UX: Usuario ve contenido inmediatamente, escenarios aparecen cuando estén listos

## 7. Métricas Actuales vs Esperadas

### Estado Actual
- Tiempo de carga inicial: 64-71s (con 3 drivers) o 40-50s (con 2 drivers)
- UI bloqueada: Sí, hasta que escenarios estén listos
- Experiencia: Usuario ve "Cargando..." durante todo el proceso

### Estado Esperado (con recomendación)
- Tiempo de carga inicial: <1 segundo (UI visible)
- Tiempo de escenarios: ~20-25s (en segundo plano, con 1 driver)
- UI bloqueada: No, UI visible inmediatamente
- Experiencia: Usuario ve contenido inmediatamente, escenarios aparecen progresivamente

## 8. Evidencia de Logs

### Logs Analizados
```
2025-12-12 20:09:57 - Generando escenarios: 10 noticias, 5 items de cartera
2025-12-12 20:09:58 - Iniciando generación de escenarios: 10 noticias
2025-12-12 20:10:02 - Identificados 3 drivers temáticos (4s)
2025-12-12 20:10:15 - Escenarios generados para driver 1 (13s)
2025-12-12 20:10:24 - Mapeo completado driver 1 (9s)
2025-12-12 20:10:41 - Escenarios generados para driver 2 (17s)
2025-12-12 20:10:47 - Mapeo completado driver 2 (6s)
2025-12-12 20:11:00 - Escenarios generados para driver 3 (13s)
2025-12-12 20:11:05 - Mapeo completado driver 3 (5s)
2025-12-12 20:11:05 - Generación completada: 3 drivers generados
```

**Tiempo total:** ~68 segundos para 3 drivers

## 9. Conclusión

El problema principal no es el timeout (está bien configurado), sino el tiempo total de procesamiento y el bloqueo de la UI durante la generación.

La solución recomendada (Opción 3 + Opción 5) proporciona:
- ✅ Mejora inmediata con esfuerzo mínimo (Opción 5)
- ✅ Solución de raíz sin complejidad excesiva (Opción 3)
- ✅ Mejor experiencia de usuario (UI visible inmediatamente)
- ✅ Mantenibilidad (código simple, sin infraestructura adicional)

