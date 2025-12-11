"""Endpoints para análisis de noticias."""
from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
import logging
import json
from datetime import datetime

from app.database import get_db, NewsItem, PortfolioItem
from app.models import (
    AnalysisRequest, AnalysisResponse,
    PortfolioAnalysisRequest, PortfolioAnalysisResponse,
    StandardizedNewsData
)
from app.services.openai_service import OpenAIService
from app.services.news_scoring_service import NewsScoringService
from app.services.portfolio_analysis_service import PortfolioAnalysisService
from app.models import NewsItemResponse, PortfolioItemResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/analysis", tags=["analysis"])


@router.post("", response_model=AnalysisResponse, status_code=status.HTTP_200_OK)
async def generate_analysis(
    request: Request,
    analysis_request: AnalysisRequest,
    db: Session = Depends(get_db)
):
    # Rate limiting aplicado a nivel de aplicación
    """
    Genera un análisis consolidado de todas las noticias guardadas usando OpenAI.
    
    Requiere al menos una noticia guardada.
    """
    try:
        # El request de análisis no necesita parámetros, pero mantenemos el modelo para consistencia
        # Obtener todas las noticias ordenadas por fecha
        news_items = db.query(NewsItem).order_by(desc(NewsItem.created_at)).all()
        
        if not news_items:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Se requiere al menos una noticia para generar el análisis"
            )
        
        # Convertir a modelos de respuesta
        news_responses = [NewsItemResponse.model_validate(item) for item in news_items]
        
        # Obtener items de cartera
        portfolio_items = db.query(PortfolioItem).order_by(desc(PortfolioItem.updated_at)).all()
        portfolio_responses = [PortfolioItemResponse.model_validate(item) for item in portfolio_items] if portfolio_items else []
        
        # Calcular scores y ordenar noticias por relevancia
        scoring_service = NewsScoringService()
        scored_news = scoring_service.score_and_sort_news(news_responses, portfolio_responses if portfolio_responses else None)
        # Usar noticias ordenadas por score
        news_responses = [item for item, score_dict in scored_news]
        
        # Agregar scores a los items
        for item, score_dict in scored_news:
            item.score = score_dict["score"]
            item.score_components = score_dict["components"]
            item.is_obsolete = score_dict["components"]["is_obsolete"]
        
        # Generar análisis con OpenAI (incluyendo cartera)
        logger.info(f"Generando análisis para {len(news_responses)} noticias y {len(portfolio_responses)} items de cartera")
        openai_service = OpenAIService()
        analysis_result = openai_service.generate_analysis(news_responses, portfolio_responses if portfolio_responses else None)
        
        # Preparar respuesta
        generated_at = datetime.utcnow().isoformat()
        version = generated_at  # Usar timestamp como versión
        
        return AnalysisResponse(
            analysis={
                "raw": analysis_result["raw_analysis"],
                "structured": analysis_result["structured_analysis"],
                "model_used": analysis_result["model_used"],
                "tokens_used": analysis_result.get("tokens_used")
            },
            news_count=len(news_responses),
            portfolio_count=len(portfolio_responses),
            generated_at=generated_at,
            version=version
        )
        
    except HTTPException:
        raise
    except ValueError as e:
        logger.warning(f"Error de validación al generar análisis: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error inesperado al generar análisis: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno al generar análisis: {str(e)}"
        )


@router.post("/portfolio", response_model=PortfolioAnalysisResponse, status_code=status.HTTP_200_OK)
async def analyze_portfolio(
    request: Request,
    analysis_request: PortfolioAnalysisRequest,
    db: Session = Depends(get_db)
):
    """
    Analiza el impacto de noticias estandarizadas en la cartera desde perspectiva de inversor experimentado.
    
    Solo utiliza campos estandarizados (no texto crudo de artículos).
    Para cada noticia proporciona:
    - Impacto en tesis de inversión
    - Banderas de riesgo
    - Nivel de confianza (high/med/low)
    - Próxima acción (watch/add/trim/exit)
    - 1-2 preguntas de seguimiento para diligencia
    
    Incluye vista agregada: top 3 oportunidades, top 3 riesgos, y lectura del mercado.
    """
    try:
        # Obtener noticias estandarizadas
        if analysis_request.news_ids:
            # Filtrar por IDs específicos
            news_items = db.query(NewsItem).filter(
                NewsItem.id.in_(analysis_request.news_ids),
                NewsItem.standardized_data.isnot(None)
            ).all()
        else:
            # Obtener todas las noticias con datos estandarizados
            news_items = db.query(NewsItem).filter(
                NewsItem.standardized_data.isnot(None)
            ).order_by(desc(NewsItem.created_at)).all()
        
        if not news_items:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se encontraron noticias estandarizadas para analizar. "
                       "Usa el endpoint /api/news/standardize para crear noticias estandarizadas primero."
            )
        
        # Parsear datos estandarizados
        standardized_news_list = []
        for item in news_items:
            try:
                standardized_dict = json.loads(item.standardized_data)
                standardized_news_list.append({
                    "id": item.id,
                    "title": item.title,
                    "standardized_data": standardized_dict
                })
            except (json.JSONDecodeError, TypeError) as e:
                logger.warning(f"Error parseando standardized_data para noticia {item.id}: {e}")
                continue
        
        if not standardized_news_list:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se pudieron parsear datos estandarizados de las noticias"
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
        
        # Generar análisis usando el servicio
        logger.info(f"Generando análisis de cartera para {len(standardized_news_list)} noticias estandarizadas")
        analysis_service = PortfolioAnalysisService()
        analysis_response = analysis_service.analyze_portfolio(
            standardized_news_list,
            portfolio_items if portfolio_items else None
        )
        
        return analysis_response
        
    except HTTPException:
        raise
    except ValueError as e:
        logger.warning(f"Error de validación al analizar cartera: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error inesperado al analizar cartera: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno al analizar cartera: {str(e)}"
        )


@router.post("/news-summaries", response_model=dict, status_code=status.HTTP_200_OK)
async def generate_news_summaries(
    request: Request,
    max_items: int = Query(10, description="Número máximo de noticias a analizar"),
    db: Session = Depends(get_db)
):
    """
    Genera resúmenes sintéticos (2-3 frases) y explicaciones breves para cada noticia.
    También incluye impactos potenciales en la cartera actual.
    
    Diseñado para el widget del asistente IA que muestra análisis por noticia individual.
    """
    try:
        # Obtener noticias recientes ordenadas por score
        news_items = db.query(NewsItem).order_by(desc(NewsItem.created_at)).limit(max_items).all()
        
        if not news_items:
            return {
                "summaries": [],
                "portfolio_impacts": [],
                "suggestions": [],
                "generated_at": datetime.utcnow().isoformat(),
                "news_count": 0
            }
        
        # Convertir a modelos de respuesta
        news_responses = [NewsItemResponse.model_validate(item) for item in news_items]
        
        # Obtener los últimos items de cartera (ordenados por fecha de actualización, más recientes primero)
        portfolio_items = db.query(PortfolioItem).order_by(desc(PortfolioItem.updated_at)).limit(50).all()
        portfolio_responses = [PortfolioItemResponse.model_validate(item) for item in portfolio_items] if portfolio_items else []
        
        logger.info(f"Obtenidos {len(portfolio_responses)} items de cartera para análisis de resúmenes")
        
        # Usar el servicio de análisis en dos pasos
        from app.services.two_step_analysis_service import TwoStepAnalysisService
        
        two_step_service = TwoStepAnalysisService()
        
        # Paso 1: Normalizar noticias
        normalized_news = two_step_service.normalize_news_batch(news_responses[:max_items])
        
        # Paso 2: Generar análisis de inversor
        analysis_result = two_step_service.analyze_normalized_news(
            normalized_news,
            portfolio_responses if portfolio_responses else None
        )
        
        # Calcular scores y agregarlos a los summaries
        scoring_service = NewsScoringService()
        scored_news = scoring_service.score_and_sort_news(news_responses, portfolio_responses if portfolio_responses else None)
        
        # Crear mapa de scores por news_id
        score_map = {}
        for item, score_dict in scored_news:
            score_map[item.id] = {
                "score": score_dict["score"],
                "sentiment": score_dict["components"].get("sentiment_type", "neutral")
            }
        
        # Agregar scores a los summaries
        for summary in analysis_result["summaries"]:
            news_id = summary.get("news_id")
            if news_id in score_map:
                summary["score"] = score_map[news_id]["score"]
                summary["sentiment"] = score_map[news_id]["sentiment"]
            else:
                summary["score"] = 0.0
                summary["sentiment"] = "neutral"
        
        return analysis_result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error inesperado al generar resúmenes de noticias: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno al generar resúmenes: {str(e)}"
        )

