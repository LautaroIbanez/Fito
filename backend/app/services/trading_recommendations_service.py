"""Servicio principal para generar recomendaciones de trading contextualizadas."""
import logging
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from datetime import datetime, timedelta, timezone

from app.database import NewsItem, PortfolioItem, TradingRecommendation
from app.models import NewsItemResponse, PortfolioItemResponse
from app.services.news_scoring_service import NewsScoringService
from app.services.news_classification_service import NewsClassificationService
from app.services.market_features_service import MarketFeaturesService
from app.services.trading_rules_engine import TradingRulesEngine
from app.services.recommendation_explanation_service import RecommendationExplanationService
from app.services.recommendation_audit_service import RecommendationAuditService
from app.config import NEWS_URGENCY_THRESHOLD_HOURS
import json

logger = logging.getLogger(__name__)


class TradingRecommendationsService:
    """Servicio para generar recomendaciones de trading contextualizadas por activo."""
    
    def __init__(self):
        """Inicializa el servicio."""
        self.scoring_service = NewsScoringService()
        self.classification_service = NewsClassificationService()
        self.market_features_service = MarketFeaturesService()
        self.rules_engine = TradingRulesEngine()
        self.explanation_service = RecommendationExplanationService()
        self.audit_service = RecommendationAuditService()
    
    def get_recommendations_for_asset(
        self,
        db: Session,
        portfolio_item: PortfolioItem,
        max_news_items: int = 5
    ) -> Dict:
        """
        Genera recomendaciones de trading para un activo específico.
        
        Returns:
            Dict con: asset_info, key_news, impact_summary, recommendations, market_features
        """
        # Obtener símbolo del activo
        symbol = portfolio_item.symbol or portfolio_item.name
        
        # Obtener noticias relevantes para este activo
        portfolio_items = [PortfolioItemResponse.model_validate(portfolio_item)]
        key_news = self._get_key_news_for_asset(db, portfolio_item, portfolio_items, max_news_items)
        
        # Clasificar noticias
        classified_news = []
        overall_sentiment = "neutral"
        overall_relevance = "low"
        overall_urgency = "low"
        overall_confidence = 0.0
        
        for news_item in key_news:
            classification = self.classification_service.classify_news(news_item, portfolio_items)
            classified_news.append({
                "news": news_item,
                "classification": classification
            })
            
            # Acumular métricas generales
            if classification["sentiment"] != "neutral":
                overall_sentiment = classification["sentiment"]
            if classification["relevance"] == "high":
                overall_relevance = "high"
            elif classification["relevance"] == "medium" and overall_relevance != "high":
                overall_relevance = "medium"
            if classification["urgency"] == "high":
                overall_urgency = "high"
            elif classification["urgency"] == "medium" and overall_urgency != "high":
                overall_urgency = "medium"
            overall_confidence = max(overall_confidence, classification["confidence"])
        
        # Obtener features de mercado
        market_features = self.market_features_service.get_market_features(symbol)
        
        # Generar recomendaciones usando el motor de reglas
        recommendations_data = self.rules_engine.generate_recommendations(
            market_features=market_features,
            sentiment=overall_sentiment,
            relevance=overall_relevance,
            urgency=overall_urgency,
            confidence=overall_confidence
        )
        
        # Preparar inputs para trazabilidad
        inputs = {
            "sentiment": overall_sentiment,
            "relevance": overall_relevance,
            "urgency": overall_urgency,
            "confidence": overall_confidence,
            "intraday_change_pct": market_features.get("intraday_change_pct"),
            "volume_ratio": market_features.get("volume_ratio"),
            "current_price": market_features.get("current_price"),
            "atr": market_features.get("atr")
        }
        
        # Obtener noticia principal (la más relevante)
        primary_news = classified_news[0]["news"] if classified_news else None
        
        # Generar explicaciones y guardar recomendaciones en BD
        saved_recommendations = []
        for rec_data in recommendations_data:
            # Generar explicación profesional
            explanation = self.explanation_service.generate_explanation(
                action=rec_data["action"],
                condition=rec_data["condition"],
                threshold_data=rec_data.get("threshold", {}),
                inputs=inputs,
                asset_name=portfolio_item.name,
                sector=None  # Podríamos obtenerlo del portfolio_item si lo agregamos
            )
            
            # Guardar en base de datos
            db_recommendation = TradingRecommendation(
                portfolio_item_id=portfolio_item.id,
                source_news_id=primary_news.id if primary_news else None,
                source_news_title=primary_news.title if primary_news else None,
                generated_at=datetime.now(timezone.utc),
                action=rec_data["action"],
                condition=rec_data["condition"],
                reason=rec_data["reason"],
                explanation=explanation,
                inputs=json.dumps(inputs, ensure_ascii=False),
                threshold_data=json.dumps(rec_data.get("threshold", {}), ensure_ascii=False),
                confidence=rec_data["confidence"],
                priority=rec_data["priority"],
                is_active=True
            )
            
            db.add(db_recommendation)
            db.flush()
            
            # Log de auditoría detallado
            self.audit_service.log_recommendation_generation(
                recommendation_id=db_recommendation.id,
                portfolio_item_id=portfolio_item.id,
                asset_name=portfolio_item.name,
                asset_symbol=portfolio_item.symbol,
                action=rec_data["action"],
                condition=rec_data["condition"],
                confidence=rec_data["confidence"],
                source_news_id=primary_news.id if primary_news else None,
                inputs=inputs,
                threshold_data=rec_data.get("threshold", {})
            )
            
            # Agregar explicación y datos de trazabilidad a la recomendación
            rec_data["explanation"] = explanation
            rec_data["source_news_id"] = primary_news.id if primary_news else None
            rec_data["source_news_title"] = primary_news.title if primary_news else None
            rec_data["generated_at"] = db_recommendation.generated_at.isoformat()
            rec_data["inputs"] = inputs
            rec_data["recommendation_id"] = db_recommendation.id
            
            saved_recommendations.append(rec_data)
        
        db.commit()
        
        # Generar resumen de impacto
        impact_summary = self._generate_impact_summary(
            classified_news,
            overall_sentiment,
            overall_relevance,
            overall_urgency
        )
        
        return {
            "asset_info": {
                "id": portfolio_item.id,
                "name": portfolio_item.name,
                "symbol": portfolio_item.symbol,
                "asset_type": portfolio_item.asset_type
            },
            "key_news": [
                {
                    "id": item["news"].id,
                    "title": item["news"].title,
                    "created_at": item["news"].created_at,
                    "classification": item["classification"]
                }
                for item in classified_news
            ],
            "impact_summary": impact_summary,
            "recommendations": saved_recommendations,
            "market_features": market_features,
            "overall_metrics": {
                "sentiment": overall_sentiment,
                "relevance": overall_relevance,
                "urgency": overall_urgency,
                "confidence": overall_confidence
            },
            "generated_at": datetime.now(timezone.utc).isoformat()
        }
    
    def _get_key_news_for_asset(
        self,
        db: Session,
        portfolio_item: PortfolioItem,
        portfolio_items: List[PortfolioItemResponse],
        max_items: int
    ) -> List[NewsItemResponse]:
        """Obtiene noticias clave para un activo."""
        # Obtener todas las noticias recientes
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=NEWS_URGENCY_THRESHOLD_HOURS * 7)
        recent_news = db.query(NewsItem).filter(
            NewsItem.created_at >= cutoff_time
        ).order_by(NewsItem.created_at.desc()).all()
        
        # Convertir a modelos de respuesta
        news_responses = [NewsItemResponse.model_validate(item) for item in recent_news]
        
        # Calcular scores y ordenar
        scored_news = self.scoring_service.score_and_sort_news(news_responses, portfolio_items)
        
        # Filtrar noticias relevantes para este activo específico
        symbol = portfolio_item.symbol or portfolio_item.name
        relevant_news = []
        
        for news_item, score_dict in scored_news:
            # Verificar si menciona el símbolo o es relevante
            components = score_dict["components"]
            if (components.get("ticker_matches", 0) > 0 or 
                components.get("category_matches", 0) > 0 or
                score_dict["score"] >= 2.0):
                relevant_news.append(news_item)
                if len(relevant_news) >= max_items:
                    break
        
        return relevant_news
    
    def _generate_impact_summary(
        self,
        classified_news: List[Dict],
        sentiment: str,
        relevance: str,
        urgency: str
    ) -> str:
        """Genera un resumen de impacto basado en las noticias clasificadas."""
        if not classified_news:
            return "No hay noticias recientes relevantes para este activo."
        
        news_count = len(classified_news)
        sentiment_text = {
            "positive": "positivo",
            "negative": "negativo",
            "neutral": "neutro"
        }.get(sentiment, "neutro")
        
        relevance_text = {
            "high": "alta",
            "medium": "media",
            "low": "baja"
        }.get(relevance, "baja")
        
        urgency_text = {
            "high": "alta",
            "medium": "media",
            "low": "baja"
        }.get(urgency, "baja")
        
        summary = f"Se analizaron {news_count} noticia(s) reciente(s). "
        summary += f"Sentimiento general: {sentiment_text}. "
        summary += f"Relevancia: {relevance_text}. "
        summary += f"Urgencia: {urgency_text}. "
        
        # Agregar detalles específicos
        if sentiment == "negative":
            summary += "Se recomienda monitorear riesgos y considerar ajustes defensivos. "
        elif sentiment == "positive":
            summary += "Oportunidades potenciales identificadas. "
        
        if urgency == "high":
            summary += "Requiere atención inmediata."
        
        return summary
    
    def get_all_recommendations(
        self,
        db: Session
    ) -> List[Dict]:
        """Obtiene recomendaciones para todos los activos en cartera."""
        portfolio_items = db.query(PortfolioItem).all()
        
        recommendations = []
        for item in portfolio_items:
            try:
                rec = self.get_recommendations_for_asset(db, item)
                recommendations.append(rec)
            except Exception as e:
                logger.error(f"Error generando recomendaciones para activo {item.id}: {e}", exc_info=True)
                continue
        
        return recommendations

