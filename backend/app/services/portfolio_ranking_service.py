"""
Servicio para ranking de holdings de cartera basado en análisis técnico y sentimiento.
Combina señales técnicas (RSI, MA, volumen) con sentimiento de noticias (empresa + sector).
"""
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.database import PortfolioItem, NewsItem, NormalizedNews, Sector, AssetCatalog
from app.models import PortfolioItemResponse, NewsItemResponse
from app.services.news_scoring_service import NewsScoringService
from app.services.sector_extraction_service import SectorExtractionService
from app.services.market_features_service import MarketFeaturesService
from app.config import (
    PORTFOLIO_RANKING_SENTIMENT_WEIGHT,
    PORTFOLIO_RANKING_TECHNICAL_WEIGHT,
    PORTFOLIO_RANKING_GREEN_THRESHOLD,
    PORTFOLIO_RANKING_AMBER_THRESHOLD,
    PORTFOLIO_RANKING_NEWS_LOOKBACK_HOURS,
    PORTFOLIO_RANKING_CACHE_TTL_MINUTES
)

logger = logging.getLogger(__name__)


class PortfolioRankingService:
    """Servicio para calcular rankings de holdings con traffic-light colors."""
    
    def __init__(self):
        self.news_scoring_service = NewsScoringService()
        self.sector_extractor = SectorExtractionService()
        self.market_features_service = MarketFeaturesService()
        self._cache: Dict[int, Dict] = {}
        self._cache_timestamps: Dict[int, datetime] = {}
    
    def get_portfolio_rankings(
        self,
        db: Session,
        portfolio_items: Optional[List[PortfolioItemResponse]] = None
    ) -> List[Dict]:
        """
        Calcula rankings para todos los holdings de la cartera.
        
        Returns:
            List[Dict] con: item_id, symbol, name, composite_score, sentiment_score,
            technical_score, color (green/amber/red), status_text, details
        """
        if portfolio_items is None:
            portfolio_items_db = db.query(PortfolioItem).all()
            portfolio_items = [PortfolioItemResponse.model_validate(item) for item in portfolio_items_db]
        
        rankings = []
        
        for item in portfolio_items:
            try:
                ranking = self._calculate_ranking_for_item(db, item)
                rankings.append(ranking)
            except Exception as e:
                logger.error(f"Error calculando ranking para item {item.id}: {e}", exc_info=True)
                # Fallback: ranking neutro
                rankings.append({
                    "item_id": item.id,
                    "symbol": item.symbol,
                    "name": item.name,
                    "composite_score": 50.0,
                    "sentiment_score": 50.0,
                    "technical_score": 50.0,
                    "color": "amber",
                    "status_text": "Datos insuficientes",
                    "details": {
                        "sentiment": {"score": 50.0, "explanation": "Error al calcular sentimiento"},
                        "technical": {"score": 50.0, "explanation": "Error al calcular señales técnicas"},
                        "error": str(e)
                    }
                })
        
        # Ordenar por composite_score descendente
        rankings.sort(key=lambda x: x["composite_score"], reverse=True)
        
        return rankings
    
    def _calculate_ranking_for_item(
        self,
        db: Session,
        item: PortfolioItemResponse
    ) -> Dict:
        """Calcula ranking para un item específico."""
        # Verificar caché
        cache_key = item.id
        if self._is_cache_valid(cache_key):
            return self._cache[cache_key]
        
        # Calcular sentimiento
        sentiment_result = self._calculate_sentiment_score(db, item)
        
        # Calcular señales técnicas
        technical_result = self._calculate_technical_score(item)
        
        # Combinar scores
        composite_score = (
            sentiment_result["score"] * PORTFOLIO_RANKING_SENTIMENT_WEIGHT +
            technical_result["score"] * PORTFOLIO_RANKING_TECHNICAL_WEIGHT
        )
        
        # Mapear a color
        color, status_text = self._map_to_traffic_light(composite_score, sentiment_result, technical_result)
        
        ranking = {
            "item_id": item.id,
            "symbol": item.symbol,
            "name": item.name,
            "composite_score": round(composite_score * 100, 1),  # Convertir a 0-100 para display
            "sentiment_score": round(sentiment_result["score"] * 100, 1),  # Convertir a 0-100
            "technical_score": round(technical_result["score"] * 100, 1),  # Convertir a 0-100
            "color": color,
            "status_text": status_text,
            "details": {
                "sentiment": {
                    "score": round(sentiment_result["score"] * 100, 1),  # 0-100 para display
                    "explanation": sentiment_result["explanation"],
                    "company_news_count": sentiment_result.get("company_news_count", 0),
                    "sector_news_count": sentiment_result.get("sector_news_count", 0),
                    "headlines": sentiment_result.get("headlines", [])
                },
                "technical": {
                    "score": round(technical_result["score"] * 100, 1),  # 0-100 para display
                    "explanation": technical_result["explanation"],
                    "signals": technical_result.get("signals", {})
                }
            }
        }
        
        # Guardar en caché
        self._cache[cache_key] = ranking
        self._cache_timestamps[cache_key] = datetime.now(timezone.utc)
        
        return ranking
    
    def _calculate_sentiment_score(
        self,
        db: Session,
        item: PortfolioItemResponse
    ) -> Dict:
        """
        Calcula score de sentimiento basado en noticias de empresa y sector.
        Retorna score normalizado 0-100.
        """
        lookback_hours = PORTFOLIO_RANKING_NEWS_LOOKBACK_HOURS
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)
        
        # Buscar noticias de la empresa (por símbolo o nombre)
        company_news = self._fetch_company_news(db, item, cutoff_time)
        
        # Buscar noticias del sector
        sector_news = self._fetch_sector_news(db, item, cutoff_time)
        
        # Calcular scores
        company_sentiment = self._score_news_sentiment(company_news)
        sector_sentiment = self._score_news_sentiment(sector_news)
        
        # Combinar: 70% empresa, 30% sector
        sentiment_score = company_sentiment["score"] * 0.7 + sector_sentiment["score"] * 0.3
        
        # Headlines para tooltip
        headlines = []
        for news in (company_news[:3] + sector_news[:2]):  # Top 5 headlines
            if news.title:
                headlines.append(news.title[:100])
            elif hasattr(news, 'summary'):
                headlines.append(news.summary[:100])
        
        explanation_parts = []
        if company_sentiment["count"] > 0:
            explanation_parts.append(
                f"{company_sentiment['count']} noticias de empresa: {company_sentiment['avg_sentiment']:.1f}"
            )
        if sector_sentiment["count"] > 0:
            explanation_parts.append(
                f"{sector_sentiment['count']} noticias de sector: {sector_sentiment['avg_sentiment']:.1f}"
            )
        
        explanation = "; ".join(explanation_parts) if explanation_parts else "Sin noticias recientes"
        
        return {
            "score": sentiment_score,  # Ya normalizado 0-1
            "explanation": explanation,
            "company_news_count": company_sentiment["count"],
            "sector_news_count": sector_sentiment["count"],
            "headlines": headlines[:5]
        }
    
    def _fetch_company_news(
        self,
        db: Session,
        item: PortfolioItemResponse,
        cutoff_time: datetime
    ) -> List[NewsItemResponse]:
        """Busca noticias relacionadas con la empresa."""
        news_items = []
        
        # Buscar por símbolo
        if item.symbol:
            # Buscar en noticias normales
            news_db = db.query(NewsItem).filter(
                and_(
                    NewsItem.created_at >= cutoff_time,
                    or_(
                        NewsItem.title.ilike(f"%{item.symbol}%"),
                        NewsItem.body.ilike(f"%{item.symbol}%")
                    )
                )
            ).limit(20).all()
            
            news_items.extend([NewsItemResponse.model_validate(n) for n in news_db])
            
            # Buscar en noticias normalizadas
            normalized_db = db.query(NormalizedNews).filter(
                and_(
                    NormalizedNews.timestamp >= cutoff_time,
                    NormalizedNews.tickers.contains(item.symbol)
                )
            ).limit(20).all()
            
            # Convertir a formato compatible
            for n in normalized_db:
                # Crear NewsItemResponse compatible
                news_items.append(NewsItemResponse(
                    id=n.id,
                    title=n.title or n.summary[:100] if n.summary else None,
                    body=n.summary or "",
                    source=n.source,
                    created_at=n.timestamp,
                    score=n.impact_score * 10.0  # Escalar a rango similar
                ))
        
        # Buscar por nombre (si no hay símbolo o para complementar)
        if item.name:
            name_keywords = item.name.split()[:2]  # Primeras 2 palabras del nombre
            for keyword in name_keywords:
                if len(keyword) > 3:  # Ignorar palabras muy cortas
                    news_db = db.query(NewsItem).filter(
                        and_(
                            NewsItem.created_at >= cutoff_time,
                            or_(
                                NewsItem.title.ilike(f"%{keyword}%"),
                                NewsItem.body.ilike(f"%{keyword}%")
                            )
                        )
                    ).limit(10).all()
                    
                    news_items.extend([NewsItemResponse.model_validate(n) for n in news_db])
        
        # Eliminar duplicados por ID
        seen_ids = set()
        unique_news = []
        for news in news_items:
            if news.id not in seen_ids:
                seen_ids.add(news.id)
                unique_news.append(news)
        
        return unique_news[:30]  # Limitar a 30
    
    def _fetch_sector_news(
        self,
        db: Session,
        item: PortfolioItemResponse,
        cutoff_time: datetime
    ) -> List[NewsItemResponse]:
        """Busca noticias del sector relacionado."""
        # Determinar sector del item
        sector_name = None
        
        # Buscar en catálogo de activos
        if item.symbol:
            asset = db.query(AssetCatalog).filter(AssetCatalog.symbol == item.symbol).first()
            if asset and asset.sector:
                sector_name = asset.sector.name
        
        # Si no se encuentra, intentar inferir del nombre/tipo
        if not sector_name:
            # Usar sector extraction service
            fake_news = NewsItemResponse(
                id=0,
                title=item.name,
                body=f"{item.name} {item.asset_type}",
                source="portfolio",
                created_at=datetime.now(timezone.utc)
            )
            extraction = self.sector_extractor.extract_sectors_and_themes(fake_news)
            if extraction["sectors"]:
                sector_name = extraction["sectors"][0]
        
        if not sector_name:
            return []
        
        # Buscar noticias del sector
        news_items = []
        
        # Buscar en noticias normalizadas por categorías
        normalized_db = db.query(NormalizedNews).filter(
            and_(
                NormalizedNews.timestamp >= cutoff_time,
                NormalizedNews.categories.contains(sector_name)
            )
        ).limit(30).all()
        
        for n in normalized_db:
            news_items.append(NewsItemResponse(
                id=n.id,
                title=n.title or n.summary[:100] if n.summary else None,
                body=n.summary or "",
                source=n.source,
                created_at=n.timestamp,
                score=n.impact_score * 10.0
            ))
        
        # Buscar en noticias normales por keywords del sector
        sector = db.query(Sector).filter(Sector.name == sector_name).first()
        if sector and sector.keywords:
            import json
            try:
                keywords = json.loads(sector.keywords) if isinstance(sector.keywords, str) else sector.keywords
                if isinstance(keywords, str):
                    keywords = [k.strip() for k in keywords.split(",")]
                
                for keyword in keywords[:5]:  # Top 5 keywords
                    news_db = db.query(NewsItem).filter(
                        and_(
                            NewsItem.created_at >= cutoff_time,
                            or_(
                                NewsItem.title.ilike(f"%{keyword}%"),
                                NewsItem.body.ilike(f"%{keyword}%")
                            )
                        )
                    ).limit(10).all()
                    
                    news_items.extend([NewsItemResponse.model_validate(n) for n in news_db])
            except Exception as e:
                logger.warning(f"Error parsing sector keywords: {e}")
        
        # Eliminar duplicados
        seen_ids = set()
        unique_news = []
        for news in news_items:
            if news.id not in seen_ids:
                seen_ids.add(news.id)
                unique_news.append(news)
        
        return unique_news[:30]
    
    def _score_news_sentiment(self, news_items: List[NewsItemResponse]) -> Dict:
        """Calcula score de sentimiento promedio de una lista de noticias."""
        if not news_items:
            return {
                "score": 0.5,  # Neutro
                "count": 0,
                "avg_sentiment": 0.0
            }
        
        # Calcular scores usando el servicio de scoring
        portfolio_items = []  # No necesitamos portfolio items para scoring básico
        scores = []
        
        for news in news_items:
            try:
                score_dict = self.news_scoring_service.calculate_news_score(news, portfolio_items)
                score = score_dict["score"]
                sentiment_type = score_dict["components"].get("sentiment_type", "neutral")
                
                # Convertir a -1 (negativo), 0 (neutro), 1 (positivo)
                if sentiment_type == "positive":
                    sentiment_value = 1.0
                elif sentiment_type == "negative":
                    sentiment_value = -1.0
                else:
                    sentiment_value = 0.0
                
                # Ponderar por score de relevancia
                weighted_sentiment = sentiment_value * min(1.0, abs(score) / 10.0)
                scores.append(weighted_sentiment)
            except Exception as e:
                logger.warning(f"Error scoring news {news.id}: {e}")
        
        if not scores:
            return {
                "score": 0.5,
                "count": 0,
                "avg_sentiment": 0.0
            }
        
        avg_sentiment = sum(scores) / len(scores)
        
        # Normalizar a 0-1 (donde 0.5 = neutro)
        normalized_score = (avg_sentiment + 1.0) / 2.0
        
        return {
            "score": normalized_score,
            "count": len(scores),
            "avg_sentiment": avg_sentiment
        }
    
    def _calculate_technical_score(self, item: PortfolioItemResponse) -> Dict:
        """
        Calcula score técnico basado en señales (RSI, MA, volumen).
        Retorna score normalizado 0-100.
        """
        if not item.symbol:
            return {
                "score": 0.5,
                "explanation": "Sin símbolo para análisis técnico",
                "signals": {}
            }
        
        signals = {}
        signal_scores = []
        
        # Obtener features de mercado
        market_features = self.market_features_service.get_market_features(item.symbol)
        
        # 1. Señal de tendencia vs MA (precio vs promedio móvil)
        price_change = market_features.get("intraday_change_pct")
        if price_change is not None:
            # Normalizar: +5% = 1.0, 0% = 0.5, -5% = 0.0
            trend_score = max(0.0, min(1.0, 0.5 + (price_change / 10.0)))
            signals["trend"] = {
                "value": price_change,
                "score": trend_score,
                "description": f"Cambio de precio: {price_change:+.2f}%"
            }
            signal_scores.append(("trend", trend_score, 0.4))  # 40% peso
        
        # 2. Señal de volumen
        volume_ratio = market_features.get("volume_ratio")
        if volume_ratio is not None:
            # Normalizar: 2.0x = 1.0 (muy alto), 1.0x = 0.5 (normal), 0.5x = 0.0 (muy bajo)
            volume_score = max(0.0, min(1.0, 0.5 + (volume_ratio - 1.0) / 2.0))
            signals["volume"] = {
                "value": volume_ratio,
                "score": volume_score,
                "description": f"Volumen: {volume_ratio:.2f}x promedio"
            }
            signal_scores.append(("volume", volume_score, 0.3))  # 30% peso
        
        # 3. Señal de RSI (simulada si no hay datos reales)
        # En producción, esto vendría de la API de precios
        rsi_score = None
        if price_change is not None:
            # Simular RSI basado en momentum
            # Si precio sube mucho, RSI alto (sobrecomprado)
            # Si precio baja mucho, RSI bajo (sobrevendido)
            momentum = price_change
            if momentum > 3.0:
                rsi_estimate = 70.0  # Sobrecomprado
            elif momentum < -3.0:
                rsi_estimate = 30.0  # Sobrevendido
            else:
                rsi_estimate = 50.0 + (momentum * 5.0)  # Lineal entre 30-70
            
            # Normalizar RSI a 0-1 (50 = 0.5, 70+ = 1.0, 30- = 0.0)
            rsi_score = max(0.0, min(1.0, (rsi_estimate - 30.0) / 40.0))
            signals["rsi"] = {
                "value": rsi_estimate,
                "score": rsi_score,
                "description": f"RSI estimado: {rsi_estimate:.1f}"
            }
            signal_scores.append(("rsi", rsi_score, 0.3))  # 30% peso
        
        # Calcular score técnico ponderado
        if signal_scores:
            total_weight = sum(w for _, _, w in signal_scores)
            if total_weight > 0:
                technical_score = sum(score * weight for _, score, weight in signal_scores) / total_weight
            else:
                technical_score = 0.5
        else:
            technical_score = 0.5  # Neutro si no hay señales
        
        # Generar explicación
        explanation_parts = []
        for signal_name, signal_data in signals.items():
            explanation_parts.append(signal_data["description"])
        
        explanation = "; ".join(explanation_parts) if explanation_parts else "Sin señales técnicas disponibles"
        
        return {
            "score": technical_score,  # Ya normalizado 0-1
            "explanation": explanation,
            "signals": signals
        }
    
    def _map_to_traffic_light(
        self,
        composite_score: float,
        sentiment_result: Dict,
        technical_result: Dict
    ) -> Tuple[str, str]:
        """
        Mapea composite_score a color de semáforo y texto de estado.
        
        Returns:
            Tuple[color, status_text]
        """
        if composite_score >= PORTFOLIO_RANKING_GREEN_THRESHOLD:
            color = "green"
            status_text = "Favorable"
        elif composite_score >= PORTFOLIO_RANKING_AMBER_THRESHOLD:
            color = "amber"
            status_text = "Neutro"
        else:
            color = "red"
            status_text = "Precaución"
        
        return color, status_text
    
    def _is_cache_valid(self, cache_key: int) -> bool:
        """Verifica si el caché es válido."""
        if cache_key not in self._cache:
            return False
        
        cache_time = self._cache_timestamps.get(cache_key)
        if not cache_time:
            return False
        
        ttl_minutes = PORTFOLIO_RANKING_CACHE_TTL_MINUTES
        age = (datetime.now(timezone.utc) - cache_time).total_seconds() / 60.0
        
        return age < ttl_minutes
    
    def clear_cache(self, item_id: Optional[int] = None):
        """Limpia el caché para un item específico o todos."""
        if item_id:
            self._cache.pop(item_id, None)
            self._cache_timestamps.pop(item_id, None)
        else:
            self._cache.clear()
            self._cache_timestamps.clear()
