# Instrucciones para Ejecutar News Analyzer Manualmente

## Requisitos Previos

- Python 3.8+ instalado
- Node.js 18+ instalado
- npm instalado (viene con Node.js)

## Paso 1: Backend

### 1.1. Abrir una terminal y navegar al directorio backend

```bash
cd news-analyzer/backend
```

### 1.2. Crear y activar entorno virtual (solo la primera vez)

**Windows (PowerShell):**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**Windows (CMD):**
```cmd
python -m venv venv
venv\Scripts\activate.bat
```

**Linux/Mac:**
```bash
python -m venv venv
source venv/bin/activate
```

### 1.3. Instalar dependencias (solo la primera vez)

```bash
pip install -r requirements.txt
```

### 1.4. Verificar que la API key esté configurada

Abre el archivo `app/config.py` y verifica que `OPENAI_API_KEY` tenga tu API key real (no el placeholder).

### 1.5. Iniciar el servidor backend

```bash
uvicorn app.main:app --reload --port 8001
```

Deberías ver algo como:
```
INFO:     Uvicorn running on http://127.0.0.1:8001 (Press CTRL+C to quit)
INFO:     Started reloader process [...]
INFO:     Started server process [...]
INFO:     Application startup complete.
```

**Mantén esta terminal abierta** - el servidor seguirá corriendo hasta que presiones `CTRL+C`.

---

## Paso 2: Frontend

### 2.1. Abrir una NUEVA terminal (deja la del backend corriendo)

### 2.2. Navegar al directorio frontend

```bash
cd news-analyzer/frontend
```

### 2.3. Instalar dependencias (solo la primera vez)

```bash
npm install
```

### 2.4. Iniciar el servidor de desarrollo

```bash
npm run dev
```

Deberías ver algo como:
```
  VITE v5.x.x  ready in xxx ms

  ➜  Local:   http://localhost:3001/
  ➜  Network: use --host to expose
```

**Mantén esta terminal también abierta**.

---

## Paso 3: Usar la aplicación

1. Abre tu navegador
2. Ve a: `http://localhost:3001`
3. Deberías ver la interfaz de News Analyzer

---

## Comandos Rápidos (Resumen)

### Backend (Terminal 1):
```bash
cd news-analyzer/backend
.\venv\Scripts\Activate.ps1  # Windows PowerShell
# o: venv\Scripts\activate.bat  # Windows CMD
# o: source venv/bin/activate  # Linux/Mac

uvicorn app.main:app --reload --port 8001
```

### Frontend (Terminal 2):
```bash
cd news-analyzer/frontend
npm run dev
```

---

## Detener los Servidores

- **Backend**: Presiona `CTRL+C` en la terminal del backend
- **Frontend**: Presiona `CTRL+C` en la terminal del frontend

---

## Solución de Problemas

### Error: "puerto 8001 ya en uso"
- Cierra cualquier proceso que esté usando el puerto 8001
- O cambia el puerto en el comando: `--port 8002` (y actualiza `vite.config.ts`)

### Error: "No se puede activar el entorno virtual"
- En PowerShell, puede necesitar ejecutar: `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`
- Luego intenta activar nuevamente

### Error: "OPENAI_API_KEY no está configurada"
- Abre `backend/app/config.py`
- Reemplaza el placeholder con tu API key real

### El frontend no se conecta al backend
- Verifica que el backend esté corriendo en el puerto 8001
- Verifica que `frontend/vite.config.ts` tenga `target: 'http://localhost:8001'`
- Verifica que `frontend/src/services/api.ts` tenga la URL correcta

---

## Verificar que Todo Funciona

1. Backend saludable:
   ```bash
   curl http://localhost:8001/health
   ```
   Debería responder: `{"status":"healthy"}`

2. Backend listando noticias:
   ```bash
   curl http://localhost:8001/api/news
   ```
   Debería responder: `{"items":[],"total":0}` o una lista de noticias

3. Frontend accesible:
   - Abre `http://localhost:3001` en el navegador
   - Deberías ver la interfaz sin errores




