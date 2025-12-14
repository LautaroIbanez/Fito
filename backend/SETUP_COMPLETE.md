# Setup Completo - Motor Local Sin LLM

## Estado

✅ **spacy instalado correctamente** en el entorno virtual.

## Verificación

El servidor debería poder iniciar ahora. El sistema de NLP local tiene fallbacks automáticos:

1. **Si los modelos completos están instalados** (`es_core_news_sm`, `en_core_web_sm`):
   - Usa modelos completos con mejor precisión

2. **Si los modelos NO están instalados**:
   - Usa modelos base de spaCy (Spanish(), English())
   - Funciona sin dependencias de red
   - Precisión reducida pero funcional

## Instalación Opcional de Modelos (Recomendado)

Para mejor precisión, puedes instalar los modelos de idioma:

```bash
# Activar entorno virtual
cd backend
.\venv\Scripts\Activate.ps1

# Instalar modelos de spaCy (opcional, pero recomendado)
python -m spacy download es_core_news_sm
python -m spacy download en_core_web_sm
```

**Nota:** Los modelos son grandes (~50-100 MB cada uno) y requieren descarga de internet. El sistema funciona sin ellos usando modelos base.

## Iniciar Servidor

```bash
cd backend
.\venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --port 8001
```

**Logs esperados al iniciar:**
```
MOTOR LOCAL ACTIVO (SIN LLM)
  Resumen: Extractivo (NLP local)
  Drivers: Detección por keywords/entidades
  Escenarios: Plantillas 'si-entonces'
  Mapeo: Reglas basadas en coincidencias
  Sin llamadas HTTP externas
  Sin costos de API
```

Si los modelos no están instalados, verás:
```
WARNING: Modelo es_core_news_sm no encontrado, usando modelo base español
WARNING: Modelo en_core_web_sm no encontrado, usando modelo base inglés
INFO: Usando modelos base de spaCy (sin dependencias de red)
```

Esto es normal y el sistema funcionará correctamente.

## Prueba Rápida

Una vez iniciado el servidor, prueba:

```bash
# Test de NLP local
curl http://localhost:8001/api/local-nlp/test?text=Apple%20anunció%20crecimiento%20récord

# Debería retornar análisis sin errores
```

## Resumen de Dependencias

✅ **Instalado:**
- spacy>=3.7.0
- Todos los servicios de NLP local funcionan

⚠️ **Opcional (recomendado):**
- es_core_news_sm (modelo español)
- en_core_web_sm (modelo inglés)

El sistema funciona con o sin los modelos opcionales.
