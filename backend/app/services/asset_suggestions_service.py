"""Servicio para generar sugerencias de nuevos activos con guardrails."""
import logging
import json
import re
from typing import List, Dict, Tuple, Optional
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session

from app.database import NewsItem, PortfolioItem, AssetSuggestion
from app.models import NewsItemResponse, PortfolioItemResponse
from app.services.news_scoring_service import NewsScoringService
from app.config import (
    SUGGESTIONS_MIN_NEWS_SCORE,
    SUGGESTIONS_MAX_CORRELATION,
    SUGGESTIONS_MIN_CONFIDENCE,
    SUGGESTIONS_MAX_POSITION_PCT,
    SUGGESTIONS_NEWS_LOOKBACK_HOURS
)

logger = logging.getLogger(__name__)


class AssetSuggestionsService:
    """Servicio para generar sugerencias de activos."""
    
    def __init__(self):
        self.scoring_service = NewsScoringService()
    
    def extract_assets_from_news(self, db: Session, lookback_hours: int = 168) -> Dict[str, Dict]:
        """
        Extrae activos mencionados en noticias recientes.
        
        Returns:
            Dict[str, Dict]: {symbol: {name, asset_type, news_count, total_score, news_ids}}
        """
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)
        
        recent_news = db.query(NewsItem).filter(
            NewsItem.created_at >= cutoff_time
        ).order_by(NewsItem.created_at.desc()).all()
        
        if not recent_news:
            return {}
        
        # Obtener portfolio para scoring
        portfolio_items_db = db.query(PortfolioItem).all()
        portfolio_items = [PortfolioItemResponse.model_validate(item) for item in portfolio_items_db]
        
        # Diccionario para acumular información por activo
        assets_found: Dict[str, Dict] = {}
        
        # Patrón común para detectar tickers (1-5 letras mayúsculas, seguido opcionalmente de punto)
        ticker_pattern = re.compile(r'\b([A-Z]{1,5})(?:\.[A-Z]{1,2})?\b')
        
        for news_item in recent_news:
            news_response = NewsItemResponse.model_validate(news_item)
            
            # Calcular score
            scored_news = self.scoring_service.score_and_sort_news([news_response], portfolio_items)
            if not scored_news:
                continue
            
            _, score_dict = scored_news[0]
            score = score_dict["score"]
            
            if score < SUGGESTIONS_MIN_NEWS_SCORE:
                continue
            
            # Buscar tickers en título y cuerpo
            text_to_search = f"{news_item.title or ''} {news_item.body}".upper()
            matches = ticker_pattern.findall(text_to_search)
            
            for ticker_match in matches:
                symbol = ticker_match.upper()
                
                # Ignorar palabras comunes que no son tickers
                common_words = {'THE', 'AND', 'FOR', 'ARE', 'BUT', 'NOT', 'YOU', 'ALL', 'CAN', 'HER', 'WAS', 'ONE', 'OUR', 'OUT', 'DAY', 'GET', 'HAS', 'HIM', 'HIS', 'HOW', 'ITS', 'MAY', 'NEW', 'NOW', 'OLD', 'SEE', 'TWO', 'WHO', 'WAY', 'USE', 'HER', 'SHE', 'MAN', 'HAS', 'HAD', 'BUT'}
                if symbol in common_words or len(symbol) < 2:
                    continue
                
                if symbol not in assets_found:
                    assets_found[symbol] = {
                        "name": symbol,  # Por defecto, usar símbolo como nombre
                        "symbol": symbol,
                        "asset_type": "acciones",  # Por defecto
                        "news_count": 0,
                        "total_score": 0.0,
                        "news_ids": []
                    }
                
                assets_found[symbol]["news_count"] += 1
                assets_found[symbol]["total_score"] += score
                assets_found[symbol]["news_ids"].append(news_item.id)
        
        # Calcular score promedio y filtrar
        filtered_assets = {}
        for symbol, data in assets_found.items():
            avg_score = data["total_score"] / data["news_count"]
            if avg_score >= SUGGESTIONS_MIN_NEWS_SCORE and data["news_count"] >= 1:
                data["avg_score"] = avg_score
                filtered_assets[symbol] = data
        
        return filtered_assets
    
    def calculate_correlation(
        self,
        symbol: str,
        portfolio_symbols: List[str],
        portfolio_items: List[PortfolioItemResponse]
    ) -> Optional[float]:
        """
        Calcula correlación estimada entre un activo y la cartera.
        
        Nota: Esta es una implementación simplificada. En producción, usar datos históricos reales.
        Por ahora, asume correlación baja para activos diferentes y alta para similares.
        
        Returns:
            Optional[float]: Correlación estimada (-1 a 1), None si no hay datos
        """
        # Si el activo ya está en la cartera, correlación = 1.0
        if symbol in [s.upper() for s in portfolio_symbols]:
            return 1.0
        
        # Correlaciones estimadas por tipo de activo
        # En producción, esto debería usar datos históricos reales
        asset_types = {
            "acciones": 0.7,  # Correlación promedio entre acciones
            "bonos": 0.2,     # Baja correlación acciones-bonos
            "etf": 0.6,       # Correlación media ETFs-acciones
            "fondos": 0.5,    # Correlación media
            "divisas": 0.1,   # Muy baja correlación
            "otros": 0.3
        }
        
        # Determinar tipo de activo (simplificado, asumir acciones por defecto)
        asset_type = "acciones"
        
        # Calcular correlación promedio ponderada con la cartera
        if not portfolio_items:
            return 0.0
        
        portfolio_type_weights = {}
        for item in portfolio_items:
            item_type = item.asset_type.lower()
            portfolio_type_weights[item_type] = portfolio_type_weights.get(item_type, 0) + 1
        
        # Correlación estimada basada en tipos de activo
        estimated_correlation = asset_types.get(asset_type, 0.5)
        
        # Ajustar según diversidad de la cartera
        portfolio_diversity = len(portfolio_type_weights)
        if portfolio_diversity > 3:
            estimated_correlation *= 0.8  # Carters diversificadas tienen menor correlación
        
        return estimated_correlation
    
    def determine_reason(
        self,
        symbol: str,
        correlation: Optional[float],
        news_score: float,
        portfolio_items: List[PortfolioItemResponse]
    ) -> Tuple[str, str]:
        """
        Determina el motivo de la sugerencia.
        
        Returns:
            Tuple[str, str]: (reason_code, reason_description)
        """
        # Motivo: Diversificación
        if correlation is not None and correlation < 0.3:
            return (
                "diversification",
                f"Baja correlación ({correlation:.2f}) con la cartera actual. Ayuda a reducir riesgo mediante diversificación."
            )
        
        # Motivo: Hedge
        portfolio_types = [item.asset_type.lower() for item in portfolio_items]
        if "acciones" in portfolio_types and correlation is not None and correlation < 0.5:
            return (
                "hedge",
                f"Correlación moderada ({correlation:.2f}). Puede servir como hedge ante movimientos del mercado de acciones."
            )
        
        # Motivo: Momentum
        if news_score >= 5.0:
            return (
                "momentum",
                f"Alta relevancia en noticias recientes (score: {news_score:.2f}). Posible momentum positivo."
            )
        
        # Default: Diversificación
        return (
            "diversification",
            "Activo identificado en noticias recientes con relevancia suficiente para considerar."
        )
    
    def calculate_position_size(
        self,
        reason: str,
        correlation: Optional[float],
        confidence: float,
        portfolio_value: float
    ) -> Tuple[float, Optional[float]]:
        """
        Calcula tamaño de posición sugerido con guardrails.
        
        Returns:
            Tuple[float, Optional[float]]: (percentage, max_value_usd)
        """
        # Base según motivo
        base_pct = {
            "diversification": 10.0,
            "hedge": 15.0,
            "momentum": 5.0
        }.get(reason, 8.0)
        
        # Ajustar por confianza
        adjusted_pct = base_pct * confidence
        
        # Ajustar por correlación (mayor posición si correlación más baja)
        if correlation is not None:
            if correlation < 0.2:
                adjusted_pct *= 1.2
            elif correlation > 0.6:
                adjusted_pct *= 0.7
        
        # Aplicar límite máximo
        adjusted_pct = min(adjusted_pct, SUGGESTIONS_MAX_POSITION_PCT)
        
        max_value = portfolio_value * (adjusted_pct / 100.0) if portfolio_value > 0 else None
        
        return round(adjusted_pct, 1), round(max_value, 2) if max_value else None
    
    def calculate_confidence(
        self,
        news_score: float,
        news_count: int,
        correlation_available: bool,
        correlation: Optional[float]
    ) -> float:
        """
        Calcula nivel de confianza de la sugerencia.
        
        Returns:
            float: Confianza entre 0.0 y 1.0
        """
        confidence = 0.5  # Base
        
        # Factor de noticias (más noticias = más confianza)
        news_factor = min(news_count / 5.0, 1.0)  # Máximo 1.0 con 5+ noticias
        confidence += 0.2 * news_factor
        
        # Factor de score (mayor score = más confianza)
        score_factor = min(news_score / 10.0, 1.0)  # Máximo 1.0 con score 10+
        confidence += 0.2 * score_factor
        
        # Factor de datos de correlación
        if correlation_available:
            confidence += 0.1
        
        # Ajustar por correlación (baja correlación = más confianza para diversificación)
        if correlation is not None and correlation < 0.3:
            confidence += 0.1
        
        return min(confidence, 1.0)
    
    def generate_suggestions(
        self,
        db: Session,
        min_news_score: float = SUGGESTIONS_MIN_NEWS_SCORE,
        max_correlation: float = SUGGESTIONS_MAX_CORRELATION,
        min_confidence: float = SUGGESTIONS_MIN_CONFIDENCE,
        max_suggestions: int = 10
    ) -> List[AssetSuggestion]:
        """
        Genera sugerencias de nuevos activos con guardrails.
        
        Returns:
            List[AssetSuggestion]: Lista de sugerencias generadas
        """
        # Calcular valor de cartera
        portfolio_items_db = db.query(PortfolioItem).all()
        portfolio_items = [PortfolioItemResponse.model_validate(item) for item in portfolio_items_db]
        
        portfolio_value = 0.0
        for item in portfolio_items:
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
        
        if portfolio_value == 0:
            portfolio_value = 100000.0  # Default para cálculo
        
        portfolio_symbols = [item.symbol.upper() for item in portfolio_items if item.symbol]
        
        # Extraer activos de noticias
        assets_found = self.extract_assets_from_news(db, SUGGESTIONS_NEWS_LOOKBACK_HOURS)
        
        if not assets_found:
            logger.info("No se encontraron activos relevantes en noticias recientes")
            return []
        
        # Generar sugerencias
        suggestions = []
        
        for symbol, asset_data in assets_found.items():
            # Filtrar si ya está en cartera
            if symbol in portfolio_symbols:
                continue
            
            # Calcular correlación
            correlation = self.calculate_correlation(symbol, portfolio_symbols, portfolio_items)
            correlation_available = correlation is not None
            
            # Filtrar por correlación máxima
            if correlation is not None and correlation > max_correlation:
                continue
            
            # Calcular confianza
            confidence = self.calculate_confidence(
                asset_data["avg_score"],
                asset_data["news_count"],
                correlation_available,
                correlation
            )
            
            # Filtrar por confianza mínima
            if confidence < min_confidence:
                continue
            
            # Determinar motivo
            reason, reason_description = self.determine_reason(
                symbol,
                correlation,
                asset_data["avg_score"],
                portfolio_items
            )
            
            # Calcular tamaño de posición
            position_pct, max_value = self.calculate_position_size(
                reason,
                correlation,
                confidence,
                portfolio_value
            )
            
            # Crear sugerencia
            suggestion = AssetSuggestion(
                asset_type=asset_data["asset_type"],
                name=asset_data["name"],
                symbol=symbol,
                reason=reason,
                reason_description=reason_description,
                correlation_with_portfolio=correlation,
                news_relevance_score=round(asset_data["avg_score"], 2),
                news_count=asset_data["news_count"],
                suggested_position_size_pct=position_pct,
                max_position_value=max_value,
                confidence_level=round(confidence, 2),
                supporting_news_ids=json.dumps(asset_data["news_ids"]),
                correlation_data_available=correlation_available
            )
            
            suggestions.append(suggestion)
        
        # Ordenar por confianza y score, limitar cantidad
        suggestions.sort(key=lambda s: (s.confidence_level, s.news_relevance_score), reverse=True)
        suggestions = suggestions[:max_suggestions]
        
        return suggestions

