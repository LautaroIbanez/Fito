"""Aplicación principal FastAPI."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import logging

from app.config import (
    validate_config, 
    RATE_LIMIT_PER_MINUTE,
    OPENAI_MODEL,
    OPENAI_TEMPERATURE,
    OPENAI_MAX_TOKENS,
    validate_openai_model
)
from app.database import init_db
from app.routers import news, analysis, portfolio, suggestions, opportunities, normalized_news, scenarios

# Validar configuración antes de iniciar
validate_config()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Verificar y loguear configuración del modelo OpenAI
is_valid_model, model_message = validate_openai_model()
if is_valid_model:
    logger.info("=" * 60)
    logger.info("CONFIGURACIÓN DE OPENAI:")
    logger.info(f"  Modelo: {OPENAI_MODEL}")
    logger.info(f"  Temperatura: {OPENAI_TEMPERATURE}")
    logger.info(f"  Máximo de tokens: {OPENAI_MAX_TOKENS}")
    logger.info(f"  Estado: {model_message}")
    logger.info("=" * 60)
else:
    logger.warning("=" * 60)
    logger.warning("ADVERTENCIA DE CONFIGURACIÓN DE OPENAI:")
    logger.warning(f"  {model_message}")
    logger.warning("=" * 60)

# Inicializar base de datos
init_db()
logger.info("Base de datos inicializada")

# Ejecutar migraciones
try:
    from app.migrations import run_migrations
    run_migrations()
except Exception as e:
    logger.error(f"Error ejecutando migraciones: {e}", exc_info=True)
    # Continuar aunque falle la migración para no bloquear el inicio

# Rate limiter
limiter = Limiter(key_func=get_remote_address)
app = FastAPI(
    title="News Analyzer API",
    description="API para análisis de noticias con OpenAI",
    version="1.0.0"
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(news.router, prefix="/api")
app.include_router(analysis.router, prefix="/api")
app.include_router(portfolio.router, prefix="/api")
app.include_router(suggestions.router, prefix="/api")
app.include_router(opportunities.router, prefix="/api")
app.include_router(normalized_news.router, prefix="/api")
app.include_router(scenarios.router, prefix="/api")


@app.get("/")
async def root():
    """Endpoint raíz."""
    return {
        "message": "News Analyzer API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health():
    """Endpoint de salud."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

