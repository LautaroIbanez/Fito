"""Endpoints para sugerencias de activos."""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from sqlalchemy import desc
import logging
import json
from datetime import datetime, timedelta, timezone

from app.database import get_db, AssetSuggestion, PortfolioItem
from app.models import (
    AssetSuggestionResponse,
    AssetSuggestionListResponse,
    GenerateSuggestionsRequest
)
from app.services.asset_suggestions_service import AssetSuggestionsService
from app.models import PortfolioItemResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/suggestions", tags=["suggestions"])


@router.post("/generate", response_model=AssetSuggestionListResponse, status_code=status.HTTP_200_OK)
async def generate_suggestions(
    request: Request,
    generate_request: GenerateSuggestionsRequest,
    db: Session = Depends(get_db)
):
    """
    Genera sugerencias de nuevos activos basadas en noticias y correlación con la cartera.
    """
    try:
        # Limpiar sugerencias expiradas
        expired_cutoff = datetime.now(timezone.utc)
        db.query(AssetSuggestion).filter(
            AssetSuggestion.expires_at < expired_cutoff
        ).delete()
        db.commit()
        
        # Generar nuevas sugerencias
        suggestions_service = AssetSuggestionsService()
        suggestions = suggestions_service.generate_suggestions(
            db,
            min_news_score=generate_request.min_news_score,
            max_correlation=generate_request.max_correlation,
            min_confidence=generate_request.min_confidence,
            max_suggestions=generate_request.max_suggestions
        )
        
        if not suggestions:
            return AssetSuggestionListResponse(
                items=[],
                total=0,
                portfolio_value=None
            )
        
        # Guardar sugerencias en base de datos
        expires_at = datetime.now(timezone.utc) + timedelta(days=7)  # Expiran en 7 días
        
        for suggestion in suggestions:
            suggestion.expires_at = expires_at
            db.add(suggestion)
        
        db.commit()
        
        # Calcular valor de cartera para respuesta
        portfolio_items_db = db.query(PortfolioItem).all()
        portfolio_value = 0.0
        for item in portfolio_items_db:
            if item.total_value:
                try:
                    portfolio_value += float(item.total_value.replace(',', ''))
                except (ValueError, AttributeError):
                    pass
            elif item.quantity and item.price:
                try:
                    portfolio_value += float(item.quantity.replace(',', '')) * float(item.price.replace(',', ''))
                except (ValueError, AttributeError):
                    pass
        
        # Construir respuestas
        suggestion_responses = []
        for suggestion in suggestions:
            news_ids = []
            if suggestion.supporting_news_ids:
                try:
                    news_ids = json.loads(suggestion.supporting_news_ids)
                except (ValueError, TypeError):
                    pass
            
            suggestion_responses.append(AssetSuggestionResponse(
                id=suggestion.id,
                asset_type=suggestion.asset_type,
                name=suggestion.name,
                symbol=suggestion.symbol,
                reason=suggestion.reason,
                reason_description=suggestion.reason_description,
                correlation_with_portfolio=suggestion.correlation_with_portfolio,
                news_relevance_score=suggestion.news_relevance_score,
                news_count=suggestion.news_count,
                suggested_position_size_pct=suggestion.suggested_position_size_pct,
                max_position_value=suggestion.max_position_value,
                confidence_level=suggestion.confidence_level,
                supporting_news_ids=news_ids,
                correlation_data_available=suggestion.correlation_data_available,
                generated_at=suggestion.generated_at.isoformat(),
                expires_at=suggestion.expires_at.isoformat() if suggestion.expires_at else None
            ))
        
        logger.info(f"Generadas {len(suggestions)} sugerencias de activos")
        
        return AssetSuggestionListResponse(
            items=suggestion_responses,
            total=len(suggestion_responses),
            portfolio_value=portfolio_value if portfolio_value > 0 else None
        )
        
    except Exception as e:
        logger.error(f"Error al generar sugerencias: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno al generar sugerencias: {str(e)}"
        )


@router.get("", response_model=AssetSuggestionListResponse)
async def list_suggestions(
    db: Session = Depends(get_db)
):
    """
    Lista todas las sugerencias activas (no expiradas).
    """
    try:
        # Filtrar sugerencias no expiradas
        now = datetime.now(timezone.utc)
        suggestions = db.query(AssetSuggestion).filter(
            (AssetSuggestion.expires_at.is_(None)) | (AssetSuggestion.expires_at > now)
        ).order_by(desc(AssetSuggestion.confidence_level)).all()
        
        # Calcular valor de cartera
        portfolio_items_db = db.query(PortfolioItem).all()
        portfolio_value = 0.0
        for item in portfolio_items_db:
            if item.total_value:
                try:
                    portfolio_value += float(item.total_value.replace(',', ''))
                except (ValueError, AttributeError):
                    pass
            elif item.quantity and item.price:
                try:
                    portfolio_value += float(item.quantity.replace(',', '')) * float(item.price.replace(',', ''))
                except (ValueError, AttributeError):
                    pass
        
        # Construir respuestas
        suggestion_responses = []
        for suggestion in suggestions:
            news_ids = []
            if suggestion.supporting_news_ids:
                try:
                    news_ids = json.loads(suggestion.supporting_news_ids)
                except (ValueError, TypeError):
                    pass
            
            suggestion_responses.append(AssetSuggestionResponse(
                id=suggestion.id,
                asset_type=suggestion.asset_type,
                name=suggestion.name,
                symbol=suggestion.symbol,
                reason=suggestion.reason,
                reason_description=suggestion.reason_description,
                correlation_with_portfolio=suggestion.correlation_with_portfolio,
                news_relevance_score=suggestion.news_relevance_score,
                news_count=suggestion.news_count,
                suggested_position_size_pct=suggestion.suggested_position_size_pct,
                max_position_value=suggestion.max_position_value,
                confidence_level=suggestion.confidence_level,
                supporting_news_ids=news_ids,
                correlation_data_available=suggestion.correlation_data_available,
                generated_at=suggestion.generated_at.isoformat(),
                expires_at=suggestion.expires_at.isoformat() if suggestion.expires_at else None
            ))
        
        return AssetSuggestionListResponse(
            items=suggestion_responses,
            total=len(suggestion_responses),
            portfolio_value=portfolio_value if portfolio_value > 0 else None
        )
    except Exception as e:
        logger.error(f"Error al listar sugerencias: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al listar sugerencias"
        )


@router.delete("/{suggestion_id}", status_code=status.HTTP_204_NO_CONTENT)
async def dismiss_suggestion(
    suggestion_id: int,
    db: Session = Depends(get_db)
):
    """
    Descarta una sugerencia específica.
    """
    try:
        suggestion = db.query(AssetSuggestion).filter(AssetSuggestion.id == suggestion_id).first()
        
        if not suggestion:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Sugerencia con ID {suggestion_id} no encontrada"
            )
        
        db.delete(suggestion)
        db.commit()
        
        logger.info(f"Sugerencia descartada: ID {suggestion_id}")
        return None
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al descartar sugerencia {suggestion_id}: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al descartar la sugerencia"
        )





