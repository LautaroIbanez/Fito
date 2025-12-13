# Mejoras de Guía Accionable en Tarjetas de Escenarios

## Resumen Ejecutivo

Se ha mejorado el modelo de datos y la visualización de las tarjetas de escenarios para incluir guía accionable: probabilidad/confianza, impacto esperado en el mercado, acciones sugeridas (posicionamiento, hedges), y condiciones trigger (eventos a monitorear).

## 1. Cambios en el Modelo de Datos (Backend)

### 1.1 Actualización del Modelo Scenario

**Archivo:** `backend/app/models.py`

**Campos agregados:**
- `market_impact: Optional[str]` - Impacto esperado en el mercado (breve descripción)
- `suggested_actions: List[str]` - Acciones sugeridas (posicionamiento, hedges, etc.)
- `triggers: List[str]` - Condiciones trigger o eventos a monitorear (ej: FOMC statement, CPI release)

**Modelo completo:**
```python
class Scenario(BaseModel):
    scenario_type: str
    title: str
    description: str
    assumptions: List[ScenarioAssumption]
    risks: List[ScenarioRisk]
    invalidators: List[ScenarioInvalidator]
    confidence: float  # Probabilidad/confianza ya existía
    timeframe: Optional[str]
    market_impact: Optional[str]  # NUEVO
    suggested_actions: List[str]  # NUEVO
    triggers: List[str]  # NUEVO
```

### 1.2 Actualización del Prompt de Generación

**Archivo:** `backend/app/services/scenario_generation_service.py`

**Campos solicitados al LLM:**
- `market_impact`: Impacto esperado en el mercado (1-2 oraciones breves, ej: "Caída del 5-10% en tech stocks")
- `suggested_actions`: Lista de acciones sugeridas (2-3 items, ej: ["Reducir exposición a tech", "Aumentar hedges con puts", "Monitorear indicadores técnicos"])
- `triggers`: Lista de eventos o condiciones trigger a monitorear (2-3 items, ej: ["FOMC statement del 15/03", "CPI release de marzo", "Earnings de AAPL"])

**Ejemplo de estructura JSON solicitada:**
```json
{
  "base": {
    "title": "...",
    "description": "...",
    "confidence": 0.75,
    "timeframe": "3-6 meses",
    "market_impact": "Impacto esperado en el mercado...",
    "suggested_actions": ["Acción 1", "Acción 2"],
    "triggers": ["Evento 1", "Evento 2"]
  }
}
```

### 1.3 Validación y Procesamiento

**Validaciones implementadas:**
- `suggested_actions` y `triggers` se validan como listas
- Si no son listas, se convierten a listas vacías
- `market_impact` es opcional y puede ser None

## 2. Cambios en la Visualización (Frontend)

### 2.1 Actualización del Componente ScenarioInsightCard

**Archivo:** `frontend/src/components/ScenarioInsightCard.tsx`

**Nuevas secciones agregadas:**

1. **Impacto Esperado (Market Impact)**
   - Muestra el impacto esperado en el mercado
   - Formato: Párrafo destacado con borde izquierdo
   - Solo se muestra si está disponible

2. **Acciones Sugeridas (Suggested Actions)**
   - Lista de acciones sugeridas (máximo 3)
   - Icono ⚡ para cada acción
   - Formato: Bullets compactos

3. **Eventos a Monitorear (Triggers)**
   - Lista de eventos o condiciones trigger (máximo 3)
   - Icono 📅 para cada trigger
   - Formato: Bullets compactos

### 2.2 Layout Compacto

**Optimizaciones implementadas:**
- Descripción limitada a 3 bullets máximo
- Supuestos limitados a 2 items máximo
- Riesgos limitados a 2 items máximo
- Invalidadores limitados a 2 items máximo
- Acciones sugeridas limitadas a 3 items máximo
- Triggers limitados a 3 items máximo
- Altura máxima de 600px con scroll si es necesario

**Estructura de la tarjeta:**
```
┌─────────────────────────────────────┐
│ [Tipo]              [Confianza %]  │
├─────────────────────────────────────┤
│ 💡 Key Takeaway                     │
├─────────────────────────────────────┤
│ CONTEXTO                            │
│ • Bullet 1                          │
│ • Bullet 2                          │
│ • Bullet 3                          │
├─────────────────────────────────────┤
│ IMPACTO ESPERADO                    │
│ [Descripción breve del impacto]     │
├─────────────────────────────────────┤
│ ANÁLISIS                            │
│ Supuestos Clave                     │
│ • Supuesto 1 (Prob: 70%)            │
│ • Supuesto 2                        │
│ Riesgos                              │
│ • Riesgo 1 • high                   │
│ • Riesgo 2                          │
├─────────────────────────────────────┤
│ ACCIONES SUGERIDAS                  │
│ ⚡ Reducir exposición a tech        │
│ ⚡ Aumentar hedges con puts         │
│ ⚡ Monitorear indicadores técnicos  │
├─────────────────────────────────────┤
│ EVENTOS A MONITOREAR                │
│ 📅 FOMC statement del 15/03         │
│ 📅 CPI release de marzo             │
│ 📅 Earnings de AAPL                 │
├─────────────────────────────────────┤
│ TIMELINE                            │
│ Horizonte: 3-6 meses                 │
│ Invalidadores                       │
│ • Condición: Descripción            │
└─────────────────────────────────────┘
```

### 2.3 Estilos CSS

**Archivo:** `frontend/src/components/ScenarioInsightCard.css`

**Nuevos estilos:**
- `.market-impact` - Sección de impacto esperado
- `.impact-description` - Descripción del impacto con borde izquierdo
- `.suggested-actions` - Sección de acciones sugeridas
- `.action-item` - Item de acción con icono
- `.triggers` - Sección de triggers
- `.trigger-item` - Item de trigger con icono
- `.insight-bullets.compact` - Bullets compactos con menos gap

**Colores por tipo:**
- Base: Borde izquierdo azul para impacto
- Risk: Borde izquierdo rojo para impacto
- Opportunity: Borde izquierdo verde para impacto

## 3. Validación de Requisitos

### 3.1 Checklist de Implementación

- [x] Probabilidad/confianza incluida (ya existía, se mantiene)
- [x] Impacto esperado en el mercado agregado (`market_impact`)
- [x] Acciones sugeridas agregadas (`suggested_actions`)
- [x] Condiciones trigger agregadas (`triggers`)
- [x] Layout compacto con 2-3 bullets clave
- [x] Oración descriptiva corta sin overflow
- [x] Modelo de datos incluye campos estructurados
- [x] Validación de datos implementada

### 3.2 Campos Estructurados Validados

**Probabilidad/Confianza:**
- ✅ Campo `confidence` (0.0-1.0) ya existía
- ✅ Se muestra en badge prominente
- ✅ Se incluye en assumptions con `probability`

**Impacto Esperado:**
- ✅ Campo `market_impact` agregado (string opcional)
- ✅ Se muestra en sección destacada
- ✅ Formato: 1-2 oraciones breves

**Acciones Sugeridas:**
- ✅ Campo `suggested_actions` agregado (List[str])
- ✅ Se muestra en bullets con iconos
- ✅ Limitado a 3 items máximo

**Triggers:**
- ✅ Campo `triggers` agregado (List[str])
- ✅ Se muestra en bullets con iconos
- ✅ Limitado a 3 items máximo

## 4. Ejemplos de Uso

### 4.1 Ejemplo de Escenario Base

```json
{
  "title": "Continuación de tendencia alcista en tech",
  "confidence": 0.75,
  "market_impact": "Aumento del 5-10% en tech stocks en los próximos 3 meses",
  "suggested_actions": [
    "Aumentar exposición a tech stocks",
    "Considerar calls en tech ETFs",
    "Monitorear indicadores técnicos de momentum"
  ],
  "triggers": [
    "FOMC statement del 15/03",
    "CPI release de marzo",
    "Earnings de AAPL y MSFT"
  ]
}
```

### 4.2 Ejemplo de Escenario de Riesgo

```json
{
  "title": "Corrección en tech por preocupaciones de inflación",
  "confidence": 0.65,
  "market_impact": "Caída del 10-15% en tech stocks si la inflación supera expectativas",
  "suggested_actions": [
    "Reducir exposición a tech",
    "Aumentar hedges con puts",
    "Considerar posiciones defensivas"
  ],
  "triggers": [
    "CPI release de marzo",
    "FOMC statement sobre política monetaria",
    "Indicadores de inflación PPI"
  ]
}
```

## 5. Mejoras Futuras Opcionales

### 5.1 Priorización de Acciones

Agregar campo `action_priority` para ordenar acciones por importancia.

### 5.2 Fechas Específicas para Triggers

Agregar campo `trigger_dates` para mostrar fechas específicas de eventos.

### 5.3 Notificaciones

Integrar con sistema de alertas para notificar cuando se acerquen eventos trigger.

### 5.4 Tracking de Acciones

Permitir marcar acciones como "completadas" o "en progreso".

## 6. Conclusión

### 6.1 Mejoras Implementadas

- ✅ Probabilidad/confianza visible y destacada
- ✅ Impacto esperado en el mercado agregado
- ✅ Acciones sugeridas con formato accionable
- ✅ Condiciones trigger/eventos a monitorear
- ✅ Layout compacto sin overflow
- ✅ Modelo de datos estructurado y validado

### 6.2 Resultado

Las tarjetas de escenarios ahora proporcionan:
- **Guía accionable clara** (acciones sugeridas específicas)
- **Contexto de impacto** (qué esperar en el mercado)
- **Timeline accionable** (eventos a monitorear)
- **Información estructurada** (probabilidad, impacto, acciones, triggers)
- **Layout optimizado** (compacto, sin overflow, fácil de escanear)

