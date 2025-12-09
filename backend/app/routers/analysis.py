"""Endpoints para análisis de noticias."""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from sqlalchemy import desc
import logging
from datetime import datetime

from app.database import get_db, NewsItem, PortfolioItem
from app.models import AnalysisRequest, AnalysisResponse
from app.services.openai_service import OpenAIService
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

