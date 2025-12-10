"""Servicio para monitoreo y generación de alertas combinadas."""
import logging
from typing import List, Optional, Dict, Tuple
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session

from app.database import AlertTrigger, AlertHistory, NewsItem, PortfolioItem
from app.models import NewsItemResponse, PortfolioItemResponse
from app.services.news_scoring_service import NewsScoringService
from app.config import ALERT_NEWS_MIN_SCORE, ALERT_DEFAULT_NEWS_AGE_HOURS

logger = logging.getLogger(__name__)


class AlertService:
    """Servicio para verificar triggers y generar alertas."""
    
    def __init__(self):
        self.scoring_service = NewsScoringService()
    
    def get_recent_relevant_news(
        self,
        db: Session,
        symbol: Optional[str] = None,
        asset_type: Optional[str] = None,
        max_age_hours: int = 24,
        min_score: float = 2.0
    ) -> Tuple[List[NewsItemResponse], float]:
        """
        Obtiene noticias recientes relevantes para un símbolo o tipo de activo.
        
        Returns:
            Tuple[List[NewsItemResponse], float]: (noticias relevantes, score máximo)
        """
        # Calcular fecha límite
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
        
        # Obtener todas las noticias recientes
        recent_news = db.query(NewsItem).filter(
            NewsItem.created_at >= cutoff_time
        ).order_by(NewsItem.created_at.desc()).all()
        
        if not recent_news:
            return [], 0.0
        
        # Obtener cartera para scoring
        portfolio_items_db = db.query(PortfolioItem).all()
        portfolio_items = [PortfolioItemResponse.model_validate(item) for item in portfolio_items_db]
        
        # Filtrar por símbolo si se especifica
        if symbol:
            portfolio_items = [p for p in portfolio_items if p.symbol and p.symbol.upper() == symbol.upper()]
        
        # Filtrar por tipo de activo si se especifica
        if asset_type:
            portfolio_items = [p for p in portfolio_items if p.asset_type.lower() == asset_type.lower()]
        
        # Calcular scores y filtrar
        news_responses = [NewsItemResponse.model_validate(item) for item in recent_news]
        scored_news = self.scoring_service.score_and_sort_news(news_responses, portfolio_items if portfolio_items else None)
        
        # Filtrar por score mínimo
        relevant_news = []
        max_score = 0.0
        
        for news_item, score_dict in scored_news:
            if score_dict["score"] >= min_score:
                relevant_news.append(news_item)
                max_score = max(max_score, score_dict["score"])
        
        return relevant_news, max_score
    
    def check_price_condition(
        self,
        trigger: AlertTrigger,
        current_price: Optional[float] = None,
        previous_close: Optional[float] = None,
        open_price: Optional[float] = None
    ) -> Tuple[bool, Optional[float], Optional[float], Optional[float]]:
        """
        Verifica si se cumple la condición de precio del trigger.
        
        Nota: Esta implementación es una estructura base. En producción, necesitarías
        integrar con una API de precios en tiempo real (Alpha Vantage, Yahoo Finance, etc.).
        
        Returns:
            Tuple[bool, Optional[float], Optional[float], Optional[float]]: 
            (condición_cumplida, precio_actual, cambio_porcentual, gap_porcentual)
        """
        # Si no hay datos de precio, retornar False (en producción, obtener de API)
        if current_price is None:
            logger.warning(f"Trigger {trigger.id}: No hay datos de precio disponibles")
            return False, None, None, None
        
        price_change_percent = None
        gap_percent = None
        
        if trigger.price_trigger_type == "intraday_change":
            # Cambio intradía: necesita precio anterior de cierre
            if previous_close is None:
                return False, current_price, None, None
            
            price_change_percent = ((current_price - previous_close) / previous_close) * 100
            
            if trigger.price_threshold:
                # Verificar si supera el umbral (positivo o negativo)
                condition_met = abs(price_change_percent) >= abs(trigger.price_threshold)
                return condition_met, current_price, price_change_percent, None
        
        elif trigger.price_trigger_type == "gap":
            # Gap de apertura: necesita precio de cierre anterior y precio de apertura
            if previous_close is None or open_price is None:
                return False, current_price, None, None
            
            gap_percent = ((open_price - previous_close) / previous_close) * 100
            
            if trigger.gap_threshold:
                condition_met = abs(gap_percent) >= abs(trigger.gap_threshold)
                return condition_met, current_price, None, gap_percent
        
        elif trigger.price_trigger_type == "absolute":
            # Precio absoluto: compara con umbral
            if trigger.price_threshold:
                condition_met = current_price >= trigger.price_threshold
                return condition_met, current_price, None, None
        
        return False, current_price, price_change_percent, gap_percent
    
    def generate_alert_content(
        self,
        trigger: AlertTrigger,
        relevant_news: List[NewsItemResponse],
        price_info: Dict
    ) -> Tuple[str, str, str]:
        """
        Genera el contenido de la alerta basado en el trigger y noticias relevantes.
        
        Returns:
            Tuple[str, str, str]: (resumen, impacto_esperado, acción_sugerida)
        """
        symbol_str = trigger.symbol or trigger.asset_type or "activo"
        
        # Construir resumen
        summary_parts = [f"🚨 Alerta para {symbol_str}"]
        
        if price_info.get("price_change_percent"):
            direction = "📈" if price_info["price_change_percent"] > 0 else "📉"
            summary_parts.append(f"{direction} Cambio: {price_info['price_change_percent']:.2f}%")
        
        if price_info.get("gap_percent"):
            direction = "📈" if price_info["gap_percent"] > 0 else "📉"
            summary_parts.append(f"{direction} Gap: {price_info['gap_percent']:.2f}%")
        
        summary_parts.append(f"📰 Noticias relevantes: {len(relevant_news)}")
        
        summary = " | ".join(summary_parts)
        
        # Construir impacto esperado
        if relevant_news:
            news_titles = [n.title or "Sin título" for n in relevant_news[:3]]
            impact = f"Impacto potencial basado en {len(relevant_news)} noticia(s) relevante(s). "
            impact += f"Temas: {', '.join(news_titles[:3])}"
        else:
            impact = "Cambio de precio detectado. Revisar contexto de mercado."
        
        # Construir acción sugerida
        if price_info.get("price_change_percent", 0) > 5:
            action = "⚠️ Movimiento significativo al alza. Considerar revisar posición y tomar ganancias parciales."
        elif price_info.get("price_change_percent", 0) < -5:
            action = "⚠️ Movimiento significativo a la baja. Evaluar stop-loss y reducir exposición si es necesario."
        elif relevant_news and len(relevant_news) >= 3:
            action = "📰 Múltiples noticias relevantes. Revisar análisis completo para contexto."
        else:
            action = "🔍 Monitorear situación y revisar análisis de noticias para más contexto."
        
        return summary, impact, action
    
    def check_trigger(
        self,
        db: Session,
        trigger: AlertTrigger,
        price_data: Optional[Dict] = None
    ) -> Optional[AlertHistory]:
        """
        Verifica un trigger y genera alerta si se cumplen las condiciones.
        
        Args:
            db: Sesión de base de datos
            trigger: Trigger a verificar
            price_data: Diccionario con datos de precio (opcional, estructura base para integración futura)
                Formato esperado: {
                    'symbol': 'AAPL',
                    'current_price': 150.0,
                    'previous_close': 148.0,
                    'open_price': 149.0
                }
        
        Returns:
            AlertHistory si se dispara la alerta, None en caso contrario
        """
        if not trigger.is_active:
            return None
        
        # Verificar condición de precio
        current_price = price_data.get("current_price") if price_data else None
        previous_close = price_data.get("previous_close") if price_data else None
        open_price = price_data.get("open_price") if price_data else None
        
        price_condition_met, price_value, price_change, gap_percent = self.check_price_condition(
            trigger, current_price, previous_close, open_price
        )
        
        if not price_condition_met:
            logger.debug(f"Trigger {trigger.id}: Condición de precio no cumplida")
            return None
        
        # Verificar condición de noticias si está habilitada
        news_condition_met = True
        relevant_news = []
        max_news_score = 0.0
        
        if trigger.require_recent_news:
            relevant_news, max_news_score = self.get_recent_relevant_news(
                db,
                symbol=trigger.symbol,
                asset_type=trigger.asset_type,
                max_age_hours=trigger.news_max_age_hours,
                min_score=trigger.news_relevance_threshold
            )
            
            news_condition_met = len(relevant_news) > 0 and max_news_score >= trigger.news_relevance_threshold
        
        if not news_condition_met:
            logger.debug(f"Trigger {trigger.id}: Condición de noticias no cumplida")
            return None
        
        # Ambas condiciones cumplidas: generar alerta
        price_info = {
            "price_value": price_value,
            "price_change_percent": price_change,
            "gap_percent": gap_percent
        }
        
        summary, impact, action = self.generate_alert_content(trigger, relevant_news, price_info)
        
        # Obtener nombre del activo
        asset_name = trigger.symbol or trigger.asset_type or "Activo general"
        if trigger.symbol:
            portfolio_item = db.query(PortfolioItem).filter(
                PortfolioItem.symbol == trigger.symbol
            ).first()
            if portfolio_item:
                asset_name = portfolio_item.name
        
        # Crear registro de alerta
        alert = AlertHistory(
            trigger_id=trigger.id,
            symbol=trigger.symbol,
            asset_name=asset_name,
            price_condition_met=True,
            news_condition_met=True,
            price_value=price_value,
            price_change_percent=price_change,
            gap_percent=gap_percent,
            relevant_news_count=len(relevant_news),
            highest_news_score=max_news_score,
            alert_summary=summary,
            expected_impact=impact,
            suggested_action=action
        )
        
        db.add(alert)
        db.commit()
        db.refresh(alert)
        
        logger.info(f"Alerta generada: Trigger {trigger.id} para {asset_name}")
        return alert
    
    def check_all_active_triggers(
        self,
        db: Session,
        price_data_map: Optional[Dict[str, Dict]] = None
    ) -> List[AlertHistory]:
        """
        Verifica todos los triggers activos y genera alertas.
        
        Args:
            db: Sesión de base de datos
            price_data_map: Mapa de símbolos a datos de precio (opcional)
                Formato: {'AAPL': {'current_price': 150.0, ...}, ...}
        
        Returns:
            Lista de alertas generadas
        """
        active_triggers = db.query(AlertTrigger).filter(AlertTrigger.is_active == True).all()
        
        alerts_generated = []
        
        for trigger in active_triggers:
            try:
                # Obtener datos de precio para este trigger
                price_data = None
                if price_data_map and trigger.symbol:
                    price_data = price_data_map.get(trigger.symbol.upper())
                
                alert = self.check_trigger(db, trigger, price_data)
                
                if alert:
                    alerts_generated.append(alert)
            
            except Exception as e:
                logger.error(f"Error verificando trigger {trigger.id}: {e}", exc_info=True)
        
        return alerts_generated


