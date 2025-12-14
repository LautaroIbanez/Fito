# Troubleshooting - Error de Importación de spaCy

## Problema

Al iniciar el servidor con `uvicorn app.main:app --reload --port 8001`, aparece el error:
```
ModuleNotFoundError: No module named 'spacy'
```

Sin embargo, cuando se ejecuta directamente con Python del venv, la importación funciona correctamente.

## Causa

El problema está relacionado con cómo uvicorn inicia el proceso hijo cuando usa `--reload`. El proceso hijo puede no estar usando el entorno virtual correcto.

## Soluciones

### Solución 1: Usar uvicorn sin --reload (Recomendado para validación)

```bash
cd backend
.\venv\Scripts\Activate.ps1
uvicorn app.main:app --port 8001
```

Esto evitará el problema del proceso hijo y permitirá validar que todo funciona.

### Solución 2: Verificar que el venv esté activado

Asegúrate de que el entorno virtual esté activado antes de ejecutar uvicorn:

```powershell
cd backend
.\venv\Scripts\Activate.ps1
# Verificar que estás usando el Python correcto
python --version
which python  # Debe mostrar la ruta del venv
uvicorn app.main:app --reload --port 8001
```

### Solución 3: Usar el Python del venv directamente

```bash
cd backend
.\venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8001
```

Esto fuerza a usar el Python del venv específicamente.

### Solución 4: Reinstalar spaCy en el venv

Si el problema persiste, reinstala spaCy:

```bash
cd backend
.\venv\Scripts\Activate.ps1
pip uninstall spacy
pip install spacy>=3.7.0
```

## Verificación

Para verificar que todo está correcto:

```bash
cd backend
.\venv\Scripts\python.exe -c "from app.main import app; print('OK')"
```

Si esto funciona, el problema es solo con el proceso de reload de uvicorn.

## Estado Actual

✅ **spaCy está instalado** en el venv (versión 3.8.11)
✅ **La aplicación se importa correctamente** cuando se usa el Python del venv directamente
✅ **El problema es específico** del proceso de reload de uvicorn

## Recomendación

Para validar el flujo completo sin LLM, usa:

```bash
cd backend
.\venv\Scripts\Activate.ps1
uvicorn app.main:app --port 8001
```

Esto evitará el problema del reload y permitirá validar que:
- ✅ No hay llamadas a `api.openai.com`
- ✅ Los endpoints funcionan con motor local
- ✅ Los logs muestran `[MOTOR LOCAL]`
