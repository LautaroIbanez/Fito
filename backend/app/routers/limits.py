"""Endpoints para límites dinámicos."""
from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
import logging

from app.database import get_db, DynamicLimit, PortfolioItem
from app.models import DynamicLimitResponse, DynamicLimitListResponse
from app.services.limit_service import LimitService
from app.services.risk_service import RiskService
from app.models import PortfolioItemResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/limits", tags=["limits"])


@router.post("/calculate", response_model=DynamicLimitListResponse, status_code=status.HTTP_200_OK)
async def calculate_limits(
    request: Request,
    force: bool = Query(False, description="Forzar recálculo incluso si hay límites recientes"),
    db: Session = Depends(get_db)
):
    """
    Calcula límites dinámicos para todos los activos en la cartera.
    """
    try:
        limit_service = LimitService()
        limits = limit_service.calculate_all_limits(db, force_recalculate=force)
        
        if not limits:
            return DynamicLimitListResponse(
                items=[],
                total=0,
                exceeded_count=0
            )
        
        # Obtener información de portfolio items para respuesta
        portfolio_items_dict = {}
        portfolio_items_db = db.query(PortfolioItem).all()
        for item in portfolio_items_db:
            portfolio_items_dict[item.id] = item
        
        # Construir respuestas
        limit_responses = []
        exceeded_count = 0
        
        for limit in limits:
            portfolio_item = portfolio_items_dict.get(limit.portfolio_item_id)
            
            # Calcular valor actual
            current_value = None
            if portfolio_item:
                risk_service = RiskService()
                portfolio_items = [PortfolioItemResponse.model_validate(portfolio_item)]
                total_value = risk_service.calculate_portfolio_value(portfolio_items)
                if total_value > 0:
                    current_value = total_value * (limit.current_position_pct / 100.0)
            
            limit_responses.append(DynamicLimitResponse(
                id=limit.id,
                portfolio_item_id=limit.portfolio_item_id,
                portfolio_item_name=portfolio_item.name if portfolio_item else None,
                portfolio_item_symbol=portfolio_item.symbol if portfolio_item else None,
                asset_type=portfolio_item.asset_type if portfolio_item else None,
                current_position_pct=limit.current_position_pct,
                recent_drawdown_pct=limit.recent_drawdown_pct,
                realized_volatility=limit.realized_volatility,
                implied_volatility=limit.implied_volatility,
                max_position_pct=limit.max_position_pct,
                suggested_stop_loss_pct=limit.suggested_stop_loss_pct,
                risk_adjusted_size_pct=limit.risk_adjusted_size_pct,
                is_exceeded=limit.is_exceeded,
                excess_amount_pct=limit.excess_amount_pct,
                suggested_reduction_pct=limit.suggested_reduction_pct,
                current_value=current_value,
                calculated_at=limit.calculated_at.isoformat(),
                next_calculation_at=limit.next_calculation_at.isoformat() if limit.next_calculation_at else None
            ))
            
            if limit.is_exceeded:
                exceeded_count += 1
        
        logger.info(f"Límites calculados: {len(limits)} activos, {exceeded_count} excedidos")
        
        return DynamicLimitListResponse(
            items=limit_responses,
            total=len(limit_responses),
            exceeded_count=exceeded_count
        )
        
    except Exception as e:
        logger.error(f"Error al calcular límites: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno al calcular límites: {str(e)}"
        )


@router.get("", response_model=DynamicLimitListResponse)
async def get_limits(
    exceeded_only: bool = Query(False, description="Solo límites excedidos"),
    db: Session = Depends(get_db)
):
    """
    Obtiene límites dinámicos actuales.
    """
    try:
        query = db.query(DynamicLimit)
        
        if exceeded_only:
            query = query.filter(DynamicLimit.is_exceeded == True)
        
        limits = query.order_by(desc(DynamicLimit.excess_amount_pct)).all()
        
        if not limits:
            return DynamicLimitListResponse(
                items=[],
                total=0,
                exceeded_count=0
            )
        
        # Obtener información de portfolio items
        portfolio_items_dict = {}
        portfolio_items_db = db.query(PortfolioItem).all()
        for item in portfolio_items_db:
            portfolio_items_dict[item.id] = item
        
        # Construir respuestas
        limit_responses = []
        exceeded_count = 0
        
        for limit in limits:
            portfolio_item = portfolio_items_dict.get(limit.portfolio_item_id)
            
            # Calcular valor actual
            current_value = None
            if portfolio_item:
                risk_service = RiskService()
                portfolio_items = [PortfolioItemResponse.model_validate(portfolio_item)]
                total_value = risk_service.calculate_portfolio_value(portfolio_items)
                if total_value > 0:
                    current_value = total_value * (limit.current_position_pct / 100.0)
            
            limit_responses.append(DynamicLimitResponse(
                id=limit.id,
                portfolio_item_id=limit.portfolio_item_id,
                portfolio_item_name=portfolio_item.name if portfolio_item else None,
                portfolio_item_symbol=portfolio_item.symbol if portfolio_item else None,
                asset_type=portfolio_item.asset_type if portfolio_item else None,
                current_position_pct=limit.current_position_pct,
                recent_drawdown_pct=limit.recent_drawdown_pct,
                realized_volatility=limit.realized_volatility,
                implied_volatility=limit.implied_volatility,
                max_position_pct=limit.max_position_pct,
                suggested_stop_loss_pct=limit.suggested_stop_loss_pct,
                risk_adjusted_size_pct=limit.risk_adjusted_size_pct,
                is_exceeded=limit.is_exceeded,
                excess_amount_pct=limit.excess_amount_pct,
                suggested_reduction_pct=limit.suggested_reduction_pct,
                current_value=current_value,
                calculated_at=limit.calculated_at.isoformat(),
                next_calculation_at=limit.next_calculation_at.isoformat() if limit.next_calculation_at else None
            ))
            
            if limit.is_exceeded:
                exceeded_count += 1
        
        return DynamicLimitListResponse(
            items=limit_responses,
            total=len(limit_responses),
            exceeded_count=exceeded_count
        )
    except Exception as e:
        logger.error(f"Error al obtener límites: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al obtener límites"
        )


@router.get("/{portfolio_item_id}", response_model=DynamicLimitResponse)
async def get_limit_for_item(
    portfolio_item_id: int,
    db: Session = Depends(get_db)
):
    """
    Obtiene límite dinámico para un activo específico.
    """
    try:
        limit = db.query(DynamicLimit).filter(
            DynamicLimit.portfolio_item_id == portfolio_item_id
        ).first()
        
        if not limit:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Límite para portfolio item {portfolio_item_id} no encontrado. Ejecuta /calculate primero."
            )
        
        portfolio_item = db.query(PortfolioItem).filter(PortfolioItem.id == portfolio_item_id).first()
        
        # Calcular valor actual
        current_value = None
        if portfolio_item:
            risk_service = RiskService()
            portfolio_items = [PortfolioItemResponse.model_validate(portfolio_item)]
            total_value = risk_service.calculate_portfolio_value(portfolio_items)
            if total_value > 0:
                current_value = total_value * (limit.current_position_pct / 100.0)
        
        return DynamicLimitResponse(
            id=limit.id,
            portfolio_item_id=limit.portfolio_item_id,
            portfolio_item_name=portfolio_item.name if portfolio_item else None,
            portfolio_item_symbol=portfolio_item.symbol if portfolio_item else None,
            asset_type=portfolio_item.asset_type if portfolio_item else None,
            current_position_pct=limit.current_position_pct,
            recent_drawdown_pct=limit.recent_drawdown_pct,
            realized_volatility=limit.realized_volatility,
            implied_volatility=limit.implied_volatility,
            max_position_pct=limit.max_position_pct,
            suggested_stop_loss_pct=limit.suggested_stop_loss_pct,
            risk_adjusted_size_pct=limit.risk_adjusted_size_pct,
            is_exceeded=limit.is_exceeded,
            excess_amount_pct=limit.excess_amount_pct,
            suggested_reduction_pct=limit.suggested_reduction_pct,
            current_value=current_value,
            calculated_at=limit.calculated_at.isoformat(),
            next_calculation_at=limit.next_calculation_at.isoformat() if limit.next_calculation_at else None
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al obtener límite: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al obtener límite"
        )


