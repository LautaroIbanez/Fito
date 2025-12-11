"""Servicio de auditoría y logging para recomendaciones."""
import logging
from typing import Dict, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.database import TradingRecommendation
from app.config import RECOMMENDATION_AUDIT_ENABLED, RECOMMENDATION_LOG_LEVEL

logger = logging.getLogger(__name__)

# Configurar nivel de logging específico para recomendaciones
if RECOMMENDATION_LOG_LEVEL == "DEBUG":
    logger.setLevel(logging.DEBUG)
elif RECOMMENDATION_LOG_LEVEL == "INFO":
    logger.setLevel(logging.INFO)
elif RECOMMENDATION_LOG_LEVEL == "WARNING":
    logger.setLevel(logging.WARNING)


class RecommendationAuditService:
    """Servicio para auditoría y logging de recomendaciones."""
    
    def __init__(self):
        """Inicializa el servicio de auditoría."""
        self.audit_enabled = RECOMMENDATION_AUDIT_ENABLED
    
    def log_recommendation_generation(
        self,
        recommendation_id: int,
        portfolio_item_id: int,
        asset_name: str,
        asset_symbol: Optional[str],
        action: str,
        condition: str,
        confidence: float,
        source_news_id: Optional[int],
        inputs: Dict,
        threshold_data: Dict
    ):
        """
        Registra la generación de una recomendación para auditoría.
        """
        if not self.audit_enabled:
            return
        
        logger.info(
            f"RECOMMENDATION_GENERATED | "
            f"ID={recommendation_id} | "
            f"Asset={asset_name} ({asset_symbol or 'N/A'}) | "
            f"Action={action} | "
            f"Condition={condition} | "
            f"Confidence={confidence:.2f} | "
            f"SourceNews={source_news_id or 'N/A'} | "
            f"Sentiment={inputs.get('sentiment', 'N/A')} | "
            f"Relevance={inputs.get('relevance', 'N/A')} | "
            f"Urgency={inputs.get('urgency', 'N/A')} | "
            f"PriceChange={inputs.get('intraday_change_pct', 'N/A')} | "
            f"VolumeRatio={inputs.get('volume_ratio', 'N/A')}"
        )
    
    def log_recommendation_acknowledgment(
        self,
        recommendation_id: int,
        acknowledged_at: datetime
    ):
        """Registra cuando una recomendación es reconocida."""
        if not self.audit_enabled:
            return
        
        logger.info(
            f"RECOMMENDATION_ACKNOWLEDGED | "
            f"ID={recommendation_id} | "
            f"AcknowledgedAt={acknowledged_at.isoformat()}"
        )
    
    def log_recommendation_execution(
        self,
        recommendation_id: int,
        executed_at: datetime,
        action: str,
        asset_name: str
    ):
        """Registra cuando una recomendación es ejecutada."""
        if not self.audit_enabled:
            return
        
        logger.info(
            f"RECOMMENDATION_EXECUTED | "
            f"ID={recommendation_id} | "
            f"Action={action} | "
            f"Asset={asset_name} | "
            f"ExecutedAt={executed_at.isoformat()}"
        )
    
    def get_recommendation_statistics(
        self,
        db: Session,
        portfolio_item_id: Optional[int] = None,
        days: int = 30
    ) -> Dict:
        """
        Obtiene estadísticas de recomendaciones para análisis y depuración.
        """
        from datetime import timedelta
        
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        
        query = db.query(TradingRecommendation).filter(
            TradingRecommendation.generated_at >= cutoff_date
        )
        
        if portfolio_item_id:
            query = query.filter(TradingRecommendation.portfolio_item_id == portfolio_item_id)
        
        recommendations = query.all()
        
        if not recommendations:
            return {
                "total": 0,
                "by_action": {},
                "by_confidence_range": {},
                "acknowledged_count": 0,
                "executed_count": 0,
                "average_confidence": 0.0
            }
        
        # Estadísticas por acción
        by_action = {}
        by_confidence_range = {
            "high": 0,  # >= 0.8
            "medium": 0,  # 0.5-0.8
            "low": 0  # < 0.5
        }
        
        acknowledged_count = 0
        executed_count = 0
        total_confidence = 0.0
        
        for rec in recommendations:
            # Por acción
            action = rec.action
            by_action[action] = by_action.get(action, 0) + 1
            
            # Por rango de confianza
            if rec.confidence >= 0.8:
                by_confidence_range["high"] += 1
            elif rec.confidence >= 0.5:
                by_confidence_range["medium"] += 1
            else:
                by_confidence_range["low"] += 1
            
            # Contadores
            if rec.acknowledged_at:
                acknowledged_count += 1
            if rec.executed_at:
                executed_count += 1
            
            total_confidence += rec.confidence
        
        return {
            "total": len(recommendations),
            "by_action": by_action,
            "by_confidence_range": by_confidence_range,
            "acknowledged_count": acknowledged_count,
            "executed_count": executed_count,
            "acknowledged_rate": acknowledged_count / len(recommendations) if recommendations else 0.0,
            "executed_rate": executed_count / len(recommendations) if recommendations else 0.0,
            "average_confidence": total_confidence / len(recommendations) if recommendations else 0.0,
            "period_days": days
        }



