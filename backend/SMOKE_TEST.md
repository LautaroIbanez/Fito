# Smoke Test - Motor Local Sin LLM

## Objetivo

Validar que el sistema funciona completamente sin llamadas a OpenAI, usando solo el motor local basado en reglas y NLP local.

## Pre-requisitos

1. Backend corriendo en `http://localhost:8001`
2. Base de datos inicializada
3. spaCy instalado (para NLP local)

## Pasos del Smoke Test

### 1. Verificar que el servidor inicia sin errores

```bash
cd backend
python -m uvicorn app.main:app --reload --port 8001
```

**Verificar en logs:**
```
MOTOR LOCAL ACTIVO (SIN LLM)
  Resumen: Extractivo (NLP local)
  Drivers: Detección por keywords/entidades
  Escenarios: Plantillas 'si-entonces'
  Mapeo: Reglas basadas en coincidencias
  Sin llamadas HTTP externas
  Sin costos de API
```

### 2. Cargar noticias de ejemplo

```bash
# Noticia 1: Tecnología (positiva)
curl -X POST http://localhost:8001/api/news \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Apple anuncia crecimiento récord en iPhone",
    "body": "Apple Inc. reportó un crecimiento récord en sus ventas de iPhone durante el último trimestre, superando las expectativas del mercado. La empresa tecnológica reportó ganancias históricas de $120 mil millones, un aumento del 15% respecto al año anterior. Los analistas esperan que esta tendencia continúe en los próximos meses.",
    "source": "Tech News"
  }'

# Noticia 2: Finanzas (negativa)
curl -X POST http://localhost:8001/api/news \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Reserva Federal aumenta tasas de interés",
    "body": "La Reserva Federal anunció un aumento de 0.25 puntos porcentuales en las tasas de interés, generando preocupación en los mercados financieros. Los analistas prevén una desaceleración económica y recomiendan cautela en inversiones de riesgo.",
    "source": "Financial Times"
  }'

# Noticia 3: Energía (positiva)
curl -X POST http://localhost:8001/api/news \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Petróleo sube por tensiones geopolíticas",
    "body": "El precio del petróleo subió un 3% debido a las tensiones geopolíticas en el Medio Oriente. Los inversores esperan que esta tendencia continúe si las tensiones se intensifican.",
    "source": "Energy Report"
  }'
```

**Verificar:**
- ✅ Respuestas con status `201 Created`
- ✅ IDs de noticias retornados
- ✅ Logs muestran `[MOTOR LOCAL]` (si hay estandarización automática)

### 3. Generar resumen de situación

```bash
curl http://localhost:8001/api/news/summary
```

**Verificar en respuesta:**
- ✅ `"method": "extractive"`
- ✅ `"summary"` contiene texto generado
- ✅ `"meta_summary"` contiene texto generado
- ✅ `"tokens_used": null` (sin costos de API)
- ✅ `"estimated_tokens"` tiene valor (estimación local)

**Verificar en logs del servidor:**
- ✅ `[MOTOR LOCAL] Resumen extractivo completado`
- ✅ `procesamiento local, sin llamadas HTTP externas`
- ✅ No aparece "api.openai.com"
- ✅ No aparece "costos de API"

### 4. Generar drivers y escenarios

```bash
curl -X POST http://localhost:8001/api/scenarios \
  -H "Content-Type: application/json" \
  -d '{
    "max_drivers": 3,
    "include_portfolio_mapping": true
  }'
```

**Verificar en respuesta:**
- ✅ `"total_drivers"` > 0
- ✅ Cada driver tiene `"scenarios"` con `"base"`, `"risk"`, `"opportunity"`
- ✅ Cada escenario tiene todos los campos requeridos
- ✅ `"portfolio_mappings"` contiene mapeos (si hay cartera)

**Verificar en logs del servidor:**
- ✅ `[MOTOR LOCAL] Iniciando generación de escenarios: ... (método: reglas locales (sin LLM))`
- ✅ `[MOTOR LOCAL] Drivers detectados: ... drivers (procesamiento local, sin LLM)`
- ✅ `[MOTOR LOCAL] Escenarios generados para driver ... (plantillas locales, sin LLM)`
- ✅ `[MOTOR LOCAL] Mapeo completado: ... activos identificados (reglas locales, sin LLM)`
- ✅ `[MOTOR LOCAL] Generación de escenarios completada: ... drivers generados (procesamiento local, sin llamadas HTTP externas)`
- ✅ No aparece "api.openai.com"
- ✅ No aparece "OpenAI"

### 5. Verificar que no hay llamadas HTTP externas

**Opción A: Usar script de validación**

```bash
cd backend
python -m app.scripts.validate_local_motor
```

**Opción B: Monitorear red**

Usar herramientas como:
- `tcpdump` o `wireshark` para monitorear tráfico de red
- `netstat` para ver conexiones activas
- Interceptores de proxy (Burp, OWASP ZAP)

**Verificar:**
- ✅ No hay conexiones a `api.openai.com`
- ✅ No hay conexiones a `*.openai.com`
- ✅ Solo hay conexiones locales (localhost) o a la base de datos

### 6. Verificar logs completos

Buscar en los logs del servidor durante todas las pruebas:

**Debe aparecer:**
- ✅ `[MOTOR LOCAL]` en todos los mensajes relevantes
- ✅ "procesamiento local"
- ✅ "sin llamadas HTTP externas"
- ✅ "sin LLM"
- ✅ "plantillas locales"
- ✅ "reglas locales"

**NO debe aparecer:**
- ❌ "api.openai.com"
- ❌ "OpenAI API"
- ❌ "costos de API"
- ❌ "tokens usados" (solo "tokens estimados")
- ❌ "Error de autenticación con OpenAI"
- ❌ "Cuota de OpenAI agotada"

## Checklist de Validación

### Funcionalidad
- [ ] Servidor inicia sin errores
- [ ] Noticias se cargan correctamente
- [ ] Resumen se genera exitosamente
- [ ] Drivers se detectan correctamente
- [ ] Escenarios se generan con estructura completa
- [ ] Mapeo a cartera funciona (si hay cartera)

### Sin LLM
- [ ] No hay llamadas a `api.openai.com`
- [ ] Logs muestran `[MOTOR LOCAL]`
- [ ] Respuestas incluyen `"method": "extractive"` o similar
- [ ] No hay errores de autenticación de OpenAI
- [ ] No hay referencias a costos de API

### Logs
- [ ] Todos los logs relevantes incluyen `[MOTOR LOCAL]`
- [ ] Logs mencionan "procesamiento local"
- [ ] Logs mencionan "sin llamadas HTTP externas"
- [ ] No hay logs de OpenAI en el flujo estándar

## Resultado Esperado

Al completar el smoke test, deberías ver:

1. **Servidor iniciado:**
   ```
   MOTOR LOCAL ACTIVO (SIN LLM)
   ```

2. **Resumen generado:**
   ```json
   {
     "summary": "Resumen extractivo...",
     "method": "extractive",
     "estimated_tokens": 250,
     "tokens_used": null
   }
   ```

3. **Escenarios generados:**
   ```json
   {
     "total_drivers": 2,
     "drivers": [
       {
         "driver": "Sector: tecnología",
         "scenarios": {
           "base": {...},
           "risk": {...},
           "opportunity": {...}
         }
       }
     ]
   }
   ```

4. **Logs del servidor:**
   ```
   [MOTOR LOCAL] Resumen extractivo completado: 2 lotes, 850 chars totales, ~212 tokens estimados (procesamiento local, sin llamadas HTTP externas)
   [MOTOR LOCAL] Drivers detectados: 2 drivers (procesamiento local, sin LLM)
   [MOTOR LOCAL] Generación de escenarios completada: 2 drivers generados (procesamiento local, sin llamadas HTTP externas)
   ```

## Troubleshooting

### Si aparecen errores de OpenAI:

1. Verificar que los servicios se instancian sin parámetros:
   ```python
   # Correcto (usa motor local)
   service = SituationSummaryService()
   service = ScenarioEngineService()
   
   # Incorrecto (usa OpenAI)
   service = SituationSummaryService(use_extractive=False)
   service = ScenarioEngineService(use_rule_based=False)
   ```

2. Verificar que los endpoints no pasan parámetros:
   ```python
   # En routers/news.py y routers/scenarios.py
   summary_service = SituationSummaryService()  # Sin parámetros
   scenario_service = ScenarioEngineService()    # Sin parámetros
   ```

### Si no se generan drivers:

1. Verificar que hay suficientes noticias (mínimo 2 por driver)
2. Verificar que las noticias tienen contenido suficiente
3. Revisar logs para ver qué keywords/entidades se detectaron

### Si no se generan escenarios:

1. Verificar que se detectaron drivers
2. Verificar que los drivers tienen noticias relacionadas
3. Revisar logs para ver errores específicos
