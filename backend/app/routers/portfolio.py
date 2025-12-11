"""Endpoints para gestión de cartera."""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from sqlalchemy import desc, asc, and_, or_
from typing import Optional
from datetime import datetime, timezone
import logging
import json

from app.database import get_db, PortfolioItem
from app.models import (
    PortfolioItemCreate,
    PortfolioItemResponse,
    PortfolioListResponse,
    AssetRecommendationsResponse,
    AllRecommendationsResponse,
    TradingRecommendation
)
from app.database import TradingRecommendation as TradingRecommendationDB
from app.services.trading_recommendations_service import TradingRecommendationsService
from app.services.recommendation_audit_service import RecommendationAuditService
from app.services.risk_service import RiskService
from sqlalchemy import and_, or_, desc, asc

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/portfolio", tags=["portfolio"])

# Inicializar servicios
recommendations_service = TradingRecommendationsService()
audit_service = RecommendationAuditService()


@router.post("", response_model=PortfolioItemResponse, status_code=status.HTTP_201_CREATED)
async def create_portfolio_item(
    request: Request,
    item: PortfolioItemCreate,
    db: Session = Depends(get_db)
):
    """
    Crea un nuevo item en la cartera.
    """
    try:
        db_item = PortfolioItem(
            asset_type=item.asset_type,
            name=item.name,
            symbol=item.symbol,
            quantity=item.quantity,
            price=item.price,
            total_value=item.total_value,
            currency=item.currency,
            notes=item.notes
        )
        db.add(db_item)
        db.commit()
        db.refresh(db_item)
        
        logger.info(f"Item de cartera creado: ID {db_item.id} - {item.name}")
        return PortfolioItemResponse.model_validate(db_item)
        
    except ValueError as e:
        logger.warning(f"Error de validación al crear item de cartera: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error inesperado al crear item de cartera: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al crear el item de cartera"
        )


@router.get("", response_model=PortfolioListResponse)
async def list_portfolio(
    db: Session = Depends(get_db)
):
    """
    Lista todos los items de la cartera ordenados por fecha de actualización.
    """
    try:
        total = db.query(PortfolioItem).count()
        items = db.query(PortfolioItem).order_by(desc(PortfolioItem.updated_at)).all()
        
        return PortfolioListResponse(
            items=[PortfolioItemResponse.model_validate(item) for item in items],
            total=total
        )
    except Exception as e:
        logger.error(f"Error al listar cartera: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al listar la cartera"
        )


@router.get("/risk-dashboard")
async def get_risk_dashboard(
    top_n: int = 5,
    db: Session = Depends(get_db)
):
    """
    Obtiene el dashboard de riesgo con métricas consolidadas de la cartera.
    Incluye valor total, concentraciones, exposición por sector y métricas de riesgo.
    """
    try:
        portfolio_items_db = db.query(PortfolioItem).all()
        portfolio_items = [PortfolioItemResponse.model_validate(item) for item in portfolio_items_db]
        
        risk_service = RiskService()
        dashboard = risk_service.calculate_risk_dashboard(portfolio_items, top_n=top_n)
        
        return dashboard
    except Exception as e:
        logger.error(f"Error al calcular dashboard de riesgo: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al calcular el dashboard de riesgo"
        )


@router.put("/{item_id}", response_model=PortfolioItemResponse)
async def update_portfolio_item(
    request: Request,
    item_id: int,
    item: PortfolioItemCreate,
    db: Session = Depends(get_db)
):
    """
    Actualiza un item de la cartera.
    """
    try:
        db_item = db.query(PortfolioItem).filter(PortfolioItem.id == item_id).first()
        
        if not db_item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Item de cartera con ID {item_id} no encontrado"
            )
        
        # Actualizar campos
        db_item.asset_type = item.asset_type
        db_item.name = item.name
        db_item.symbol = item.symbol
        db_item.quantity = item.quantity
        db_item.price = item.price
        db_item.total_value = item.total_value
        db_item.currency = item.currency
        db_item.notes = item.notes
        # updated_at se actualiza automáticamente por el modelo
        
        db.commit()
        db.refresh(db_item)
        
        logger.info(f"Item de cartera actualizado: ID {item_id}")
        return PortfolioItemResponse.model_validate(db_item)
        
    except HTTPException:
        raise
    except ValueError as e:
        logger.warning(f"Error de validación al actualizar item de cartera: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error al actualizar item de cartera {item_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al actualizar el item de cartera"
        )


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_portfolio_item(
    item_id: int,
    db: Session = Depends(get_db)
):
    """
    Elimina un item de la cartera por ID.
    """
    try:
        item = db.query(PortfolioItem).filter(PortfolioItem.id == item_id).first()
        
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Item de cartera con ID {item_id} no encontrado"
            )
        
        db.delete(item)
        db.commit()
        
        logger.info(f"Item de cartera eliminado: ID {item_id}")
        return None
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al eliminar item de cartera {item_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al eliminar el item de cartera"
        )


@router.get("/recommendations", response_model=AllRecommendationsResponse)
async def get_all_recommendations(
    db: Session = Depends(get_db)
):
    """
    Obtiene recomendaciones de trading contextualizadas para todos los activos en cartera.
    
    Para cada activo proporciona:
    - Noticias clave relacionadas
    - Clasificación (sentimiento, relevancia, urgencia)
    - Resumen de impacto
    - Recomendaciones accionables con umbrales cuantitativos
    - Features de mercado (precio, volumen, ATR)
    """
    try:
        recommendations = recommendations_service.get_all_recommendations(db)
        
        logger.info(f"Recomendaciones generadas para {len(recommendations)} activos")
        
        return AllRecommendationsResponse(
            recommendations=recommendations,
            total_assets=len(recommendations),
            generated_at=recommendations[0]["generated_at"] if recommendations else ""
        )
        
    except Exception as e:
        logger.error(f"Error al generar recomendaciones: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno al generar recomendaciones: {str(e)}"
        )


@router.get("/recommendations/{item_id}", response_model=AssetRecommendationsResponse)
async def get_asset_recommendations(
    item_id: int,
    db: Session = Depends(get_db)
):
    """
    Obtiene recomendaciones de trading para un activo específico.
    
    Incluye:
    - Noticias clave relacionadas con clasificación
    - Resumen de impacto
    - Recomendaciones accionables (condición + acción + umbrales)
    - Features de mercado
    """
    try:
        portfolio_item = db.query(PortfolioItem).filter(PortfolioItem.id == item_id).first()
        
        if not portfolio_item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Activo con ID {item_id} no encontrado"
            )
        
        recommendations = recommendations_service.get_recommendations_for_asset(db, portfolio_item)
        
        logger.info(f"Recomendaciones generadas para activo {item_id} ({portfolio_item.name})")
        
        return AssetRecommendationsResponse(**recommendations)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al generar recomendaciones para activo {item_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno al generar recomendaciones: {str(e)}"
        )


@router.get("/recommendations/stored", response_model=dict)
async def get_stored_recommendations(
    skip: int = 0,
    limit: int = 100,
    signal: Optional[str] = None,
    min_confidence: Optional[float] = None,
    max_confidence: Optional[float] = None,
    action: Optional[str] = None,
    portfolio_item_id: Optional[int] = None,
    sort_by: str = "generated_at",
    sort_order: str = "desc",
    active_only: bool = True,
    db: Session = Depends(get_db)
):
    """
    Obtiene recomendaciones guardadas con filtros y ordenamientos.
    
    Filtros: signal, min_confidence, max_confidence, action, portfolio_item_id, active_only
    Ordenamientos: sort_by (generated_at, confidence, priority), sort_order (asc, desc)
    """
    try:
        query = db.query(TradingRecommendationDB)
        
        if active_only:
            query = query.filter(TradingRecommendationDB.is_active == True)
        
        if portfolio_item_id:
            query = query.filter(TradingRecommendationDB.portfolio_item_id == portfolio_item_id)
        
        if action:
            query = query.filter(TradingRecommendationDB.action == action.lower())
        
        if min_confidence is not None:
            query = query.filter(TradingRecommendationDB.confidence >= min_confidence)
        
        if max_confidence is not None:
            query = query.filter(TradingRecommendationDB.confidence <= max_confidence)
        
        # Ordenamiento
        if sort_by == "confidence":
            order_func = desc(TradingRecommendationDB.confidence) if sort_order == "desc" else asc(TradingRecommendationDB.confidence)
        elif sort_by == "priority":
            order_func = desc(TradingRecommendationDB.priority) if sort_order == "desc" else asc(TradingRecommendationDB.priority)
        else:
            order_func = desc(TradingRecommendationDB.generated_at) if sort_order == "desc" else asc(TradingRecommendationDB.generated_at)
        
        query = query.order_by(order_func)
        
        total = query.count()
        recommendations_db = query.offset(skip).limit(limit).all()
        
        recommendations = []
        for rec_db in recommendations_db:
            inputs_dict = None
            threshold_dict = None
            
            if rec_db.inputs:
                try:
                    inputs_dict = json.loads(rec_db.inputs)
                except (json.JSONDecodeError, TypeError):
                    inputs_dict = None
            
            if rec_db.threshold_data:
                try:
                    threshold_dict = json.loads(rec_db.threshold_data)
                except (json.JSONDecodeError, TypeError):
                    threshold_dict = None
            
            # Filtrar por señal si se especificó
            if signal and inputs_dict:
                sentiment = inputs_dict.get("sentiment", "").lower()
                if signal.lower() != sentiment:
                    continue
            
            portfolio_item = rec_db.portfolio_item
            
            rec_dict = {
                "recommendation_id": rec_db.id,
                "action": rec_db.action,
                "condition": rec_db.condition,
                "reason": rec_db.reason,
                "explanation": rec_db.explanation,
                "threshold": threshold_dict,
                "confidence": rec_db.confidence,
                "priority": rec_db.priority,
                "source_news_id": rec_db.source_news_id,
                "source_news_title": rec_db.source_news_title,
                "generated_at": rec_db.generated_at.isoformat() if rec_db.generated_at else None,
                "inputs": inputs_dict,
                "asset_info": {
                    "id": portfolio_item.id,
                    "name": portfolio_item.name,
                    "symbol": portfolio_item.symbol,
                    "asset_type": portfolio_item.asset_type
                } if portfolio_item else None,
                "is_active": rec_db.is_active
            }
            
            recommendations.append(rec_dict)
        
        if signal:
            total = len(recommendations)
        
        return {
            "items": recommendations,
            "total": total,
            "skip": skip,
            "limit": limit,
            "filters_applied": {
                "signal": signal,
                "action": action,
                "min_confidence": min_confidence,
                "max_confidence": max_confidence,
                "portfolio_item_id": portfolio_item_id,
                "active_only": active_only
            },
            "sorting": {
                "sort_by": sort_by,
                "sort_order": sort_order
            }
        }
        
    except Exception as e:
        logger.error(f"Error obteniendo recomendaciones guardadas: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno al obtener recomendaciones: {str(e)}"
        )


@router.put("/recommendations/{recommendation_id}/acknowledge", status_code=status.HTTP_200_OK)
async def acknowledge_recommendation(
    recommendation_id: int,
    db: Session = Depends(get_db)
):
    """Marca una recomendación como reconocida (revisada por el usuario)."""
    try:
        recommendation = db.query(TradingRecommendationDB).filter(
            TradingRecommendationDB.id == recommendation_id
        ).first()
        
        if not recommendation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Recomendación con ID {recommendation_id} no encontrada"
            )
        
        recommendation.acknowledged_at = datetime.now(timezone.utc)
        db.commit()
        
        audit_service.log_recommendation_acknowledgment(recommendation_id, recommendation.acknowledged_at)
        
        return {"message": "Recomendación reconocida", "recommendation_id": recommendation_id}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reconociendo recomendación {recommendation_id}: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno al reconocer recomendación: {str(e)}"
        )


@router.put("/recommendations/{recommendation_id}/execute", status_code=status.HTTP_200_OK)
async def execute_recommendation(
    recommendation_id: int,
    db: Session = Depends(get_db)
):
    """Marca una recomendación como ejecutada."""
    try:
        recommendation = db.query(TradingRecommendationDB).filter(
            TradingRecommendationDB.id == recommendation_id
        ).first()
        
        if not recommendation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Recomendación con ID {recommendation_id} no encontrada"
            )
        
        executed_at = datetime.now(timezone.utc)
        recommendation.executed_at = executed_at
        recommendation.is_active = False
        db.commit()
        
        audit_service.log_recommendation_execution(
            recommendation_id,
            executed_at,
            recommendation.action,
            recommendation.portfolio_item.name
        )
        
        return {"message": "Recomendación ejecutada", "recommendation_id": recommendation_id}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error ejecutando recomendación {recommendation_id}: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno al ejecutar recomendación: {str(e)}"
        )


@router.get("/recommendations/statistics", response_model=dict)
async def get_recommendation_statistics(
    portfolio_item_id: Optional[int] = None,
    days: int = 30,
    db: Session = Depends(get_db)
):
    """Obtiene estadísticas de recomendaciones para análisis y depuración."""
    try:
        statistics = audit_service.get_recommendation_statistics(
            db,
            portfolio_item_id=portfolio_item_id,
            days=days
        )
        return statistics
        
    except Exception as e:
        logger.error(f"Error obteniendo estadísticas: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno al obtener estadísticas: {str(e)}"
        )

