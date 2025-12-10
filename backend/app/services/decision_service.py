"""Servicio para gestionar log de decisiones y evaluaciones."""
import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

from app.database import DecisionLog, DecisionEvaluation, PortfolioItem
from app.models import PortfolioItemResponse
from app.config import (
    DECISION_DEFAULT_EVALUATION_WINDOW_DAYS,
    DECISION_HIT_THRESHOLD_PCT,
    DECISION_AUTO_EVALUATE_ENABLED
)

logger = logging.getLogger(__name__)


class DecisionService:
    """Servicio para gestionar decisiones de trading y sus evaluaciones."""
    
    def get_price_at_date(
        self,
        symbol: str,
        date: datetime
    ) -> Optional[float]:
        """
        Obtiene precio de un activo en una fecha específica.
        
        Nota: En producción, obtener datos históricos reales de una API.
        
        Returns:
            Optional[float]: Precio en la fecha, None si no hay datos
        """
        # En producción, aquí obtendrías datos históricos reales
        # Por ahora, retornar None indica que no hay datos disponibles
        logger.warning(f"Usando precio estimado para {symbol} en {date}. En producción, usar datos históricos reales.")
        return None
    
    def evaluate_decision(
        self,
        db: Session,
        decision: DecisionLog,
        force: bool = False
    ) -> Optional[DecisionEvaluation]:
        """
        Evalúa una decisión comparando expectativa vs resultado real.
        
        Returns:
            Optional[DecisionEvaluation]: Evaluación creada, None si no se puede evaluar
        """
        # Verificar si ya fue evaluada
        if decision.status == 'evaluated' and not force:
            return decision.evaluation
        
        # Verificar si ha pasado el periodo de evaluación
        evaluation_date = decision.decided_at + timedelta(days=decision.evaluation_window_days)
        now = datetime.now(timezone.utc)
        
        if now < evaluation_date and not force:
            logger.info(f"Decisión {decision.id} aún no está lista para evaluación (faltan {(evaluation_date - now).days} días)")
            return None
        
        # Obtener precios (si están disponibles)
        portfolio_item = db.query(PortfolioItem).filter(PortfolioItem.id == decision.portfolio_item_id).first()
        if not portfolio_item:
            logger.warning(f"PortfolioItem {decision.portfolio_item_id} no encontrado para decisión {decision.id}")
            return None
        
        symbol = portfolio_item.symbol or portfolio_item.name
        price_at_decision = self.get_price_at_date(symbol, decision.decided_at)
        price_at_evaluation = self.get_price_at_date(symbol, evaluation_date)
        
        # Si no hay precios, usar precio actual del portfolio item como aproximación
        if price_at_decision is None and portfolio_item.price:
            try:
                price_at_decision = float(str(portfolio_item.price).replace(',', ''))
            except (ValueError, AttributeError):
                price_at_decision = None
        
        if price_at_evaluation is None and portfolio_item.price:
            try:
                price_at_evaluation = float(str(portfolio_item.price).replace(',', ''))
            except (ValueError, AttributeError):
                price_at_evaluation = None
        
        # Calcular resultado
        result = 'miss'
        price_change_pct = None
        outcome_match = False
        
        if price_at_decision is not None and price_at_evaluation is not None:
            price_change_pct = ((price_at_evaluation - price_at_decision) / price_at_decision) * 100
            
            # Determinar si fue hit/miss según tipo de decisión y expectativa
            if decision.expected_direction == 'up':
                if price_change_pct >= DECISION_HIT_THRESHOLD_PCT * 100:
                    result = 'hit'
                    outcome_match = True
                elif price_change_pct >= (DECISION_HIT_THRESHOLD_PCT * 50) * 100:
                    result = 'partial'
                    outcome_match = True
            elif decision.expected_direction == 'down':
                if price_change_pct <= -DECISION_HIT_THRESHOLD_PCT * 100:
                    result = 'hit'
                    outcome_match = True
                elif price_change_pct <= -(DECISION_HIT_THRESHOLD_PCT * 50) * 100:
                    result = 'partial'
                    outcome_match = True
            elif decision.expected_direction == 'neutral' or decision.decision_type == 'hold':
                if abs(price_change_pct) <= DECISION_HIT_THRESHOLD_PCT * 100:
                    result = 'hit'
                    outcome_match = True
                else:
                    result = 'partial'
        
        # Verificar si precio objetivo se alcanzó
        if decision.expected_price and price_at_evaluation:
            try:
                expected_price_val = float(str(decision.expected_price).replace('$', '').replace(',', ''))
                if decision.expected_direction == 'up':
                    if price_at_evaluation >= expected_price_val * 0.95:  # 5% de tolerancia
                        result = 'hit'
                        outcome_match = True
                elif decision.expected_direction == 'down':
                    if price_at_evaluation <= expected_price_val * 1.05:  # 5% de tolerancia
                        result = 'hit'
                        outcome_match = True
            except (ValueError, AttributeError):
                pass
        
        # Crear o actualizar evaluación
        evaluation = db.query(DecisionEvaluation).filter(DecisionEvaluation.decision_id == decision.id).first()
        
        if evaluation:
            evaluation.price_at_decision = price_at_decision
            evaluation.price_at_evaluation = price_at_evaluation
            evaluation.result = result
            evaluation.price_change_pct = price_change_pct
            evaluation.outcome_match = outcome_match
            evaluation.evaluated_at = now
        else:
            evaluation = DecisionEvaluation(
                decision_id=decision.id,
                price_at_decision=price_at_decision,
                price_at_evaluation=price_at_evaluation,
                result=result,
                price_change_pct=price_change_pct,
                outcome_match=outcome_match,
                evaluated_at=now
            )
            db.add(evaluation)
        
        # Actualizar estado de la decisión
        decision.status = 'evaluated'
        decision.evaluated_at = now
        
        db.commit()
        db.refresh(evaluation)
        
        logger.info(f"Decisión {decision.id} evaluada: {result} ({price_change_pct:.2f}% cambio)")
        
        return evaluation
    
    def evaluate_pending_decisions(
        self,
        db: Session,
        force_all: bool = False
    ) -> List[DecisionEvaluation]:
        """
        Evalúa automáticamente todas las decisiones pendientes que han cumplido su ventana.
        """
        if not DECISION_AUTO_EVALUATE_ENABLED and not force_all:
            return []
        
        query = db.query(DecisionLog).filter(DecisionLog.status == 'pending')
        
        if not force_all:
            # Solo evaluar decisiones que han cumplido su ventana
            cutoff_date = datetime.now(timezone.utc)
            query = query.filter(
                func.date(DecisionLog.decided_at) + func.cast(DecisionLog.evaluation_window_days, func.Integer) <= cutoff_date.date()
            )
        
        pending_decisions = query.all()
        
        evaluations = []
        for decision in pending_decisions:
            try:
                evaluation = self.evaluate_decision(db, decision, force=force_all)
                if evaluation:
                    evaluations.append(evaluation)
            except Exception as e:
                logger.error(f"Error al evaluar decisión {decision.id}: {e}", exc_info=True)
        
        logger.info(f"Evaluadas {len(evaluations)} decisiones pendientes")
        
        return evaluations
    
    def get_statistics_by_signal_type(
        self,
        db: Session
    ) -> Dict[str, Dict]:
        """
        Calcula estadísticas de aciertos por tipo de señal.
        
        Returns:
            Dict con estadísticas por signal_type
        """
        # Obtener todas las decisiones evaluadas
        evaluated_decisions = db.query(DecisionLog).filter(
            DecisionLog.status == 'evaluated'
        ).all()
        
        stats = {}
        
        for decision in evaluated_decisions:
            signal_type = decision.signal_type
            if signal_type not in stats:
                stats[signal_type] = {
                    'total': 0,
                    'hits': 0,
                    'misses': 0,
                    'partials': 0,
                    'hit_rate': 0.0,
                    'avg_price_change_pct': 0.0,
                }
            
            stats[signal_type]['total'] += 1
            
            if decision.evaluation:
                if decision.evaluation.result == 'hit':
                    stats[signal_type]['hits'] += 1
                elif decision.evaluation.result == 'miss':
                    stats[signal_type]['misses'] += 1
                elif decision.evaluation.result == 'partial':
                    stats[signal_type]['partials'] += 1
                
                if decision.evaluation.price_change_pct is not None:
                    current_avg = stats[signal_type]['avg_price_change_pct']
                    count = stats[signal_type]['total']
                    new_price_change = decision.evaluation.price_change_pct
                    stats[signal_type]['avg_price_change_pct'] = (
                        (current_avg * (count - 1) + new_price_change) / count
                    )
        
        # Calcular hit rate
        for signal_type in stats:
            if stats[signal_type]['total'] > 0:
                stats[signal_type]['hit_rate'] = (
                    stats[signal_type]['hits'] / stats[signal_type]['total']
                ) * 100
        
        return stats
    
    def get_statistics_by_decision_type(
        self,
        db: Session
    ) -> Dict[str, Dict]:
        """
        Calcula estadísticas de aciertos por tipo de decisión (buy/sell/hold).
        """
        evaluated_decisions = db.query(DecisionLog).filter(
            DecisionLog.status == 'evaluated'
        ).all()
        
        stats = {}
        
        for decision in evaluated_decisions:
            decision_type = decision.decision_type
            if decision_type not in stats:
                stats[decision_type] = {
                    'total': 0,
                    'hits': 0,
                    'misses': 0,
                    'partials': 0,
                    'hit_rate': 0.0,
                }
            
            stats[decision_type]['total'] += 1
            
            if decision.evaluation:
                if decision.evaluation.result == 'hit':
                    stats[decision_type]['hits'] += 1
                elif decision.evaluation.result == 'miss':
                    stats[decision_type]['misses'] += 1
                elif decision.evaluation.result == 'partial':
                    stats[decision_type]['partials'] += 1
        
        # Calcular hit rate
        for decision_type in stats:
            if stats[decision_type]['total'] > 0:
                stats[decision_type]['hit_rate'] = (
                    stats[decision_type]['hits'] / stats[decision_type]['total']
                ) * 100
        
        return stats
    
    def get_overall_statistics(
        self,
        db: Session
    ) -> Dict:
        """
        Calcula estadísticas generales del log de decisiones.
        """
        total_decisions = db.query(DecisionLog).count()
        pending_decisions = db.query(DecisionLog).filter(DecisionLog.status == 'pending').count()
        evaluated_decisions = db.query(DecisionLog).filter(DecisionLog.status == 'evaluated').count()
        
        evaluated = db.query(DecisionLog).filter(DecisionLog.status == 'evaluated').all()
        
        total_hits = 0
        total_misses = 0
        total_partials = 0
        total_price_change = 0.0
        count_with_price_change = 0
        
        for decision in evaluated:
            if decision.evaluation:
                if decision.evaluation.result == 'hit':
                    total_hits += 1
                elif decision.evaluation.result == 'miss':
                    total_misses += 1
                elif decision.evaluation.result == 'partial':
                    total_partials += 1
                
                if decision.evaluation.price_change_pct is not None:
                    total_price_change += decision.evaluation.price_change_pct
                    count_with_price_change += 1
        
        overall_hit_rate = 0.0
        if evaluated_decisions > 0:
            overall_hit_rate = (total_hits / evaluated_decisions) * 100
        
        avg_price_change = 0.0
        if count_with_price_change > 0:
            avg_price_change = total_price_change / count_with_price_change
        
        return {
            'total_decisions': total_decisions,
            'pending_decisions': pending_decisions,
            'evaluated_decisions': evaluated_decisions,
            'total_hits': total_hits,
            'total_misses': total_misses,
            'total_partials': total_partials,
            'overall_hit_rate': round(overall_hit_rate, 2),
            'avg_price_change_pct': round(avg_price_change, 2),
        }



