"""Servicio de scoring diferenciado por tipo de activo con métricas específicas."""
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session

from app.models import PortfolioItemResponse, NewsItemResponse
from app.services.news_scoring_service import NewsScoringService
from app.services.market_features_service import MarketFeaturesService

logger = logging.getLogger(__name__)


class MultiAssetScoringService:
    """Servicio para calcular scores diferenciados por tipo de activo."""
    
    def __init__(self):
        self.news_scoring_service = NewsScoringService()
        self.market_features_service = MarketFeaturesService()
    
    def calculate_asset_score(
        self,
        db: Session,
        item: PortfolioItemResponse,
        news_items: List[NewsItemResponse],
        lookback_hours: int = 168
    ) -> Dict:
        """
        Calcula score diferenciado según tipo de activo.
        
        Args:
            db: Sesión de base de datos
            item: Item de cartera
            news_items: Lista de noticias relacionadas
            lookback_hours: Horas de lookback para frescura
            
        Returns:
            Dict con score y desglose completo de contribuciones
        """
        asset_type = item.asset_type.lower()
        
        # Determinar tipo de activo y calcular score específico
        if asset_type in ['acciones', 'stock', 'stocks']:
            return self._calculate_stock_score(item, news_items, lookback_hours)
        elif asset_type in ['bonos', 'bond', 'bonds', 'renta fija']:
            return self._calculate_bond_score(item, news_items, lookback_hours)
        elif asset_type in ['divisas', 'fx', 'currency', 'forex']:
            return self._calculate_fx_score(item, news_items, lookback_hours)
        elif asset_type in ['commodities', 'commodity', 'materias primas']:
            return self._calculate_commodity_score(item, news_items, lookback_hours)
        else:
            # Tipo genérico o desconocido
            return self._calculate_generic_score(item, news_items, lookback_hours)
    
    def _calculate_stock_score(
        self,
        item: PortfolioItemResponse,
        news_items: List[NewsItemResponse],
        lookback_hours: int
    ) -> Dict:
        """Calcula score para acciones con métricas específicas."""
        # 1. Sentimiento (40% peso)
        sentiment_score, sentiment_breakdown = self._calculate_sentiment_breakdown(news_items, lookback_hours)
        
        # 2. Técnico (40% peso) - RSI, MA, volumen, momentum
        technical_score, technical_breakdown = self._calculate_stock_technical(item)
        
        # 3. Frescura (10% peso) - Antigüedad de noticias
        freshness_score, freshness_breakdown = self._calculate_freshness_breakdown(news_items, lookback_hours)
        
        # 4. Cobertura de datos (10% peso) - Cantidad y calidad de datos disponibles
        coverage_score, coverage_breakdown = self._calculate_coverage_breakdown(news_items, technical_breakdown)
        
        # Calcular score compuesto
        composite_score = (
            sentiment_score * 0.4 +
            technical_score * 0.4 +
            freshness_score * 0.1 +
            coverage_score * 0.1
        )
        
        return {
            "composite_score": composite_score,
            "asset_type": "acciones",
            "breakdown": {
                "sentiment": {
                    "score": sentiment_score,
                    "weight": 0.4,
                    "contribution": sentiment_score * 0.4,
                    "details": sentiment_breakdown
                },
                "technical": {
                    "score": technical_score,
                    "weight": 0.4,
                    "contribution": technical_score * 0.4,
                    "details": technical_breakdown
                },
                "freshness": {
                    "score": freshness_score,
                    "weight": 0.1,
                    "contribution": freshness_score * 0.1,
                    "details": freshness_breakdown
                },
                "coverage": {
                    "score": coverage_score,
                    "weight": 0.1,
                    "contribution": coverage_score * 0.1,
                    "details": coverage_breakdown
                }
            },
            "data_sufficiency": self._assess_data_sufficiency(news_items, technical_breakdown)
        }
    
    def _calculate_bond_score(
        self,
        item: PortfolioItemResponse,
        news_items: List[NewsItemResponse],
        lookback_hours: int
    ) -> Dict:
        """Calcula score para bonos con métricas específicas (tasas, spreads, rating)."""
        # Para bonos: más peso en macro y menos en técnico
        # 1. Sentimiento macro (50% peso)
        sentiment_score, sentiment_breakdown = self._calculate_sentiment_breakdown(news_items, lookback_hours, macro_focus=True)
        
        # 2. Técnico/macro (30% peso) - Yield, spread, rating changes
        technical_score, technical_breakdown = self._calculate_bond_technical(item)
        
        # 3. Frescura (10% peso)
        freshness_score, freshness_breakdown = self._calculate_freshness_breakdown(news_items, lookback_hours)
        
        # 4. Cobertura (10% peso)
        coverage_score, coverage_breakdown = self._calculate_coverage_breakdown(news_items, technical_breakdown)
        
        composite_score = (
            sentiment_score * 0.5 +
            technical_score * 0.3 +
            freshness_score * 0.1 +
            coverage_score * 0.1
        )
        
        return {
            "composite_score": composite_score,
            "asset_type": "bonos",
            "breakdown": {
                "sentiment": {
                    "score": sentiment_score,
                    "weight": 0.5,
                    "contribution": sentiment_score * 0.5,
                    "details": sentiment_breakdown
                },
                "technical": {
                    "score": technical_score,
                    "weight": 0.3,
                    "contribution": technical_score * 0.3,
                    "details": technical_breakdown
                },
                "freshness": {
                    "score": freshness_score,
                    "weight": 0.1,
                    "contribution": freshness_score * 0.1,
                    "details": freshness_breakdown
                },
                "coverage": {
                    "score": coverage_score,
                    "weight": 0.1,
                    "contribution": coverage_score * 0.1,
                    "details": coverage_breakdown
                }
            },
            "data_sufficiency": self._assess_data_sufficiency(news_items, technical_breakdown)
        }
    
    def _calculate_fx_score(
        self,
        item: PortfolioItemResponse,
        news_items: List[NewsItemResponse],
        lookback_hours: int
    ) -> Dict:
        """Calcula score para divisas con métricas específicas (tipo de cambio, interés diferencial)."""
        # Para FX: más peso en macro y política monetaria
        # 1. Sentimiento macro (45% peso)
        sentiment_score, sentiment_breakdown = self._calculate_sentiment_breakdown(news_items, lookback_hours, macro_focus=True)
        
        # 2. Técnico/macro (35% peso) - Tipo de cambio, interés diferencial
        technical_score, technical_breakdown = self._calculate_fx_technical(item)
        
        # 3. Frescura (10% peso)
        freshness_score, freshness_breakdown = self._calculate_freshness_breakdown(news_items, lookback_hours)
        
        # 4. Cobertura (10% peso)
        coverage_score, coverage_breakdown = self._calculate_coverage_breakdown(news_items, technical_breakdown)
        
        composite_score = (
            sentiment_score * 0.45 +
            technical_score * 0.35 +
            freshness_score * 0.1 +
            coverage_score * 0.1
        )
        
        return {
            "composite_score": composite_score,
            "asset_type": "divisas",
            "breakdown": {
                "sentiment": {
                    "score": sentiment_score,
                    "weight": 0.45,
                    "contribution": sentiment_score * 0.45,
                    "details": sentiment_breakdown
                },
                "technical": {
                    "score": technical_score,
                    "weight": 0.35,
                    "contribution": technical_score * 0.35,
                    "details": technical_breakdown
                },
                "freshness": {
                    "score": freshness_score,
                    "weight": 0.1,
                    "contribution": freshness_score * 0.1,
                    "details": freshness_breakdown
                },
                "coverage": {
                    "score": coverage_score,
                    "weight": 0.1,
                    "contribution": coverage_score * 0.1,
                    "details": coverage_breakdown
                }
            },
            "data_sufficiency": self._assess_data_sufficiency(news_items, technical_breakdown)
        }
    
    def _calculate_commodity_score(
        self,
        item: PortfolioItemResponse,
        news_items: List[NewsItemResponse],
        lookback_hours: int
    ) -> Dict:
        """Calcula score para commodities con métricas específicas (oferta/demanda, inventarios)."""
        # Para commodities: balance entre macro y técnico
        # 1. Sentimiento (40% peso) - Oferta/demanda, inventarios
        sentiment_score, sentiment_breakdown = self._calculate_sentiment_breakdown(news_items, lookback_hours, macro_focus=True)
        
        # 2. Técnico (40% peso) - Precio, momentum, inventarios
        technical_score, technical_breakdown = self._calculate_commodity_technical(item)
        
        # 3. Frescura (10% peso)
        freshness_score, freshness_breakdown = self._calculate_freshness_breakdown(news_items, lookback_hours)
        
        # 4. Cobertura (10% peso)
        coverage_score, coverage_breakdown = self._calculate_coverage_breakdown(news_items, technical_breakdown)
        
        composite_score = (
            sentiment_score * 0.4 +
            technical_score * 0.4 +
            freshness_score * 0.1 +
            coverage_score * 0.1
        )
        
        return {
            "composite_score": composite_score,
            "asset_type": "commodities",
            "breakdown": {
                "sentiment": {
                    "score": sentiment_score,
                    "weight": 0.4,
                    "contribution": sentiment_score * 0.4,
                    "details": sentiment_breakdown
                },
                "technical": {
                    "score": technical_score,
                    "weight": 0.4,
                    "contribution": technical_score * 0.4,
                    "details": technical_breakdown
                },
                "freshness": {
                    "score": freshness_score,
                    "weight": 0.1,
                    "contribution": freshness_score * 0.1,
                    "details": freshness_breakdown
                },
                "coverage": {
                    "score": coverage_score,
                    "weight": 0.1,
                    "contribution": coverage_score * 0.1,
                    "details": coverage_breakdown
                }
            },
            "data_sufficiency": self._assess_data_sufficiency(news_items, technical_breakdown)
        }
    
    def _calculate_generic_score(
        self,
        item: PortfolioItemResponse,
        news_items: List[NewsItemResponse],
        lookback_hours: int
    ) -> Dict:
        """Calcula score genérico para tipos de activo desconocidos."""
        # Score genérico con pesos balanceados
        sentiment_score, sentiment_breakdown = self._calculate_sentiment_breakdown(news_items, lookback_hours)
        technical_score, technical_breakdown = self._calculate_generic_technical(item)
        freshness_score, freshness_breakdown = self._calculate_freshness_breakdown(news_items, lookback_hours)
        coverage_score, coverage_breakdown = self._calculate_coverage_breakdown(news_items, technical_breakdown)
        
        composite_score = (
            sentiment_score * 0.5 +
            technical_score * 0.3 +
            freshness_score * 0.1 +
            coverage_score * 0.1
        )
        
        return {
            "composite_score": composite_score,
            "asset_type": "genérico",
            "breakdown": {
                "sentiment": {
                    "score": sentiment_score,
                    "weight": 0.5,
                    "contribution": sentiment_score * 0.5,
                    "details": sentiment_breakdown
                },
                "technical": {
                    "score": technical_score,
                    "weight": 0.3,
                    "contribution": technical_score * 0.3,
                    "details": technical_breakdown
                },
                "freshness": {
                    "score": freshness_score,
                    "weight": 0.1,
                    "contribution": freshness_score * 0.1,
                    "details": freshness_breakdown
                },
                "coverage": {
                    "score": coverage_score,
                    "weight": 0.1,
                    "contribution": coverage_score * 0.1,
                    "details": coverage_breakdown
                }
            },
            "data_sufficiency": self._assess_data_sufficiency(news_items, technical_breakdown)
        }
    
    def _calculate_sentiment_breakdown(
        self,
        news_items: List[NewsItemResponse],
        lookback_hours: int,
        macro_focus: bool = False
    ) -> Tuple[float, Dict]:
        """Calcula score de sentimiento con desglose detallado."""
        if not news_items:
            return 0.5, {
                "score": 0.5,
                "news_count": 0,
                "positive_count": 0,
                "negative_count": 0,
                "neutral_count": 0,
                "avg_sentiment": 0.0,
                "data_quality": "insufficient",
                "message": "Sin noticias disponibles"
            }
        
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)
        recent_news = [
            news for news in news_items
            if datetime.fromisoformat(news.created_at.replace('Z', '+00:00')) >= cutoff_time
        ]
        
        if not recent_news:
            return 0.5, {
                "score": 0.5,
                "news_count": 0,
                "positive_count": 0,
                "negative_count": 0,
                "neutral_count": 0,
                "avg_sentiment": 0.0,
                "data_quality": "insufficient",
                "message": f"Sin noticias en las últimas {lookback_hours // 24} días"
            }
        
        # Calcular sentimiento por noticia
        sentiments = []
        positive_count = 0
        negative_count = 0
        neutral_count = 0
        
        for news in recent_news:
            try:
                score_dict = self.news_scoring_service.calculate_news_score(news, [])
                sentiment_type = score_dict["components"].get("sentiment_type", "neutral")
                
                if sentiment_type == "positive":
                    sentiments.append(1.0)
                    positive_count += 1
                elif sentiment_type == "negative":
                    sentiments.append(-1.0)
                    negative_count += 1
                else:
                    sentiments.append(0.0)
                    neutral_count += 1
            except Exception as e:
                logger.warning(f"Error scoring news {news.id}: {e}")
                sentiments.append(0.0)
                neutral_count += 1
        
        if not sentiments:
            return 0.5, {
                "score": 0.5,
                "news_count": len(recent_news),
                "positive_count": 0,
                "negative_count": 0,
                "neutral_count": 0,
                "avg_sentiment": 0.0,
                "data_quality": "insufficient",
                "message": "Error al procesar sentimiento de noticias"
            }
        
        avg_sentiment = sum(sentiments) / len(sentiments)
        # Normalizar a 0-1 (donde 0.5 = neutro)
        normalized_score = (avg_sentiment + 1.0) / 2.0
        
        # Determinar calidad de datos
        total_count = len(recent_news)
        if total_count >= 5:
            data_quality = "high"
        elif total_count >= 2:
            data_quality = "medium"
        else:
            data_quality = "low"
        
        return normalized_score, {
            "score": normalized_score,
            "news_count": total_count,
            "positive_count": positive_count,
            "negative_count": negative_count,
            "neutral_count": neutral_count,
            "avg_sentiment": avg_sentiment,
            "data_quality": data_quality,
            "message": f"{total_count} noticias analizadas ({positive_count} positivas, {negative_count} negativas, {neutral_count} neutras)"
        }
    
    def _calculate_stock_technical(self, item: PortfolioItemResponse) -> Tuple[float, Dict]:
        """Calcula score técnico específico para acciones."""
        if not item.symbol:
            return 0.5, {
                "score": 0.5,
                "signals": {},
                "data_quality": "insufficient",
                "message": "Sin símbolo para análisis técnico"
            }
        
        market_features = self.market_features_service.get_market_features(item.symbol)
        signals = {}
        signal_scores = []
        
        # RSI
        price_change = market_features.get("intraday_change_pct")
        if price_change is not None:
            momentum = price_change
            if momentum > 3.0:
                rsi_estimate = 70.0
            elif momentum < -3.0:
                rsi_estimate = 30.0
            else:
                rsi_estimate = 50.0 + (momentum * 5.0)
            
            rsi_score = max(0.0, min(1.0, (rsi_estimate - 30.0) / 40.0))
            signals["rsi"] = {"value": rsi_estimate, "score": rsi_score, "description": f"RSI: {rsi_estimate:.1f}"}
            signal_scores.append(("rsi", rsi_score, 0.3))
        
        # Volumen
        volume_ratio = market_features.get("volume_ratio")
        if volume_ratio is not None:
            volume_score = max(0.0, min(1.0, 0.5 + (volume_ratio - 1.0) / 2.0))
            signals["volume"] = {"value": volume_ratio, "score": volume_score, "description": f"Volumen: {volume_ratio:.2f}x"}
            signal_scores.append(("volume", volume_score, 0.3))
        
        # Tendencia (MA)
        if price_change is not None:
            trend_score = max(0.0, min(1.0, 0.5 + (price_change / 10.0)))
            signals["trend"] = {"value": price_change, "score": trend_score, "description": f"Tendencia: {price_change:+.2f}%"}
            signal_scores.append(("trend", trend_score, 0.4))
        
        if signal_scores:
            total_weight = sum(w for _, _, w in signal_scores)
            technical_score = sum(score * weight for _, score, weight in signal_scores) / total_weight
            data_quality = "high" if len(signals) >= 3 else "medium"
        else:
            technical_score = 0.5
            data_quality = "insufficient"
        
        return technical_score, {
            "score": technical_score,
            "signals": signals,
            "data_quality": data_quality,
            "message": f"{len(signals)} señales técnicas disponibles" if signals else "Sin señales técnicas disponibles"
        }
    
    def _calculate_bond_technical(self, item: PortfolioItemResponse) -> Tuple[float, Dict]:
        """Calcula score técnico/macro específico para bonos."""
        # Para bonos, el técnico se enfoca en yield, spread, rating
        # Por ahora, retornamos score neutro con mensaje de datos insuficientes
        return 0.5, {
            "score": 0.5,
            "signals": {},
            "data_quality": "insufficient",
            "message": "Datos de yield/spread no disponibles. Score neutro por defecto."
        }
    
    def _calculate_fx_technical(self, item: PortfolioItemResponse) -> Tuple[float, Dict]:
        """Calcula score técnico/macro específico para divisas."""
        # Para FX, el técnico se enfoca en tipo de cambio, interés diferencial
        # Por ahora, retornamos score neutro con mensaje de datos insuficientes
        return 0.5, {
            "score": 0.5,
            "signals": {},
            "data_quality": "insufficient",
            "message": "Datos de tipo de cambio/interés diferencial no disponibles. Score neutro por defecto."
        }
    
    def _calculate_commodity_technical(self, item: PortfolioItemResponse) -> Tuple[float, Dict]:
        """Calcula score técnico específico para commodities."""
        # Para commodities, el técnico se enfoca en precio, inventarios
        # Por ahora, retornamos score neutro con mensaje de datos insuficientes
        return 0.5, {
            "score": 0.5,
            "signals": {},
            "data_quality": "insufficient",
            "message": "Datos de precio/inventarios no disponibles. Score neutro por defecto."
        }
    
    def _calculate_generic_technical(self, item: PortfolioItemResponse) -> Tuple[float, Dict]:
        """Calcula score técnico genérico."""
        return 0.5, {
            "score": 0.5,
            "signals": {},
            "data_quality": "insufficient",
            "message": "Análisis técnico no disponible para este tipo de activo"
        }
    
    def _calculate_freshness_breakdown(
        self,
        news_items: List[NewsItemResponse],
        lookback_hours: int
    ) -> Tuple[float, Dict]:
        """Calcula score de frescura basado en antigüedad de noticias."""
        if not news_items:
            return 0.0, {
                "score": 0.0,
                "avg_age_hours": None,
                "newest_age_hours": None,
                "data_quality": "insufficient",
                "message": "Sin noticias para calcular frescura"
            }
        
        now = datetime.now(timezone.utc)
        ages = []
        
        for news in news_items:
            try:
                news_date = datetime.fromisoformat(news.created_at.replace('Z', '+00:00'))
                age_hours = (now - news_date).total_seconds() / 3600.0
                ages.append(age_hours)
            except Exception:
                continue
        
        if not ages:
            return 0.0, {
                "score": 0.0,
                "avg_age_hours": None,
                "newest_age_hours": None,
                "data_quality": "insufficient",
                "message": "Error al calcular edad de noticias"
            }
        
        avg_age_hours = sum(ages) / len(ages)
        newest_age_hours = min(ages)
        
        # Score de frescura: más reciente = mayor score
        # 0 horas = 1.0, lookback_hours = 0.0
        freshness_score = max(0.0, min(1.0, 1.0 - (newest_age_hours / lookback_hours)))
        
        return freshness_score, {
            "score": freshness_score,
            "avg_age_hours": round(avg_age_hours, 1),
            "newest_age_hours": round(newest_age_hours, 1),
            "data_quality": "high" if len(ages) >= 3 else "medium" if len(ages) >= 1 else "low",
            "message": f"Noticia más reciente: {round(newest_age_hours, 1)} horas"
        }
    
    def _calculate_coverage_breakdown(
        self,
        news_items: List[NewsItemResponse],
        technical_breakdown: Dict
    ) -> Tuple[float, Dict]:
        """Calcula score de cobertura de datos."""
        news_count = len(news_items) if news_items else 0
        technical_signals = len(technical_breakdown.get("signals", {}))
        
        # Score basado en cantidad de datos disponibles
        # Noticias: máximo 10+ = 1.0, 0 = 0.0
        news_coverage = min(1.0, news_count / 10.0)
        
        # Técnico: máximo 3+ señales = 1.0, 0 = 0.0
        technical_coverage = min(1.0, technical_signals / 3.0)
        
        # Combinar: 60% noticias, 40% técnico
        coverage_score = news_coverage * 0.6 + technical_coverage * 0.4
        
        return coverage_score, {
            "score": coverage_score,
            "news_count": news_count,
            "technical_signals_count": technical_signals,
            "data_quality": "high" if news_count >= 5 and technical_signals >= 2 else "medium" if news_count >= 2 or technical_signals >= 1 else "low",
            "message": f"{news_count} noticias, {technical_signals} señales técnicas"
        }
    
    def _assess_data_sufficiency(
        self,
        news_items: List[NewsItemResponse],
        technical_breakdown: Dict
    ) -> Dict:
        """Evalúa si hay datos suficientes o marca explícitamente 'datos insuficientes'."""
        news_count = len(news_items) if news_items else 0
        technical_signals = len(technical_breakdown.get("signals", {}))
        technical_quality = technical_breakdown.get("data_quality", "unknown")
        
        # Criterios para datos suficientes
        has_sufficient_news = news_count >= 3
        has_sufficient_technical = technical_quality in ["high", "medium"]
        
        is_sufficient = has_sufficient_news or has_sufficient_technical
        
        if is_sufficient:
            return {
                "sufficient": True,
                "message": "Datos suficientes disponibles",
                "details": {
                    "news": f"{news_count} noticias disponibles",
                    "technical": f"{technical_signals} señales técnicas disponibles"
                }
            }
        else:
            return {
                "sufficient": False,
                "message": "DATOS INSUFICIENTES",
                "details": {
                    "news": f"Solo {news_count} noticia(s) disponible(s) (mínimo recomendado: 3)",
                    "technical": f"{technical_signals} señal(es) técnica(s) disponible(s) (mínimo recomendado: 2)"
                },
                "recommendation": "Esperar más datos antes de tomar decisiones basadas en este ranking"
            }

