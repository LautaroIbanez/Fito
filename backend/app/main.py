"""Aplicación principal FastAPI."""
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from typing import Optional
import logging

from app.config import (
    RATE_LIMIT_PER_MINUTE,
    OPENAI_MODEL,
    OPENAI_TEMPERATURE,
    OPENAI_MAX_TOKENS
)
from app.database import init_db
from app.routers import news, analysis, portfolio, suggestions, opportunities, normalized_news, scenarios

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Log de configuración del motor local
logger.info("=" * 60)
logger.info("MOTOR LOCAL ACTIVO (SIN LLM)")
logger.info("  Resumen: Extractivo (NLP local)")
logger.info("  Drivers: Detección por keywords/entidades")
logger.info("  Escenarios: Plantillas 'si-entonces'")
logger.info("  Mapeo: Reglas basadas en coincidencias")
logger.info("  Sin llamadas HTTP externas")
logger.info("  Sin costos de API")
logger.info("=" * 60)

# Nota: OpenAI solo se usa en modo legacy (use_extractive=False o use_rule_based=False)
# La validación de OpenAI se omite ya que no es requerida para el flujo estándar

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


@app.get("/api/token-stats")
async def get_token_stats():
    """Endpoint para obtener estadísticas de tokens usados."""
    from app.services.token_logger import token_logger
    return token_logger.get_session_summary()


@app.get("/api/cache-stats")
async def get_cache_stats():
    """Endpoint para obtener estadísticas del caché."""
    from app.services.prompt_cache_service import PromptCacheService
    cache_service = PromptCacheService()
    cache_service.clear_expired()  # Limpiar expirados antes de mostrar stats
    return cache_service.get_stats()


@app.post("/api/cache/clear")
async def clear_cache(prompt_type: Optional[str] = Query(None)):
    """Endpoint para limpiar el caché (opcionalmente por tipo)."""
    from app.services.prompt_cache_service import PromptCacheService
    cache_service = PromptCacheService()
    cache_service.invalidate(prompt_type=prompt_type)
    cache_service.clear_expired()
    return {
        "message": f"Caché limpiado{' para tipo ' + prompt_type if prompt_type else ''}",
        "stats": cache_service.get_stats()
    }


@app.get("/api/local-nlp/test")
async def test_local_nlp(text: Optional[str] = Query("Apple anunció crecimiento récord en ventas", description="Texto a analizar")):
    """Endpoint de prueba para el sistema de NLP local."""
    try:
        from app.services.local_nlp import get_local_nlp_service
        
        nlp_service = get_local_nlp_service()
        
        if not nlp_service.is_ready():
            return {
                "status": "error",
                "message": "Servicio de NLP no está listo"
            }
        
        result = nlp_service.analyze_news(text)
        
        return {
            "status": "success",
            "is_ready": nlp_service.is_ready(),
            "analysis": result
        }
    except Exception as e:
        import traceback
        return {
            "status": "error",
            "message": str(e),
            "traceback": traceback.format_exc()
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

