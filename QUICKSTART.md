# Guía de Inicio Rápido - News Analyzer

## Requisitos Previos

- Python 3.8+
- Node.js 18+
- npm o yarn
- API Key de OpenAI

## Configuración Rápida

### 1. Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

**IMPORTANTE**: Editar `app/config.py` y reemplazar el placeholder de la API key:

```python
OPENAI_API_KEY = "tu_api_key_aqui"  # Reemplazar con tu key real
```

Ejecutar:
```bash
uvicorn app.main:app --reload --port 8000
```

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

La aplicación estará en `http://localhost:3001`

## Uso

1. Ingresa noticias usando el formulario (mínimo 200 caracteres)
2. Revisa las noticias guardadas en la lista
3. Genera un análisis consolidado con el botón "Generar Análisis"
4. Revisa el análisis estructurado por secciones
5. Copia o descarga el análisis completo

## Tests

```bash
cd backend
pytest tests/
```

## Solución de Problemas

### Error: "OPENAI_API_KEY no está configurada"
- Verifica que `backend/app/config.py` existe
- Verifica que la API key no tiene el valor placeholder
- Asegúrate de que el archivo no está en .gitignore (solo en producción)

### Error: "Se requiere al menos una noticia"
- Ingresa al menos una noticia antes de generar el análisis

### Error de validación en el formulario
- El cuerpo debe tener entre 200 y 10000 caracteres
- El título no puede exceder 200 caracteres
- La fuente no puede exceder 100 caracteres




