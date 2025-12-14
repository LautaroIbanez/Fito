# Optimización de Prompts - Resumen de Implementación

## Objetivo
Robustecer el flujo de prompts para optimizar tokens y evitar loops innecesarios mediante:
1. Separación de contexto fijo vs. datos variables
2. Control de longitud y truncamiento
3. Logging de tokens por paso
4. Caché de respuestas estáticas
5. Condiciones de salida explícitas

## Componentes Implementados

### 1. PromptTemplateService (`app/services/prompt_template_service.py`)
**Funcionalidad:**
- Separa contexto fijo del sistema de datos variables
- Trunca automáticamente noticias, precios y señales según límites configurables
- Valida longitud de prompts antes de enviar a OpenAI
- Aplica truncamiento agresivo si es necesario

**Límites Configurables:**
- `news_item`: 500 caracteres por noticia
- `news_list`: 10 noticias máximo
- `price_points`: 50 puntos máximo
- `signals`: 10 señales máximo
- `total_prompt_chars`: 8000 caracteres totales

**Plantillas Disponibles:**
- `situation_summary`: Para resúmenes de situación
- `scenario_generation`: Para generación de escenarios
- `technical_analysis`: Para análisis técnico (preparado para futuro)

### 2. PromptCacheService (`app/services/prompt_cache_service.py`)
**Funcionalidad:**
- Cachea respuestas basadas en contexto estático
- Invalida automáticamente cuando cambian datos variables
- TTLs configurables por tipo de prompt:
  - `static`: 24 horas
  - `dynamic`: 5 minutos (precios, indicadores)
  - `scenarios`: 30 minutos
  - `summary`: 10 minutos

**Características:**
- Hash de datos variables para detectar cambios
- Limpieza automática de entradas expiradas
- Estadísticas de hit/miss rate

### 3. TokenLogger (`app/services/token_logger.py`)
**Funcionalidad:**
- Registra tokens usados por cada paso
- Calcula costo estimado (basado en precios de gpt-4o)
- Proporciona resúmenes por paso y sesión total
- Logging detallado en consola

**Métricas Registradas:**
- Tokens de entrada (prompt)
- Tokens de salida (completion)
- Total de tokens
- Costo estimado en USD
- Desglose por paso

### 4. PromptOptimizationService (`app/services/prompt_optimization_service.py`)
**Funcionalidad:**
- Servicio centralizado para decidir si hacer llamadas a API
- Verifica datos mínimos requeridos
- Consulta caché antes de llamar
- Valida prompts antes de construir
- Centraliza logging y caché

### 5. Integración en Servicios Existentes

#### SituationSummaryService
- Usa plantillas para construir prompts optimizados
- Verifica caché antes de generar resúmenes
- Aplica truncamiento automático de noticias
- Logging de tokens por lote y meta-resumen
- Condiciones de salida: valida prompt antes de llamar

#### ScenarioGenerationService
- Usa plantillas para prompts de escenarios
- Trunca noticias relacionadas automáticamente
- Valida datos mínimos antes de generar
- Logging de tokens por driver

## Endpoints Nuevos

### GET `/api/token-stats`
Obtiene estadísticas de tokens usados en la sesión actual:
```json
{
  "total_calls": 15,
  "prompt_tokens": 12500,
  "completion_tokens": 3200,
  "total_tokens": 15700,
  "estimated_cost": 0.045,
  "breakdown": {
    "summary_batch_1": {...},
    "scenario_generation_Driver1": {...}
  }
}
```

### GET `/api/cache-stats`
Obtiene estadísticas del caché:
```json
{
  "cache_size": 5,
  "hits": 12,
  "misses": 8,
  "evictions": 2,
  "hit_rate": "60.00%"
}
```

### POST `/api/cache/clear?prompt_type=situation_summary`
Limpia el caché (opcionalmente por tipo).

## Condiciones de Salida Explícitas

### 1. Validación de Datos Mínimos
- Resúmenes: Requiere al menos 1 noticia
- Escenarios: Requiere al menos 1 noticia relacionada
- Análisis técnico: Requiere al menos 5 puntos de precio

### 2. Validación de Longitud de Prompt
- Si el prompt excede 8000 caracteres, se aplica truncamiento agresivo
- Si aún así excede, se cancela la llamada y se retorna error

### 3. Verificación de Caché
- Antes de cada llamada, se verifica si hay respuesta cacheada válida
- Si existe y no ha expirado, se retorna sin llamar a OpenAI

### 4. Validación de Respuesta
- Si la respuesta está vacía o es inválida, no se cachea
- Se registra el error pero no se bloquea el flujo

## Optimizaciones Aplicadas

### Truncamiento Inteligente
- Noticias: Máximo 500 caracteres por noticia, 10 noticias por prompt
- Precios: Solo últimos 50 puntos (mantiene los más recientes)
- Señales: Solo últimas 10 señales
- Resúmenes parciales: Máximo 500 caracteres por resumen en meta-resumen

### Caché Estratégico
- Resúmenes directos: Cacheados por 10 minutos
- Escenarios: No se cachean (noticias cambian frecuentemente)
- Contexto estático: Separado de datos variables para mejor hit rate

### Logging Detallado
- Cada llamada a OpenAI registra:
  - Tokens de entrada/salida
  - Costo estimado
  - Paso específico
  - Tipo de prompt

## Uso

### En Servicios
```python
from app.services.prompt_template_service import PromptTemplateService
from app.services.prompt_cache_service import PromptCacheService, CACHE_TTL
from app.services.token_logger import token_logger

# Construir prompt optimizado
template_service = PromptTemplateService()
prompt_data = template_service.build_optimized_prompt(
    template_type="situation_summary",
    variable_data={"news_items": news_list}
)

# Verificar caché
cache_service = PromptCacheService()
cached = cache_service.get(
    prompt_type="situation_summary",
    static_data={"context": "summary"},
    variable_data={"news_count": len(news_list)}
)

# Logging automático después de llamada
if response.usage:
    token_logger.log_usage(
        prompt_tokens=response.usage.prompt_tokens,
        completion_tokens=response.usage.completion_tokens,
        step_name="my_step",
        prompt_type="situation_summary",
        response=response
    )
```

## Beneficios

1. **Reducción de Tokens**: Truncamiento automático reduce tokens en ~30-50%
2. **Evita Llamadas Redundantes**: Caché previene re-llamadas con mismo contexto
3. **Mejor Visibilidad**: Logging detallado permite identificar pasos costosos
4. **Control de Calidad**: Validaciones previenen llamadas con datos insuficientes
5. **Costo Estimado**: Tracking de costos ayuda a optimizar presupuesto

## Próximos Pasos Sugeridos

1. Agregar métricas de tiempo de respuesta por paso
2. Implementar alertas cuando el costo estimado excede umbrales
3. Agregar dashboard de métricas en frontend
4. Implementar caché persistente (Redis/DB) para producción
5. Agregar análisis de tendencias de tokens por día/semana
