"""Servicio para calcular límites dinámicos basados en drawdown y volatilidad."""
import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session

from app.database import PortfolioItem, DynamicLimit
from app.models import PortfolioItemResponse
from app.config import (
    LIMITS_MAX_DRAWDOWN_THRESHOLD,
    LIMITS_VOLATILITY_MULTIPLIER,
    LIMITS_BASE_MAX_POSITION_PCT,
    LIMITS_MIN_POSITION_PCT,
    LIMITS_DRAWDOWN_LOOKBACK_DAYS,
    LIMITS_RECALCULATION_INTERVAL_HOURS
)

logger = logging.getLogger(__name__)


class LimitService:
    """Servicio para calcular y gestionar límites dinámicos."""
    
    def calculate_recent_drawdown(
        self,
        symbol: str,
        lookback_days: int = LIMITS_DRAWDOWN_LOOKBACK_DAYS
    ) -> Optional[float]:
        """
        Calcula drawdown reciente de un activo.
        
        Nota: En producción, obtener datos históricos reales de una API.
        Por ahora, retorna un valor estimado basado en tipo de activo.
        
        Returns:
            Optional[float]: Drawdown reciente en porcentaje (0-1), None si no hay datos
        """
        # En producción, aquí obtendrías datos históricos y calcularías:
        # drawdown = (peak_price - current_price) / peak_price
        
        # Por ahora, retornar estimación basada en volatilidad típica
        logger.warning(f"Usando drawdown estimado para {symbol}. En producción, usar datos históricos reales.")
        return None  # Retornar None indica que no hay datos disponibles
    
    def calculate_volatility(
        self,
        symbol: str,
        asset_type: str,
        lookback_days: int = 30
    ) -> Tuple[Optional[float], Optional[float]]:
        """
        Calcula volatilidad realizada e implícita.
        
        Returns:
            Tuple[Optional[float], Optional[float]]: (realized_vol, implied_vol)
        """
        # En producción, calcular volatilidad realizada desde precios históricos
        # Para volatilidad implícita, usar datos de opciones si están disponibles
        
        # Valores estimados por tipo de activo (en producción, calcular desde datos)
        volatility_by_type = {
            "acciones": (0.20, 0.22),  # 20% realizada, 22% implícita
            "bonos": (0.05, 0.06),
            "etf": (0.15, 0.16),
            "fondos": (0.12, 0.13),
            "divisas": (0.10, 0.11),
            "otros": (0.15, 0.16)
        }
        
        vol = volatility_by_type.get(asset_type.lower(), (0.15, 0.16))
        logger.warning(f"Usando volatilidad estimada para {symbol}. En producción, calcular desde datos históricos.")
        
        return vol[0], vol[1]  # realized, implied
    
    def calculate_max_position(
        self,
        current_position_pct: float,
        drawdown_pct: Optional[float],
        realized_vol: Optional[float],
        implied_vol: Optional[float],
        base_max: float = LIMITS_BASE_MAX_POSITION_PCT
    ) -> Tuple[float, float, float]:
        """
        Calcula límite máximo de posición basado en drawdown y volatilidad.
        
        Returns:
            Tuple[float, float, float]: (max_position_pct, risk_adjusted_size_pct, suggested_stop_loss_pct)
        """
        max_position = base_max
        risk_adjusted_size = current_position_pct
        
        # Ajuste por drawdown
        if drawdown_pct is not None:
            if drawdown_pct > LIMITS_MAX_DRAWDOWN_THRESHOLD:
                # Reducir límite proporcionalmente al drawdown excesivo
                excess_drawdown = drawdown_pct - LIMITS_MAX_DRAWDOWN_THRESHOLD
                reduction_factor = 1.0 - (excess_drawdown / LIMITS_MAX_DRAWDOWN_THRESHOLD)
                reduction_factor = max(0.5, reduction_factor)  # Mínimo 50% del límite base
                max_position *= reduction_factor
                logger.info(f"Drawdown {drawdown_pct:.2%} excede umbral. Reduciendo límite a {max_position:.2f}%")
        
        # Ajuste por volatilidad (usar la mayor entre realizada e implícita)
        volatility = max(realized_vol or 0, implied_vol or 0)
        if volatility > 0:
            # Reducir límite si volatilidad es alta
            # Volatilidad típica es ~15-20%, ajustar proporcionalmente
            base_vol = 0.15  # 15% como referencia
            if volatility > base_vol:
                vol_adjustment = base_vol / volatility
                max_position *= vol_adjustment
        
        # Aplicar límite mínimo
        max_position = max(max_position, LIMITS_MIN_POSITION_PCT)
        
        # Tamaño ajustado por riesgo (recomendación conservadora)
        risk_adjusted_size = min(current_position_pct, max_position * 0.8)  # 80% del máximo como recomendación
        
        # Stop loss sugerido basado en volatilidad
        # Stop loss más cercano si volatilidad es alta
        if volatility > 0:
            # Stop loss a 2 desviaciones estándar (aproximadamente)
            suggested_stop_loss = volatility * 2  # Como porcentaje
            suggested_stop_loss = min(suggested_stop_loss, 0.10)  # Máximo 10%
        else:
            suggested_stop_loss = 0.05  # Default 5%
        
        return round(max_position, 2), round(risk_adjusted_size, 2), round(suggested_stop_loss * 100, 2)
    
    def check_limits(
        self,
        portfolio_items: List[PortfolioItemResponse],
        total_portfolio_value: float
    ) -> List[Dict]:
        """
        Verifica límites para todos los activos y calcula excesos.
        
        Returns:
            List[Dict]: Lista de límites calculados con información de exceso
        """
        limits = []
        
        for item in portfolio_items:
            # Calcular % actual en cartera
            item_value = 0.0
            if item.total_value:
                try:
                    item_value = float(item.total_value.replace(',', ''))
                except (ValueError, AttributeError):
                    pass
            elif item.quantity and item.price:
                try:
                    item_value = float(item.quantity.replace(',', '')) * float(item.price.replace(',', ''))
                except (ValueError, AttributeError):
                    pass
            
            if total_portfolio_value == 0:
                current_position_pct = 0.0
            else:
                current_position_pct = (item_value / total_portfolio_value) * 100
            
            # Calcular métricas de riesgo
            drawdown = self.calculate_recent_drawdown(item.symbol or item.name)
            realized_vol, implied_vol = self.calculate_volatility(
                item.symbol or item.name,
                item.asset_type
            )
            
            # Calcular límites
            max_position, risk_adjusted, stop_loss = self.calculate_max_position(
                current_position_pct,
                drawdown,
                realized_vol,
                implied_vol
            )
            
            # Verificar si excede límite
            is_exceeded = current_position_pct > max_position
            excess_amount_pct = max(0, current_position_pct - max_position)
            suggested_reduction_pct = excess_amount_pct if is_exceeded else 0.0
            
            limits.append({
                "portfolio_item_id": item.id,
                "portfolio_item_name": item.name,
                "portfolio_item_symbol": item.symbol,
                "asset_type": item.asset_type,
                "current_position_pct": round(current_position_pct, 2),
                "recent_drawdown_pct": round(drawdown * 100, 2) if drawdown else None,
                "realized_volatility": round(realized_vol * 100, 2) if realized_vol else None,
                "implied_volatility": round(implied_vol * 100, 2) if implied_vol else None,
                "max_position_pct": max_position,
                "suggested_stop_loss_pct": stop_loss,
                "risk_adjusted_size_pct": risk_adjusted,
                "is_exceeded": is_exceeded,
                "excess_amount_pct": round(excess_amount_pct, 2),
                "suggested_reduction_pct": round(suggested_reduction_pct, 2),
                "current_value": item_value
            })
        
        return limits
    
    def save_limits(
        self,
        db: Session,
        limits: List[Dict]
    ) -> List[DynamicLimit]:
        """
        Guarda límites calculados en la base de datos.
        """
        saved_limits = []
        now = datetime.now(timezone.utc)
        next_calc = now + timedelta(hours=LIMITS_RECALCULATION_INTERVAL_HOURS)
        
        for limit_data in limits:
            # Eliminar límite anterior si existe
            db.query(DynamicLimit).filter(
                DynamicLimit.portfolio_item_id == limit_data["portfolio_item_id"]
            ).delete()
            
            db_limit = DynamicLimit(
                portfolio_item_id=limit_data["portfolio_item_id"],
                current_position_pct=limit_data["current_position_pct"],
                recent_drawdown_pct=limit_data["recent_drawdown_pct"],
                realized_volatility=limit_data["realized_volatility"],
                implied_volatility=limit_data["implied_volatility"],
                max_position_pct=limit_data["max_position_pct"],
                suggested_stop_loss_pct=limit_data["suggested_stop_loss_pct"],
                risk_adjusted_size_pct=limit_data["risk_adjusted_size_pct"],
                is_exceeded=limit_data["is_exceeded"],
                excess_amount_pct=limit_data["excess_amount_pct"],
                suggested_reduction_pct=limit_data["suggested_reduction_pct"],
                next_calculation_at=next_calc
            )
            
            db.add(db_limit)
            saved_limits.append(db_limit)
        
        db.commit()
        
        for limit in saved_limits:
            db.refresh(limit)
        
        logger.info(f"Guardados {len(saved_limits)} límites dinámicos")
        return saved_limits
    
    def calculate_all_limits(
        self,
        db: Session,
        force_recalculate: bool = False
    ) -> List[DynamicLimit]:
        """
        Calcula y guarda límites para todos los activos de la cartera.
        
        Args:
            db: Sesión de base de datos
            force_recalculate: Si True, recalcula aunque no haya pasado el intervalo
        
        Returns:
            List[DynamicLimit]: Límites calculados y guardados
        """
        from app.services.risk_service import RiskService
        
        # Obtener portfolio items
        portfolio_items_db = db.query(PortfolioItem).all()
        if not portfolio_items_db:
            return []
        
        portfolio_items = [PortfolioItemResponse.model_validate(item) for item in portfolio_items_db]
        
        # Verificar si hay límites recientes
        if not force_recalculate:
            now = datetime.now(timezone.utc)
            recent_limits = db.query(DynamicLimit).filter(
                DynamicLimit.next_calculation_at > now
            ).all()
            
            if recent_limits and len(recent_limits) == len(portfolio_items_db):
                logger.info("Límites recientes encontrados, omitiendo recálculo")
                return recent_limits
        
        # Calcular valor total del portfolio
        risk_service = RiskService()
        total_value = risk_service.calculate_portfolio_value(portfolio_items)
        
        # Calcular límites
        limits_data = self.check_limits(portfolio_items, total_value)
        
        # Guardar en base de datos
        saved_limits = self.save_limits(db, limits_data)
        
        return saved_limits

