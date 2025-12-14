# Configuración de NLP Local

## Instalación

### 1. Instalar spaCy

```bash
pip install spacy
```

### 2. Instalar modelos de idioma (opcional pero recomendado)

Para español:
```bash
python -m spacy download es_core_news_sm
```

Para inglés:
```bash
python -m spacy download en_core_web_sm
```

**Nota:** Si no se instalan los modelos, el sistema usará modelos base de spaCy que funcionan sin dependencias de red, pero con capacidades limitadas.

### 3. Verificar instalación

```bash
python -m app.scripts.init_local_nlp
```

## Estructura

```
app/
├── config/                          # Diccionarios JSON/YAML
│   ├── sentiment_dict.json         # Palabras para análisis de sentimiento
│   ├── sectors_dict.json           # Palabras clave por sector
│   └── risk_opportunity_dict.json  # Palabras para riesgos/oportunidades
│
└── services/
    └── local_nlp/                   # Módulo de NLP local
        ├── __init__.py
        ├── nlp_processor.py         # Procesador principal con spaCy
        ├── sentiment_analyzer.py    # Análisis de sentimiento
        ├── sector_classifier.py     # Clasificación de sectores
        ├── entity_extractor.py      # Extracción de entidades
        ├── dictionary_loader.py     # Cargador de diccionarios
        └── local_nlp_service.py     # Servicio unificado
```

## Uso

### Uso básico

```python
from app.services.local_nlp import get_local_nlp_service

# Obtener servicio
nlp_service = get_local_nlp_service()

# Analizar noticia
result = nlp_service.analyze_news(
    text="Apple anunció crecimiento récord...",
    title="Apple supera expectativas",
    language="es"  # Opcional, se detecta automáticamente
)

# Resultado incluye:
# - sentiment: scores de sentimiento
# - sentiment_label: "positive", "negative", o "neutral"
# - sectors: sectores detectados con scores
# - primary_sector: sector principal
# - entities: entidades nombradas (ORG, PERSON, GPE, etc.)
# - tickers: posibles símbolos de acciones
# - keywords: palabras clave extraídas
# - language: idioma detectado
```

### Componentes individuales

```python
from app.services.local_nlp import (
    get_nlp_processor,
    SentimentAnalyzer,
    SectorClassifier,
    EntityExtractor
)

# Procesador NLP
processor = get_nlp_processor()
doc = processor.process_text("Texto a procesar")
lemmas = processor.lemmatize("Texto a lematizar")
keywords = processor.extract_keywords("Texto para keywords")

# Análisis de sentimiento
sentiment_analyzer = SentimentAnalyzer()
sentiment = sentiment_analyzer.analyze_sentiment("Texto")
label = sentiment_analyzer.get_sentiment_label("Texto")

# Clasificación de sectores
sector_classifier = SectorClassifier()
sectors = sector_classifier.classify_sectors("Texto")
primary = sector_classifier.get_primary_sector("Texto")

# Extracción de entidades
entity_extractor = EntityExtractor()
entities = entity_extractor.extract_entities("Texto")
tickers = entity_extractor.extract_tickers("Texto")
```

## Diccionarios

Los diccionarios se encuentran en `app/config/` y se cargan automáticamente al inicializar el servicio.

### Actualizar diccionarios

1. Editar el archivo JSON correspondiente en `app/config/`
2. Reiniciar el servicio o llamar a `reload_dictionary()`:

```python
from app.services.local_nlp import get_dictionary_loader

loader = get_dictionary_loader()
loader.reload_dictionary("sentiment_dict.json")
```

### Versiones

Cada diccionario tiene un campo `version` para tracking:

```python
loader = get_dictionary_loader()
version = loader.get_dictionary_version("sentiment_dict.json")
```

## Criterios de Aceptación

✅ **El backend puede inicializarse sin dependencias de red**
- Los modelos base de spaCy funcionan sin descargas
- Los diccionarios se cargan desde archivos locales
- No hay llamadas HTTP durante la inicialización

✅ **Los diccionarios se cargan al inicio y son accesibles por los servicios**
- Carga automática al inicializar cada componente
- Acceso global mediante instancias singleton
- Recarga manual disponible

✅ **spaCy (o alternativa local) se instala y funciona sin llamadas externas**
- Modelos base incluidos en spaCy
- Modelos completos opcionales (requieren descarga inicial)
- Fallback a modelos base si no están disponibles

## Notas

- Los modelos completos (`es_core_news_sm`, `en_core_web_sm`) requieren descarga inicial pero luego funcionan offline
- Los modelos base funcionan completamente offline pero con capacidades limitadas
- Los diccionarios pueden actualizarse sin reiniciar el servidor usando `reload_dictionary()`
- El sistema detecta automáticamente el idioma del texto
