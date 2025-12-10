"""Endpoints para log de decisiones."""
from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
import logging
from typing import List, Optional

from app.database import get_db, DecisionLog, DecisionEvaluation, PortfolioItem
from app.models import (
    DecisionLogCreate, DecisionLogResponse, DecisionLogListResponse,
    DecisionEvaluationUpdate, DecisionEvaluationResponse,
    DecisionStatisticsResponse, PortfolioItemResponse
)
from app.services.decision_service import DecisionService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/decisions", tags=["decisions"])


@router.post("", response_model=DecisionLogResponse, status_code=status.HTTP_201_CREATED)
async def create_decision(
    request: Request,
    decision_data: DecisionLogCreate,
    db: Session = Depends(get_db)
):
    """
    Crea un nuevo registro de decisión de trading.
    """
    # Verificar que el portfolio item existe
    portfolio_item = db.query(PortfolioItem).filter(PortfolioItem.id == decision_data.portfolio_item_id).first()
    if not portfolio_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"PortfolioItem con ID {decision_data.portfolio_item_id} no encontrado."
        )
    
    try:
        db_decision = DecisionLog(**decision_data.model_dump())
        db.add(db_decision)
        db.commit()
        db.refresh(db_decision)
        
        logger.info(f"Decisión creada: ID {db_decision.id} ({db_decision.decision_type}) para PortfolioItem {db_decision.portfolio_item_id}")
        
        # Retornar respuesta con información del portfolio item
        return DecisionLogResponse(
            id=db_decision.id,
            portfolio_item_id=db_decision.portfolio_item_id,
            portfolio_item_name=portfolio_item.name,
            portfolio_item_symbol=portfolio_item.symbol,
            decision_type=db_decision.decision_type,
            reason=db_decision.reason,
            signal_type=db_decision.signal_type,
            signal_reference=db_decision.signal_reference,
            expected_direction=db_decision.expected_direction,
            expected_price=db_decision.expected_price,
            expected_timeframe_days=db_decision.expected_timeframe_days,
            expected_outcome=db_decision.expected_outcome,
            status=db_decision.status,
            evaluation_window_days=db_decision.evaluation_window_days,
            decided_at=db_decision.decided_at.isoformat(),
            evaluated_at=db_decision.evaluated_at.isoformat() if db_decision.evaluated_at else None,
            evaluation=None
        )
    except Exception as e:
        logger.error(f"Error al crear decisión: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al crear la decisión"
        )


@router.get("", response_model=DecisionLogListResponse)
async def list_decisions(
    portfolio_item_id: Optional[int] = Query(None, description="Filtrar por PortfolioItem ID"),
    status_filter: Optional[str] = Query(None, pattern="^(pending|evaluated|cancelled)$", description="Filtrar por estado"),
    signal_type: Optional[str] = Query(None, description="Filtrar por tipo de señal"),
    decision_type: Optional[str] = Query(None, pattern="^(buy|sell|hold)$", description="Filtrar por tipo de decisión"),
    db: Session = Depends(get_db)
):
    """
    Lista todas las decisiones, con filtros opcionales.
    """
    try:
        query = db.query(DecisionLog)
        
        if portfolio_item_id:
            query = query.filter(DecisionLog.portfolio_item_id == portfolio_item_id)
        
        if status_filter:
            query = query.filter(DecisionLog.status == status_filter)
        
        if signal_type:
            query = query.filter(DecisionLog.signal_type == signal_type)
        
        if decision_type:
            query = query.filter(DecisionLog.decision_type == decision_type)
        
        decisions = query.order_by(desc(DecisionLog.decided_at)).all()
        
        # Obtener información de portfolio items
        portfolio_items_dict = {}
        portfolio_items_db = db.query(PortfolioItem).all()
        for item in portfolio_items_db:
            portfolio_items_dict[item.id] = item
        
        # Construir respuestas
        decision_responses = []
        pending_count = 0
        evaluated_count = 0
        
        for decision in decisions:
            portfolio_item = portfolio_items_dict.get(decision.portfolio_item_id)
            
            evaluation_response = None
            if decision.evaluation:
                evaluation_response = DecisionEvaluationResponse.model_validate(decision.evaluation)
            
            decision_responses.append(DecisionLogResponse(
                id=decision.id,
                portfolio_item_id=decision.portfolio_item_id,
                portfolio_item_name=portfolio_item.name if portfolio_item else None,
                portfolio_item_symbol=portfolio_item.symbol if portfolio_item else None,
                decision_type=decision.decision_type,
                reason=decision.reason,
                signal_type=decision.signal_type,
                signal_reference=decision.signal_reference,
                expected_direction=decision.expected_direction,
                expected_price=decision.expected_price,
                expected_timeframe_days=decision.expected_timeframe_days,
                expected_outcome=decision.expected_outcome,
                status=decision.status,
                evaluation_window_days=decision.evaluation_window_days,
                decided_at=decision.decided_at.isoformat(),
                evaluated_at=decision.evaluated_at.isoformat() if decision.evaluated_at else None,
                evaluation=evaluation_response
            ))
            
            if decision.status == 'pending':
                pending_count += 1
            elif decision.status == 'evaluated':
                evaluated_count += 1
        
        return DecisionLogListResponse(
            items=decision_responses,
            total=len(decision_responses),
            pending_count=pending_count,
            evaluated_count=evaluated_count
        )
    except Exception as e:
        logger.error(f"Error al listar decisiones: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al listar decisiones"
        )


@router.get("/{decision_id}", response_model=DecisionLogResponse)
async def get_decision(
    decision_id: int,
    db: Session = Depends(get_db)
):
    """
    Obtiene una decisión específica por ID.
    """
    decision = db.query(DecisionLog).filter(DecisionLog.id == decision_id).first()
    if not decision:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Decisión no encontrada")
    
    portfolio_item = db.query(PortfolioItem).filter(PortfolioItem.id == decision.portfolio_item_id).first()
    
    evaluation_response = None
    if decision.evaluation:
        evaluation_response = DecisionEvaluationResponse.model_validate(decision.evaluation)
    
    return DecisionLogResponse(
        id=decision.id,
        portfolio_item_id=decision.portfolio_item_id,
        portfolio_item_name=portfolio_item.name if portfolio_item else None,
        portfolio_item_symbol=portfolio_item.symbol if portfolio_item else None,
        decision_type=decision.decision_type,
        reason=decision.reason,
        signal_type=decision.signal_type,
        signal_reference=decision.signal_reference,
        expected_direction=decision.expected_direction,
        expected_price=decision.expected_price,
        expected_timeframe_days=decision.expected_timeframe_days,
        expected_outcome=decision.expected_outcome,
        status=decision.status,
        evaluation_window_days=decision.evaluation_window_days,
        decided_at=decision.decided_at.isoformat(),
        evaluated_at=decision.evaluated_at.isoformat() if decision.evaluated_at else None,
        evaluation=evaluation_response
    )


@router.post("/{decision_id}/evaluate", response_model=DecisionEvaluationResponse, status_code=status.HTTP_200_OK)
async def evaluate_decision(
    decision_id: int,
    force: bool = Query(False, description="Forzar evaluación aunque no haya pasado la ventana"),
    db: Session = Depends(get_db)
):
    """
    Evalúa una decisión comparando expectativa vs resultado.
    """
    decision = db.query(DecisionLog).filter(DecisionLog.id == decision_id).first()
    if not decision:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Decisión no encontrada")
    
    try:
        decision_service = DecisionService()
        evaluation = decision_service.evaluate_decision(db, decision, force=force)
        
        if not evaluation:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se pudo evaluar la decisión. Asegúrate de que haya pasado la ventana de evaluación o usa force=true."
            )
        
        return DecisionEvaluationResponse.model_validate(evaluation)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al evaluar decisión {decision_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno al evaluar la decisión: {str(e)}"
        )


@router.post("/evaluate-pending", status_code=status.HTTP_200_OK)
async def evaluate_all_pending(
    force_all: bool = Query(False, description="Evaluar todas aunque no hayan cumplido la ventana"),
    db: Session = Depends(get_db)
):
    """
    Evalúa automáticamente todas las decisiones pendientes que han cumplido su ventana.
    """
    try:
        decision_service = DecisionService()
        evaluations = decision_service.evaluate_pending_decisions(db, force_all=force_all)
        
        return {
            "evaluated_count": len(evaluations),
            "message": f"Evaluadas {len(evaluations)} decisiones"
        }
    except Exception as e:
        logger.error(f"Error al evaluar decisiones pendientes: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al evaluar decisiones pendientes"
        )


@router.put("/evaluation/{evaluation_id}", response_model=DecisionEvaluationResponse)
async def update_evaluation(
    evaluation_id: int,
    evaluation_data: DecisionEvaluationUpdate,
    db: Session = Depends(get_db)
):
    """
    Actualiza notas y lecciones aprendidas de una evaluación.
    """
    evaluation = db.query(DecisionEvaluation).filter(DecisionEvaluation.id == evaluation_id).first()
    if not evaluation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evaluación no encontrada")
    
    try:
        for key, value in evaluation_data.model_dump(exclude_unset=True).items():
            setattr(evaluation, key, value)
        
        db.commit()
        db.refresh(evaluation)
        
        logger.info(f"Evaluación {evaluation_id} actualizada.")
        return DecisionEvaluationResponse.model_validate(evaluation)
    except Exception as e:
        logger.error(f"Error al actualizar evaluación {evaluation_id}: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al actualizar la evaluación"
        )


@router.get("/statistics/overview", response_model=DecisionStatisticsResponse)
async def get_statistics(
    db: Session = Depends(get_db)
):
    """
    Obtiene estadísticas completas de decisiones por tipo de señal y tipo de decisión.
    """
    try:
        decision_service = DecisionService()
        
        overall_stats = decision_service.get_overall_statistics(db)
        by_signal_stats = decision_service.get_statistics_by_signal_type(db)
        by_decision_stats = decision_service.get_statistics_by_decision_type(db)
        
        return DecisionStatisticsResponse(
            overall=overall_stats,
            by_signal_type=by_signal_stats,
            by_decision_type=by_decision_stats
        )
    except Exception as e:
        logger.error(f"Error al obtener estadísticas: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al obtener estadísticas"
        )


