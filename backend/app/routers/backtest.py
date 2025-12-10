"""Endpoints para backtesting de estrategias."""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from sqlalchemy import desc
import logging
import json

from app.database import get_db, BacktestRule, BacktestResult
from app.models import (
    BacktestRuleCreate,
    BacktestRuleResponse,
    BacktestRuleListResponse,
    BacktestResultResponse,
    BacktestResultListResponse,
    BacktestExecuteRequest
)
from app.services.backtest_service import BacktestService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/backtest", tags=["backtest"])


# ==================== Rule CRUD ====================

@router.post("/rules", response_model=BacktestRuleResponse, status_code=status.HTTP_201_CREATED)
async def create_rule(
    request: Request,
    rule: BacktestRuleCreate,
    db: Session = Depends(get_db)
):
    """Crea una nueva regla de backtesting."""
    try:
        from datetime import datetime
        
        start_date = None
        if rule.start_date:
            start_date = datetime.fromisoformat(rule.start_date.replace('Z', '+00:00'))
        
        end_date = None
        if rule.end_date:
            end_date = datetime.fromisoformat(rule.end_date.replace('Z', '+00:00'))
        
        db_rule = BacktestRule(
            name=rule.name,
            description=rule.description,
            news_sentiment_required=rule.news_sentiment_required,
            news_min_score=rule.news_min_score,
            news_max_age_hours=rule.news_max_age_hours,
            price_change_condition=rule.price_change_condition,
            price_change_threshold=rule.price_change_threshold,
            hold_period_days=rule.hold_period_days,
            position_size_pct=rule.position_size_pct,
            start_date=start_date,
            end_date=end_date
        )
        db.add(db_rule)
        db.commit()
        db.refresh(db_rule)
        
        logger.info(f"Regla de backtest creada: ID {db_rule.id} - {rule.name}")
        return BacktestRuleResponse.model_validate(db_rule)
        
    except ValueError as e:
        logger.warning(f"Error de validación al crear regla: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error inesperado al crear regla: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al crear la regla"
        )


@router.get("/rules", response_model=BacktestRuleListResponse)
async def list_rules(
    db: Session = Depends(get_db)
):
    """Lista todas las reglas de backtesting."""
    try:
        rules = db.query(BacktestRule).order_by(desc(BacktestRule.created_at)).all()
        
        return BacktestRuleListResponse(
            items=[BacktestRuleResponse.model_validate(rule) for rule in rules],
            total=len(rules)
        )
    except Exception as e:
        logger.error(f"Error al listar reglas: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al listar reglas"
        )


@router.get("/rules/{rule_id}", response_model=BacktestRuleResponse)
async def get_rule(
    rule_id: int,
    db: Session = Depends(get_db)
):
    """Obtiene una regla por ID."""
    try:
        rule = db.query(BacktestRule).filter(BacktestRule.id == rule_id).first()
        
        if not rule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Regla con ID {rule_id} no encontrada"
            )
        
        return BacktestRuleResponse.model_validate(rule)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al obtener regla {rule_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al obtener la regla"
        )


@router.delete("/rules/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_rule(
    rule_id: int,
    db: Session = Depends(get_db)
):
    """Elimina una regla por ID."""
    try:
        rule = db.query(BacktestRule).filter(BacktestRule.id == rule_id).first()
        
        if not rule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Regla con ID {rule_id} no encontrada"
            )
        
        db.delete(rule)
        db.commit()
        
        logger.info(f"Regla eliminada: ID {rule_id}")
        return None
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al eliminar regla {rule_id}: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al eliminar la regla"
        )


# ==================== Backtest Execution ====================

@router.post("/execute", response_model=BacktestResultResponse, status_code=status.HTTP_200_OK)
async def execute_backtest(
    request: Request,
    execute_request: BacktestExecuteRequest,
    db: Session = Depends(get_db)
):
    """Ejecuta un backtest para una regla."""
    try:
        rule = db.query(BacktestRule).filter(BacktestRule.id == execute_request.rule_id).first()
        
        if not rule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Regla con ID {execute_request.rule_id} no encontrada"
            )
        
        # Ejecutar backtest
        backtest_service = BacktestService()
        results = backtest_service.execute_backtest(db, rule, execute_request.initial_capital)
        
        # Guardar resultados
        from datetime import datetime
        
        db_result = BacktestResult(
            rule_id=rule.id,
            total_trades=results["total_trades"],
            winning_trades=results["winning_trades"],
            losing_trades=results["losing_trades"],
            win_rate=results["win_rate"],
            total_pnl=results["total_pnl"],
            total_pnl_pct=results["total_pnl_pct"],
            average_win=results["average_win"],
            average_loss=results["average_loss"],
            max_drawdown=results["max_drawdown"],
            max_drawdown_pct=results["max_drawdown_pct"],
            equity_curve_data=json.dumps(results["equity_curve"]),
            executed_start_date=datetime.fromisoformat(results["executed_start_date"].replace('Z', '+00:00')),
            executed_end_date=datetime.fromisoformat(results["executed_end_date"].replace('Z', '+00:00'))
        )
        
        db.add(db_result)
        db.commit()
        db.refresh(db_result)
        
        logger.info(f"Backtest ejecutado: Regla {rule.id}, {results['total_trades']} trades")
        
        # Construir respuesta
        equity_curve = [{"date": p["date"], "equity": p["equity"], "drawdown": p["drawdown"]} 
                       for p in results["equity_curve"]]
        
        return BacktestResultResponse(
            id=db_result.id,
            rule_id=db_result.rule_id,
            rule_name=rule.name,
            total_trades=db_result.total_trades,
            winning_trades=db_result.winning_trades,
            losing_trades=db_result.losing_trades,
            win_rate=db_result.win_rate,
            total_pnl=db_result.total_pnl,
            total_pnl_pct=db_result.total_pnl_pct,
            average_win=db_result.average_win,
            average_loss=db_result.average_loss,
            max_drawdown=db_result.max_drawdown,
            max_drawdown_pct=db_result.max_drawdown_pct,
            equity_curve=equity_curve,
            executed_start_date=results["executed_start_date"],
            executed_end_date=results["executed_end_date"],
            created_at=db_result.created_at.isoformat()
        )
        
    except HTTPException:
        raise
    except ValueError as e:
        logger.warning(f"Error de validación al ejecutar backtest: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error inesperado al ejecutar backtest: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno al ejecutar backtest: {str(e)}"
        )


@router.get("/results", response_model=BacktestResultListResponse)
async def list_results(
    rule_id: int = None,
    db: Session = Depends(get_db)
):
    """Lista resultados de backtesting."""
    try:
        query = db.query(BacktestResult)
        
        if rule_id:
            query = query.filter(BacktestResult.rule_id == rule_id)
        
        results = query.order_by(desc(BacktestResult.created_at)).all()
        
        result_responses = []
        for result in results:
            rule = db.query(BacktestRule).filter(BacktestRule.id == result.rule_id).first()
            
            equity_curve = []
            if result.equity_curve_data:
                equity_curve = json.loads(result.equity_curve_data)
            
            result_responses.append(BacktestResultResponse(
                id=result.id,
                rule_id=result.rule_id,
                rule_name=rule.name if rule else None,
                total_trades=result.total_trades,
                winning_trades=result.winning_trades,
                losing_trades=result.losing_trades,
                win_rate=result.win_rate,
                total_pnl=result.total_pnl,
                total_pnl_pct=result.total_pnl_pct,
                average_win=result.average_win,
                average_loss=result.average_loss,
                max_drawdown=result.max_drawdown,
                max_drawdown_pct=result.max_drawdown_pct,
                equity_curve=equity_curve,
                executed_start_date=result.executed_start_date.isoformat() if result.executed_start_date else None,
                executed_end_date=result.executed_end_date.isoformat() if result.executed_end_date else None,
                created_at=result.created_at.isoformat()
            ))
        
        return BacktestResultListResponse(
            items=result_responses,
            total=len(result_responses)
        )
    except Exception as e:
        logger.error(f"Error al listar resultados: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al listar resultados"
        )


@router.get("/results/{result_id}", response_model=BacktestResultResponse)
async def get_result(
    result_id: int,
    db: Session = Depends(get_db)
):
    """Obtiene un resultado de backtesting por ID."""
    try:
        result = db.query(BacktestResult).filter(BacktestResult.id == result_id).first()
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Resultado con ID {result_id} no encontrado"
            )
        
        rule = db.query(BacktestRule).filter(BacktestRule.id == result.rule_id).first()
        
        equity_curve = []
        if result.equity_curve_data:
            equity_curve = json.loads(result.equity_curve_data)
        
        return BacktestResultResponse(
            id=result.id,
            rule_id=result.rule_id,
            rule_name=rule.name if rule else None,
            total_trades=result.total_trades,
            winning_trades=result.winning_trades,
            losing_trades=result.losing_trades,
            win_rate=result.win_rate,
            total_pnl=result.total_pnl,
            total_pnl_pct=result.total_pnl_pct,
            average_win=result.average_win,
            average_loss=result.average_loss,
            max_drawdown=result.max_drawdown,
            max_drawdown_pct=result.max_drawdown_pct,
            equity_curve=equity_curve,
            executed_start_date=result.executed_start_date.isoformat() if result.executed_start_date else None,
            executed_end_date=result.executed_end_date.isoformat() if result.executed_end_date else None,
            created_at=result.created_at.isoformat()
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al obtener resultado {result_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al obtener el resultado"
        )

