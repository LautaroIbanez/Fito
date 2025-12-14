# Fix: Conflicto de Nombres app/config.py vs app/config/

## Problema

Existía un conflicto de nombres entre:
- `app/config.py` (archivo de configuración principal)
- `app/config/` (directorio con diccionarios JSON para NLP local)

Python intentaba importar desde el directorio en lugar del archivo, causando:
```
ImportError: cannot import name 'validate_config' from 'app.config'
```

## Solución

Se renombró el directorio `app/config/` a `app/nlp_config/` para evitar el conflicto.

## Cambios Realizados

1. **Directorio renombrado:**
   - `app/config/` → `app/nlp_config/`
   - Contiene: `sentiment_dict.json`, `sectors_dict.json`, `risk_opportunity_dict.json`

2. **DictionaryLoader actualizado:**
   - `app/services/local_nlp/dictionary_loader.py`
   - Cambiado: `Path(__file__).parent.parent.parent / "config"` 
   - A: `Path(__file__).parent.parent.parent / "nlp_config"`

3. **main.py actualizado:**
   - Removidas importaciones no usadas de `validate_config` y `validate_openai_model`
   - Las funciones siguen disponibles en `config.py` pero no se usan en el flujo estándar

## Verificación

```bash
# Verificar que el directorio fue renombrado
ls app/nlp_config/

# Verificar que DictionaryLoader funciona
python -c "from app.services.local_nlp.dictionary_loader import DictionaryLoader; loader = DictionaryLoader(); print(loader.config_dir)"
# Debe mostrar: .../app/nlp_config

# Verificar que config.py se puede importar
python -c "from app.config import validate_config; print('OK')"
```

## Estado

✅ **Resuelto**: El conflicto de nombres ha sido eliminado y el servidor debería iniciar correctamente.
