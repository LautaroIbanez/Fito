"""Endpoints para gestión de alertas y triggers."""
from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
import logging
from typing import Optional

from app.database import get_db, AlertTrigger, AlertHistory
from app.models import (
    AlertTriggerCreate,
    AlertTriggerUpdate,
    AlertTriggerResponse,
    AlertTriggerListResponse,
    AlertHistoryResponse,
    AlertHistoryListResponse
)
from app.services.alert_service import AlertService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/alerts", tags=["alerts"])


# ==================== Trigger CRUD ====================

@router.post("/triggers", response_model=AlertTriggerResponse, status_code=status.HTTP_201_CREATED)
async def create_trigger(
    request: Request,
    trigger: AlertTriggerCreate,
    db: Session = Depends(get_db)
):
    """
    Crea un nuevo trigger de alerta.
    """
    try:
        db_trigger = AlertTrigger(
            name=trigger.name,
            symbol=trigger.symbol,
            asset_type=trigger.asset_type,
            price_trigger_type=trigger.price_trigger_type,
            price_threshold=trigger.price_threshold,
            gap_threshold=trigger.gap_threshold,
            require_recent_news=trigger.require_recent_news,
            news_relevance_threshold=trigger.news_relevance_threshold,
            news_max_age_hours=trigger.news_max_age_hours,
            is_active=True
        )
        db.add(db_trigger)
        db.commit()
        db.refresh(db_trigger)
        
        logger.info(f"Trigger creado: ID {db_trigger.id} - {trigger.name}")
        return AlertTriggerResponse.model_validate(db_trigger)
        
    except ValueError as e:
        logger.warning(f"Error de validación al crear trigger: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error inesperado al crear trigger: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al crear el trigger"
        )


@router.get("/triggers", response_model=AlertTriggerListResponse)
async def list_triggers(
    is_active: Optional[bool] = Query(None, description="Filtrar por estado activo/inactivo"),
    db: Session = Depends(get_db)
):
    """
    Lista todos los triggers de alertas.
    """
    try:
        query = db.query(AlertTrigger)
        
        if is_active is not None:
            query = query.filter(AlertTrigger.is_active == is_active)
        
        items = query.order_by(desc(AlertTrigger.created_at)).all()
        total = len(items)
        
        return AlertTriggerListResponse(
            items=[AlertTriggerResponse.model_validate(item) for item in items],
            total=total
        )
    except Exception as e:
        logger.error(f"Error al listar triggers: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al listar triggers"
        )


@router.get("/triggers/{trigger_id}", response_model=AlertTriggerResponse)
async def get_trigger(
    trigger_id: int,
    db: Session = Depends(get_db)
):
    """
    Obtiene un trigger por ID.
    """
    try:
        trigger = db.query(AlertTrigger).filter(AlertTrigger.id == trigger_id).first()
        
        if not trigger:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Trigger con ID {trigger_id} no encontrado"
            )
        
        return AlertTriggerResponse.model_validate(trigger)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al obtener trigger {trigger_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al obtener el trigger"
        )


@router.put("/triggers/{trigger_id}", response_model=AlertTriggerResponse)
async def update_trigger(
    trigger_id: int,
    trigger_update: AlertTriggerUpdate,
    db: Session = Depends(get_db)
):
    """
    Actualiza un trigger existente.
    """
    try:
        trigger = db.query(AlertTrigger).filter(AlertTrigger.id == trigger_id).first()
        
        if not trigger:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Trigger con ID {trigger_id} no encontrado"
            )
        
        # Actualizar campos proporcionados
        update_data = trigger_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(trigger, field, value)
        
        db.commit()
        db.refresh(trigger)
        
        logger.info(f"Trigger actualizado: ID {trigger_id}")
        return AlertTriggerResponse.model_validate(trigger)
    except HTTPException:
        raise
    except ValueError as e:
        logger.warning(f"Error de validación al actualizar trigger: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error inesperado al actualizar trigger {trigger_id}: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al actualizar el trigger"
        )


@router.delete("/triggers/{trigger_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_trigger(
    trigger_id: int,
    db: Session = Depends(get_db)
):
    """
    Elimina un trigger por ID.
    """
    try:
        trigger = db.query(AlertTrigger).filter(AlertTrigger.id == trigger_id).first()
        
        if not trigger:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Trigger con ID {trigger_id} no encontrado"
            )
        
        db.delete(trigger)
        db.commit()
        
        logger.info(f"Trigger eliminado: ID {trigger_id}")
        return None
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al eliminar trigger {trigger_id}: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al eliminar el trigger"
        )


# ==================== Alert History ====================

@router.get("/history", response_model=AlertHistoryListResponse)
async def get_alert_history(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    trigger_id: Optional[int] = Query(None, description="Filtrar por trigger ID"),
    db: Session = Depends(get_db)
):
    """
    Obtiene el historial de alertas entregadas.
    """
    try:
        query = db.query(AlertHistory)
        
        if trigger_id:
            query = query.filter(AlertHistory.trigger_id == trigger_id)
        
        total = query.count()
        items = query.order_by(desc(AlertHistory.triggered_at)).offset(skip).limit(limit).all()
        
        # Incluir nombre del trigger en la respuesta
        alert_responses = []
        for alert in items:
            alert_dict = AlertHistoryResponse.model_validate(alert).model_dump()
            trigger = db.query(AlertTrigger).filter(AlertTrigger.id == alert.trigger_id).first()
            if trigger:
                alert_dict["trigger_name"] = trigger.name
            alert_responses.append(AlertHistoryResponse(**alert_dict))
        
        return AlertHistoryListResponse(
            items=alert_responses,
            total=total
        )
    except Exception as e:
        logger.error(f"Error al obtener historial de alertas: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al obtener el historial de alertas"
        )


@router.post("/check", response_model=AlertHistoryListResponse)
async def check_triggers(
    db: Session = Depends(get_db)
):
    """
    Verifica manualmente todos los triggers activos.
    
    Nota: En producción, esto se ejecutaría automáticamente en intervalos regulares.
    Para esta versión, se puede llamar manualmente para testing.
    """
    try:
        alert_service = AlertService()
        
        # En producción, aquí obtendrías datos de precio de una API
        # Por ahora, se retornará una lista vacía si no hay datos de precio
        alerts_generated = alert_service.check_all_active_triggers(db, price_data_map=None)
        
        # Convertir a respuestas
        alert_responses = []
        for alert in alerts_generated:
            alert_dict = AlertHistoryResponse.model_validate(alert).model_dump()
            trigger = db.query(AlertTrigger).filter(AlertTrigger.id == alert.trigger_id).first()
            if trigger:
                alert_dict["trigger_name"] = trigger.name
            alert_responses.append(AlertHistoryResponse(**alert_dict))
        
        logger.info(f"Verificación de triggers completada. {len(alerts_generated)} alerta(s) generada(s)")
        
        return AlertHistoryListResponse(
            items=alert_responses,
            total=len(alert_responses)
        )
    except Exception as e:
        logger.error(f"Error al verificar triggers: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al verificar triggers"
        )





