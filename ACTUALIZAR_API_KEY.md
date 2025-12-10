# Cómo Actualizar la API Key de OpenAI

## Problema

Si recibes el error:
```
Error code: 401 - Incorrect API key provided
```

Significa que la API key de OpenAI es incorrecta, ha expirado o fue revocada.

## Solución

### Paso 1: Obtener una nueva API Key

1. Ve a: https://platform.openai.com/account/api-keys
2. Inicia sesión en tu cuenta de OpenAI
3. Haz clic en "Create new secret key"
4. Copia la nueva API key (empieza con `sk-proj-` o `sk-`)

### Paso 2: Actualizar la configuración

1. Abre el archivo: `news-analyzer/backend/app/config.py`
2. Encuentra la línea:
   ```python
   OPENAI_API_KEY = "sk-proj-..."
   ```
3. Reemplaza el valor con tu nueva API key:
   ```python
   OPENAI_API_KEY = "sk-proj-tu_nueva_api_key_aqui"
   ```
4. Guarda el archivo

### Paso 3: Reiniciar el servidor

El servidor debería recargarse automáticamente con `--reload`, pero si no:
1. Detén el servidor (CTRL+C)
2. Inícialo nuevamente:
   ```bash
   uvicorn app.main:app --reload --port 8001
   ```

## Verificar que Funciona

Después de actualizar la key, intenta generar un análisis nuevamente. Si el error persiste:

1. Verifica que la key esté completa (no cortada)
2. Verifica que no tenga espacios al inicio o final
3. Verifica que la key esté entre comillas dobles
4. Verifica que el archivo se guardó correctamente

## Nota de Seguridad

⚠️ **IMPORTANTE**: El archivo `app/config.py` está en `.gitignore` para que no se suba al repositorio. 
Nunca compartas tu API key públicamente.


