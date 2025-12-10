"""Servicio para clasificación avanzada de noticias (sentimiento, relevancia, urgencia)."""
import logging
from typing import Dict, Tuple, List, Optional
from datetime import datetime, timezone, timedelta
from app.services.news_scoring_service import NewsScoringService
from app.models import NewsItemResponse, PortfolioItemResponse
from app.config import (
    NEWS_RELEVANCE_THRESHOLD_HIGH,
    NEWS_RELEVANCE_THRESHOLD_MEDIUM,
    NEWS_URGENCY_THRESHOLD_HOURS,
    NEWS_CONFIDENCE_HIGH_THRESHOLD,
    NEWS_CONFIDENCE_MEDIUM_THRESHOLD
)

logger = logging.getLogger(__name__)


class NewsClassificationService:
    """Servicio para clasificar noticias por sentimiento, relevancia y urgencia."""
    
    def __init__(self):
        """Inicializa el servicio."""
        self.scoring_service = NewsScoringService()
        self.relevance_high_threshold = NEWS_RELEVANCE_THRESHOLD_HIGH
        self.relevance_medium_threshold = NEWS_RELEVANCE_THRESHOLD_MEDIUM
        self.urgency_threshold_hours = NEWS_URGENCY_THRESHOLD_HOURS
    
    def classify_news(
        self,
        news_item: NewsItemResponse,
        portfolio_items: List[PortfolioItemResponse] = None
    ) -> Dict:
        """
        Clasifica una noticia por sentimiento, relevancia y urgencia.
        
        Returns:
            Dict con: sentiment, relevance, urgency, confidence, explanations
        """
        # Calcular score base
        score_dict = self.scoring_service.calculate_news_score(news_item, portfolio_items)
        score = score_dict["score"]
        components = score_dict["components"]
        
        # Clasificar sentimiento
        sentiment = self._classify_sentiment(components)
        
        # Clasificar relevancia
        relevance, relevance_explanation = self._classify_relevance(score, components, portfolio_items)
        
        # Clasificar urgencia
        urgency, urgency_explanation = self._classify_urgency(news_item.created_at)
        
        # Calcular confianza
        confidence = self._calculate_confidence(score, components)
        
        return {
            "sentiment": sentiment,
            "relevance": relevance,
            "urgency": urgency,
            "confidence": confidence,
            "score": score,
            "explanations": {
                "sentiment": self._get_sentiment_explanation(sentiment, components),
                "relevance": relevance_explanation,
                "urgency": urgency_explanation,
                "confidence": self._get_confidence_explanation(confidence, score)
            }
        }
    
    def _classify_sentiment(self, components: Dict) -> str:
        """Clasifica el sentimiento."""
        sentiment_type = components.get("sentiment_type", "neutral")
        sentiment_score = components.get("sentiment_score", 0.0)
        
        # Si hay sentimiento estandarizado, usarlo
        # Por ahora, usar el análisis básico
        if sentiment_score > 0:
            return "positive"
        elif sentiment_score < 0:
            return "negative"
        else:
            return "neutral"
    
    def _classify_relevance(
        self, 
        score: float, 
        components: Dict,
        portfolio_items: List[PortfolioItemResponse] = None
    ) -> Tuple[str, str]:
        """
        Clasifica la relevancia: high, medium, low.
        
        Returns:
            Tuple[str, str]: (relevance_level, explanation)
        """
        if score >= self.relevance_high_threshold:
            explanation = f"Alta relevancia (score: {score:.2f}). "
            if components.get("ticker_matches", 0) > 0:
                explanation += f"Menciona {components['ticker_matches']} ticker(s) de la cartera. "
            if components.get("category_matches", 0) > 0:
                explanation += f"Relacionada con {components['category_matches']} categoría(s) de activos. "
            return "high", explanation.strip()
        
        elif score >= self.relevance_medium_threshold:
            explanation = f"Relevancia media (score: {score:.2f}). "
            if components.get("ticker_matches", 0) > 0:
                explanation += "Menciona activos de la cartera. "
            elif components.get("category_matches", 0) > 0:
                explanation += "Relacionada con tipos de activos en cartera. "
            else:
                explanation += "Sentimiento relevante para el contexto general. "
            return "medium", explanation.strip()
        
        else:
            explanation = f"Baja relevancia (score: {score:.2f}). "
            if components.get("is_obsolete", False):
                explanation += "Noticia obsoleta. "
            explanation += "No hay relación directa con la cartera actual."
            return "low", explanation.strip()
    
    def _classify_urgency(self, created_at: str) -> Tuple[str, str]:
        """
        Clasifica la urgencia: high, medium, low.
        
        Returns:
            Tuple[str, str]: (urgency_level, explanation)
        """
        try:
            if 'T' in created_at:
                news_date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            else:
                news_date = datetime.fromisoformat(created_at)
            
            if news_date.tzinfo is None:
                news_date = news_date.replace(tzinfo=timezone.utc)
            
            now = datetime.now(timezone.utc)
            age_hours = (now - news_date).total_seconds() / 3600
            
            if age_hours <= self.urgency_threshold_hours:
                explanation = f"Urgente: noticia muy reciente ({age_hours:.1f} horas). Requiere atención inmediata."
                return "high", explanation
            
            elif age_hours <= self.urgency_threshold_hours * 3:
                explanation = f"Urgencia media: noticia reciente ({age_hours:.1f} horas). Revisar pronto."
                return "medium", explanation
            
            else:
                explanation = f"Baja urgencia: noticia antigua ({age_hours:.1f} horas). Información histórica."
                return "low", explanation
                
        except Exception as e:
            logger.warning(f"Error calculando urgencia: {e}")
            return "medium", "No se pudo determinar urgencia exacta."
    
    def _calculate_confidence(self, score: float, components: Dict) -> float:
        """
        Calcula nivel de confianza (0.0 a 1.0) basado en score y componentes.
        """
        # Base de confianza basada en score
        if score >= self.relevance_high_threshold:
            base_confidence = 0.9
        elif score >= self.relevance_medium_threshold:
            base_confidence = 0.7
        else:
            base_confidence = 0.5
        
        # Ajustar por componentes
        if components.get("ticker_matches", 0) > 0:
            base_confidence += 0.1  # Más confianza si menciona tickers específicos
        
        if components.get("is_obsolete", False):
            base_confidence -= 0.3  # Menos confianza si es obsoleta
        
        # Ajustar por decay temporal
        temporal_decay = components.get("temporal_decay", 1.0)
        if temporal_decay < 0.5:
            base_confidence -= 0.2
        
        # Limitar entre 0.0 y 1.0
        return max(0.0, min(1.0, base_confidence))
    
    def _get_sentiment_explanation(self, sentiment: str, components: Dict) -> str:
        """Genera explicación del sentimiento."""
        sentiment_type = components.get("sentiment_type", "neutral")
        sentiment_score = components.get("sentiment_score", 0.0)
        
        if sentiment == "positive":
            return f"Sentimiento positivo (score: {sentiment_score:.2f}). Indica perspectivas favorables."
        elif sentiment == "negative":
            return f"Sentimiento negativo (score: {sentiment_score:.2f}). Indica riesgos o perspectivas desfavorables."
        else:
            return "Sentimiento neutro. No hay sesgo claro hacia positivo o negativo."
    
    def _get_confidence_explanation(self, confidence: float, score: float) -> str:
        """Genera explicación del nivel de confianza."""
        if confidence >= NEWS_CONFIDENCE_HIGH_THRESHOLD:
            return f"Alta confianza ({confidence:.0%}). Score alto ({score:.2f}) y componentes sólidos."
        elif confidence >= NEWS_CONFIDENCE_MEDIUM_THRESHOLD:
            return f"Confianza media ({confidence:.0%}). Score moderado ({score:.2f})."
        else:
            return f"Baja confianza ({confidence:.0%}). Score bajo ({score:.2f}) o información limitada."

