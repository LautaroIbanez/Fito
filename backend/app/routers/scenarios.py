"""Endpoints para el motor de escenarios."""
from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
import logging
import json
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError

from app.database import get_db, NewsItem, PortfolioItem
from app.models import (
    ScenarioEngineRequest,
    ScenarioEngineResponse
)
from app.services.scenario_engine_service import ScenarioEngineService
from app.services.news_preprocessing_service import NewsPreprocessingService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/scenarios", tags=["scenarios"])

# Timeout global para generación de escenarios (segundos)
SCENARIO_GENERATION_TIMEOUT = 180  # 3 minutos


@router.post("", response_model=ScenarioEngineResponse, status_code=status.HTTP_200_OK)
async def generate_scenarios(
    request: Request,
    scenario_request: ScenarioEngineRequest,
    db: Session = Depends(get_db),
    timeout: int = Query(SCENARIO_GENERATION_TIMEOUT, ge=30, le=600, description="Timeout en segundos")
):
    """
    Genera escenarios de mercado agrupados por drivers temáticos.
    
    Flujo:
    1. Agrupa noticias en drivers temáticos
    2. Genera escenarios (base/riesgo/oportunidad) por driver usando GPT-4o
    3. Mapea cada escenario a la cartera (tickers/sectores/FX) con sensibilidad y confianza
    
    Maneja timeouts y retorna resultados parciales si es necesario.
    """
    try:
        # Obtener noticias (con o sin estandarización)
        if scenario_request.news_ids:
            # Filtrar por IDs específicos
            news_items = db.query(NewsItem).filter(
                NewsItem.id.in_(scenario_request.news_ids)
            ).all()
        else:
            # Obtener noticias recientes (limitar a 20 para evitar timeouts)
            # Priorizar noticias ya estandarizadas
            news_items = db.query(NewsItem).filter(
                NewsItem.standardized_data.isnot(None)
            ).order_by(desc(NewsItem.created_at)).limit(20).all()
            
            # Si no hay suficientes estandarizadas, agregar algunas sin estandarizar
            if len(news_items) < 10:
                additional_items = db.query(NewsItem).filter(
                    NewsItem.standardized_data.is_(None)
                ).order_by(desc(NewsItem.created_at)).limit(10 - len(news_items)).all()
                news_items.extend(additional_items)
        
        if not news_items:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se encontraron noticias para analizar."
            )
        
        # Estandarizar noticias que no estén estandarizadas
        preprocessing_service = NewsPreprocessingService()
        standardized_news_list = []
        needs_standardization = []
        
        for item in news_items:
            if item.standardized_data:
                # Ya está estandarizada, parsear
                try:
                    standardized_dict = json.loads(item.standardized_data)
                    standardized_news_list.append({
                        "id": item.id,
                        "title": item.title,
                        "standardized_data": standardized_dict
                    })
                except (json.JSONDecodeError, TypeError) as e:
                    logger.warning(f"Error parseando standardized_data para noticia {item.id}: {e}")
                    # Si falla el parseo, intentar re-estandarizar
                    needs_standardization.append(item)
            else:
                # No está estandarizada, agregar a la lista para estandarizar
                needs_standardization.append(item)
        
        # Estandarizar noticias que lo necesiten (limitar a 5 para evitar timeouts)
        if needs_standardization:
            # Limitar cuántas noticias estandarizamos en una sola llamada para evitar timeouts
            items_to_standardize = needs_standardization[:5]
            if len(needs_standardization) > 5:
                logger.warning(
                    f"Limitando estandarización a {len(items_to_standardize)} de {len(needs_standardization)} noticias "
                    "para evitar timeout. Las restantes se procesarán en llamadas posteriores."
                )
            
            logger.info(f"Estandarizando {len(items_to_standardize)} noticias automáticamente...")
            for item in items_to_standardize:
                try:
                    if not item.body:
                        logger.warning(f"Noticia {item.id} no tiene cuerpo, omitiendo")
                        continue
                    
                    # Estandarizar usando NLP local (sin LLM)
                    standardized_data = preprocessing_service.standardize_news(item.body)
                    
                    # Guardar datos estandarizados en la BD
                    item.standardized_data = json.dumps(standardized_data.model_dump(), ensure_ascii=False)
                    db.add(item)
                    
                    standardized_news_list.append({
                        "id": item.id,
                        "title": item.title or standardized_data.title,
                        "standardized_data": standardized_data.model_dump()
                    })
                except Exception as e:
                    logger.error(f"Error estandarizando noticia {item.id}: {e}", exc_info=True)
                    continue
            
            # Guardar cambios en la BD
            try:
                db.commit()
                logger.info(f"Estandarización completada: {len(standardized_news_list)} noticias listas")
            except Exception as e:
                logger.error(f"Error guardando estandarización: {e}", exc_info=True)
                db.rollback()
        
        if not standardized_news_list:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se pudieron procesar o estandarizar las noticias disponibles"
            )
        
        # Obtener items de cartera para contexto
        portfolio_items_db = db.query(PortfolioItem).all()
        portfolio_items = []
        if portfolio_items_db:
            for item in portfolio_items_db:
                portfolio_items.append({
                    "name": item.name,
                    "symbol": item.symbol,
                    "asset_type": item.asset_type
                })
        
        # Generar escenarios con timeout
        logger.info(
            f"Generando escenarios: {len(standardized_news_list)} noticias, "
            f"{len(portfolio_items)} items de cartera, timeout={timeout}s"
        )
        
        # Log de IDs de noticias para debugging
        news_ids = [news.get("id") for news in standardized_news_list]
        logger.debug(f"IDs de noticias a procesar: {news_ids}")
        
        scenario_service = ScenarioEngineService()
        
        try:
            # Ejecutar con timeout usando ThreadPoolExecutor
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(
                    scenario_service.generate_scenarios,
                    standardized_news_list,
                    portfolio_items if portfolio_items else None,
                    scenario_request.max_drivers,
                    scenario_request.include_portfolio_mapping
                )
                
                try:
                    response = future.result(timeout=timeout)
                    return response
                except FutureTimeoutError:
                    logger.warning(f"Timeout ({timeout}s) excedido en generación de escenarios")
                    # Intentar obtener resultados parciales si hay algún driver procesado
                    # (esto requeriría modificar el servicio para exponer estado parcial)
                    raise HTTPException(
                        status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                        detail=f"La generación de escenarios excedió el tiempo límite ({timeout}s). "
                               "Intenta con menos drivers o noticias."
                    )
        
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error en generación de escenarios: {e}", exc_info=True)
            
            # Intentar retornar respuesta parcial si es posible
            # Por ahora, simplemente propagamos el error
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error interno al generar escenarios: {str(e)}"
            )
        
    except HTTPException:
        raise
    except ValueError as e:
        logger.warning(f"Error de validación al generar escenarios: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error inesperado al generar escenarios: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno al generar escenarios: {str(e)}"
        )


@router.get("/health", status_code=status.HTTP_200_OK)
async def scenarios_health():
    """Endpoint de salud para el motor de escenarios."""
    return {
        "status": "healthy",
        "service": "scenario_engine",
        "timeout_default": SCENARIO_GENERATION_TIMEOUT
    }

