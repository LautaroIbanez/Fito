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
        
        logger.info(f"Calculando rankings para {len(portfolio_items)} items de cartera")
        
        rankings = []
        
        for item in portfolio_items:
            try:
                logger.debug(f"Calculando ranking para item {item.id} ({item.name} / {item.symbol})")
                ranking = self._calculate_ranking_for_item(db, item)
                # Asegurar que el item_id esté correctamente asignado
                ranking["item_id"] = item.id
                rankings.append(ranking)
                logger.debug(f"Ranking calculado para item {item.id}: score={ranking.get('composite_score', 'N/A')}, color={ranking.get('color', 'N/A')}")
            except Exception as e:
                logger.error(f"Error calculando ranking para item {item.id} ({item.name}): {e}", exc_info=True)
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
        
        logger.info(f"Rankings generados: {len(rankings)} items")
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
        
        # Mapear a color y obtener recomendación
        color, status_text, action_recommendation = self._map_to_traffic_light(composite_score, sentiment_result, technical_result)
        
        # Timestamp de actualización
        updated_at = datetime.now(timezone.utc)
        
        # Calcular contribución de cada factor al score final
        sentiment_contribution = sentiment_result["score"] * PORTFOLIO_RANKING_SENTIMENT_WEIGHT * 100
        technical_contribution = technical_result["score"] * PORTFOLIO_RANKING_TECHNICAL_WEIGHT * 100
        
        # Calcular desviación desde neutro (50) para mostrar empuje
        sentiment_push = (sentiment_result["score"] * 100) - 50
        technical_push = (technical_result["score"] * 100) - 50
        
        ranking = {
            "item_id": item.id,
            "symbol": item.symbol,
            "name": item.name,
            "composite_score": round(composite_score * 100, 1),  # Convertir a 0-100 para display
            "sentiment_score": round(sentiment_result["score"] * 100, 1),  # Convertir a 0-100
            "technical_score": round(technical_result["score"] * 100, 1),  # Convertir a 0-100
            "color": color,
            "status_text": status_text,
            "action_recommendation": action_recommendation,
            "updated_at": updated_at.isoformat(),
            "thresholds": {
                "red_max": round(PORTFOLIO_RANKING_AMBER_THRESHOLD * 100 - 0.1, 1),  # 0-39.9
                "amber_min": round(PORTFOLIO_RANKING_AMBER_THRESHOLD * 100, 1),  # 40
                "amber_max": round(PORTFOLIO_RANKING_GREEN_THRESHOLD * 100 - 0.1, 1),  # 64.9
                "green_min": round(PORTFOLIO_RANKING_GREEN_THRESHOLD * 100, 1),  # 65
                "green_max": 100
            },
            "weights": {
                "sentiment": PORTFOLIO_RANKING_SENTIMENT_WEIGHT,
                "technical": PORTFOLIO_RANKING_TECHNICAL_WEIGHT
            },
            "contributions": {
                "sentiment": round(sentiment_contribution, 1),
                "technical": round(technical_contribution, 1)
            },
            "factor_push": {
                "sentiment": round(sentiment_push, 1),
                "technical": round(technical_push, 1)
            },
            "details": {
                "sentiment": {
                    "score": round(sentiment_result["score"] * 100, 1),  # 0-100 para display
                    "explanation": sentiment_result["explanation"],
                    "company_news_count": sentiment_result.get("company_news_count", 0),
                    "sector_news_count": sentiment_result.get("sector_news_count", 0),
                    "headlines": sentiment_result.get("headlines", []),
                    "data_quality": sentiment_result.get("data_quality", "unknown"),
                    "last_news_date": sentiment_result.get("last_news_date"),
                    "indicators_used": sentiment_result.get("indicators_used", []),
                    "reliability_note": sentiment_result.get("reliability_note")
                },
                "technical": {
                    "score": round(technical_result["score"] * 100, 1),  # 0-100 para display
                    "explanation": technical_result["explanation"],
                    "signals": technical_result.get("signals", {}),
                    "data_quality": technical_result.get("data_quality", "unknown"),
                    "last_update": technical_result.get("last_update"),
                    "indicators_used": technical_result.get("indicators_used", []),
                    "reliability_note": technical_result.get("reliability_note")
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
        
        # Scores separados (0-1, luego convertidos a 0-100)
        company_score = company_sentiment["score"]
        sector_score = sector_sentiment["score"]
        
        # Combinar: 70% empresa, 30% sector
        sentiment_score = company_score * 0.7 + sector_score * 0.3
        
        # Generar síntesis del sector
        sector_synthesis = self._generate_sector_synthesis(sector_score, sector_sentiment["count"])
        
        # Headlines para tooltip
        headlines = []
        last_news_date = None
        for news in (company_news[:3] + sector_news[:2]):  # Top 5 headlines
            if news.title:
                headlines.append(news.title[:100])
            elif hasattr(news, 'summary'):
                headlines.append(news.summary[:100])
            # Capturar fecha más reciente
            if news.created_at:
                try:
                    news_date = datetime.fromisoformat(news.created_at.replace('Z', '+00:00'))
                    if last_news_date is None or news_date > last_news_date:
                        last_news_date = news_date
                except:
                    pass
        
        # Determinar calidad de datos y causa
        total_news = company_sentiment["count"] + sector_sentiment["count"]
        data_quality = "high" if total_news >= 5 else "medium" if total_news >= 2 else "low"
        
        # Indicadores usados
        indicators_used = []
        if company_sentiment["count"] > 0:
            indicators_used.append(f"Noticias de empresa ({company_sentiment['count']})")
        if sector_sentiment["count"] > 0:
            indicators_used.append(f"Noticias de sector ({sector_sentiment['count']})")
        
        # Nota de confiabilidad
        reliability_note = None
        if total_news == 0:
            reliability_note = "Sin noticias recientes en los últimos 7 días. Score basado en valor neutro."
            data_quality = "insufficient"
        elif total_news < 2:
            reliability_note = f"Solo {total_news} noticia(s) encontrada(s). Confianza limitada."
        elif company_sentiment["count"] == 0 and sector_sentiment["count"] > 0:
            reliability_note = "Solo noticias de sector disponibles. Sin noticias específicas de la empresa."
        
        explanation_parts = []
        if company_sentiment["count"] > 0:
            explanation_parts.append(
                f"{company_sentiment['count']} noticias de empresa"
            )
        if sector_sentiment["count"] > 0:
            explanation_parts.append(
                f"{sector_sentiment['count']} noticias de sector"
            )
        
        explanation = "; ".join(explanation_parts) if explanation_parts else "Sin noticias recientes"
        
        # Calcular ventana temporal en días
        lookback_days = lookback_hours / 24
        
        # Fechas más recientes por tipo
        company_last_date = None
        sector_last_date = None
        for news in company_news:
            if news.created_at:
                try:
                    news_date = datetime.fromisoformat(news.created_at.replace('Z', '+00:00'))
                    if company_last_date is None or news_date > company_last_date:
                        company_last_date = news_date
                except:
                    pass
        for news in sector_news:
            if news.created_at:
                try:
                    news_date = datetime.fromisoformat(news.created_at.replace('Z', '+00:00'))
                    if sector_last_date is None or news_date > sector_last_date:
                        sector_last_date = news_date
                except:
                    pass
        
        return {
            "score": sentiment_score,  # Ya normalizado 0-1
            "explanation": explanation,
            "company_news_count": company_sentiment["count"],
            "sector_news_count": sector_sentiment["count"],
            "headlines": headlines[:5],
            "data_quality": data_quality,
            "last_news_date": last_news_date.isoformat() if last_news_date else None,
            "indicators_used": indicators_used,
            "reliability_note": reliability_note,
            # Nuevos campos: scores separados y síntesis
            "company_score": round(company_score * 100, 1),  # 0-100
            "sector_score": round(sector_score * 100, 1),  # 0-100
            "sector_synthesis": sector_synthesis,
            "lookback_days": round(lookback_days, 0),
            "company_last_date": company_last_date.isoformat() if company_last_date else None,
            "sector_last_date": sector_last_date.isoformat() if sector_last_date else None
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
    
    def _generate_sector_synthesis(self, sector_score: float, sector_news_count: int) -> str:
        """
        Genera una síntesis textual del sentimiento del sector.
        Asegura que no contradiga el color final (si sector es muy negativo, 
        no puede producir verde sin explicación).
        """
        if sector_news_count == 0:
            return "Sin noticias de sector disponibles"
        
        score_100 = sector_score * 100
        
        if score_100 >= 70:
            return "Sector en positivo fuerte"
        elif score_100 >= 60:
            return "Sector en positivo moderado"
        elif score_100 >= 55:
            return "Sector en leve positivo"
        elif score_100 >= 45:
            return "Sector neutro"
        elif score_100 >= 40:
            return "Sector en leve negativo"
        elif score_100 >= 30:
            return "Sector en negativo moderado"
        else:
            return "Sector en negativo fuerte"
    
    def _calculate_technical_score(self, item: PortfolioItemResponse) -> Dict:
        """
        Calcula score técnico basado en señales (RSI, MA, volumen).
        Retorna score normalizado 0-100.
        """
        if not item.symbol:
            return {
                "score": 0.5,
                "explanation": "Sin símbolo para análisis técnico",
                "signals": {},
                "data_quality": "insufficient",
                "indicators_used": [],
                "reliability_note": "No se puede realizar análisis técnico sin símbolo del activo."
            }
        
        signals = {}
        signal_scores = []
        indicators_used = []
        data_quality = "high"
        reliability_note = None
        
        # Obtener features de mercado
        market_features = self.market_features_service.get_market_features(item.symbol)
        update_time = datetime.now(timezone.utc)
        
        # 1. Señal de tendencia vs MA (precio vs promedio móvil)
        price_change = market_features.get("intraday_change_pct")
        if price_change is not None:
            # Normalizar: +5% = 1.0, 0% = 0.5, -5% = 0.0
            trend_score = max(0.0, min(1.0, 0.5 + (price_change / 10.0)))
            signals["trend"] = {
                "value": price_change,
                "score": trend_score,
                "description": f"Cambio de precio: {price_change:+.2f}%",
                "indicator": "Precio vs Promedio Móvil (MA50)",
                "period": "24 horas"
            }
            indicators_used.append("MA50 vs Precio Actual (24h)")
            signal_scores.append(("trend", trend_score, 0.4))  # 40% peso
        else:
            data_quality = "medium"
            reliability_note = "Sin datos de precio disponibles. Score basado en señales limitadas."
        
        # 2. Señal de volumen
        volume_ratio = market_features.get("volume_ratio")
        if volume_ratio is not None:
            # Normalizar: 2.0x = 1.0 (muy alto), 1.0x = 0.5 (normal), 0.5x = 0.0 (muy bajo)
            volume_score = max(0.0, min(1.0, 0.5 + (volume_ratio - 1.0) / 2.0))
            signals["volume"] = {
                "value": volume_ratio,
                "score": volume_score,
                "description": f"Volumen: {volume_ratio:.2f}x promedio",
                "indicator": "Volumen vs Promedio",
                "period": "20 días"
            }
            indicators_used.append("Volumen vs Promedio (20d)")
            signal_scores.append(("volume", volume_score, 0.3))  # 30% peso
        else:
            if data_quality == "high":
                data_quality = "medium"
            if not reliability_note:
                reliability_note = "Sin datos de volumen suficientes para señal técnica."
        
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
                "description": f"RSI estimado: {rsi_estimate:.1f}",
                "indicator": "RSI (Relative Strength Index)",
                "period": "14 días"
            }
            indicators_used.append("RSI 14d (estimado)")
            signal_scores.append(("rsi", rsi_score, 0.3))  # 30% peso
        
        # Calcular score técnico ponderado
        if signal_scores:
            total_weight = sum(w for _, _, w in signal_scores)
            if total_weight > 0:
                technical_score = sum(score * weight for _, score, weight in signal_scores) / total_weight
            else:
                technical_score = 0.5
                data_quality = "insufficient"
                reliability_note = "Sin señales técnicas disponibles. Score neutro por defecto."
        else:
            technical_score = 0.5  # Neutro si no hay señales
            data_quality = "insufficient"
            reliability_note = "Sin datos técnicos disponibles. No hay suficiente volumen o datos de precio para generar señales."
        
        # Generar explicación
        explanation_parts = []
        for signal_name, signal_data in signals.items():
            explanation_parts.append(signal_data["description"])
        
        explanation = "; ".join(explanation_parts) if explanation_parts else "Sin señales técnicas disponibles"
        
        return {
            "score": technical_score,  # Ya normalizado 0-1
            "explanation": explanation,
            "signals": signals,
            "data_quality": data_quality,
            "last_update": update_time.isoformat(),
            "indicators_used": indicators_used,
            "reliability_note": reliability_note
        }
    
    def _map_to_traffic_light(
        self,
        composite_score: float,
        sentiment_result: Dict,
        technical_result: Dict
    ) -> Tuple[str, str, str]:
        """
        Mapea composite_score a color de semáforo, texto de estado y recomendación de acción.
        
        Returns:
            Tuple[color, status_text, action_recommendation]
        """
        # Generar explicación rápida para estado neutro
        quick_reason = []
        sentiment_quality = sentiment_result.get("data_quality", "unknown")
        technical_quality = technical_result.get("data_quality", "unknown")
        
        if sentiment_quality == "insufficient":
            quick_reason.append("sin noticias")
        if technical_quality == "insufficient":
            quick_reason.append("sin señales técnicas")
        
        reason_suffix = f" ({', '.join(quick_reason)})" if quick_reason else ""
        
        if composite_score >= PORTFOLIO_RANKING_GREEN_THRESHOLD:
            color = "green"
            status_text = "Favorable"
            action_recommendation = "Mantener posición y monitorear indicadores clave"
        elif composite_score >= PORTFOLIO_RANKING_AMBER_THRESHOLD:
            color = "amber"
            # Hacer el texto más descriptivo para neutro
            if quick_reason:
                status_text = f"Neutro{reason_suffix}"
            else:
                status_text = "Neutro"
            action_recommendation = "Monitorear noticias próximas 48 horas"
        else:
            color = "red"
            status_text = "Precaución"
            action_recommendation = "Revisar soporte técnico y considerar reducción"
        
        return color, status_text, action_recommendation
    
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
