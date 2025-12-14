"""Servicio de análisis de sentimiento sin LLM, basado en diccionarios."""
import logging
from typing import Dict, Optional, Any
from typing import Optional as Opt
from app.services.local_nlp import get_local_nlp_service

logger = logging.getLogger(__name__)


class SentimentService:
    """Servicio para análisis de sentimiento basado en reglas y diccionarios."""
    
    def __init__(self):
        """Inicializa el servicio."""
        self.nlp_service = get_local_nlp_service()
        logger.info("SentimentService inicializado (sin LLM)")
    
    def analyze_sentiment(
        self, 
        text: str, 
        title: Optional[str] = None,
        language: Optional[str] = None
    ) -> Dict[str, any]:
        """
        Analiza el sentimiento de un texto usando diccionarios locales.
        
        Args:
            text: Cuerpo del texto
            title: Título (opcional, se combina con el texto)
            language: Idioma del texto ('es' o 'en'). Si es None, se detecta automáticamente
        
        Returns:
            Diccionario con:
            {
                "sentiment": "positive" | "negative" | "neutral",
                "scores": {
                    "positive": 0.0-1.0,
                    "negative": 0.0-1.0,
                    "neutral": 0.0-1.0
                },
                "confidence": 0.0-1.0,  # Confianza basada en diferencia entre scores
                "method": "dictionary_based",
                "language": "es" | "en"
            }
        """
        # Combinar título y texto
        full_text = f"{title} {text}" if title else text
        
        if not full_text:
            logger.warning("Texto vacío para análisis de sentimiento, retornando neutral")
            return {
                "sentiment": "neutral",
                "scores": {"positive": 0.0, "negative": 0.0, "neutral": 1.0},
                "confidence": 0.0,
                "method": "dictionary_based",
                "language": language or "es"
            }
        
        # Analizar usando NLP local
        analysis = self.nlp_service.analyze_news(full_text, language=language)
        
        scores = analysis["sentiment"]
        sentiment_label = analysis["sentiment_label"]
        detected_language = analysis["language"]
        
        # Calcular confianza basada en la diferencia entre el score dominante y el segundo
        # Orden determinista: primero por score descendente, luego por nombre de sentimiento ascendente
        sorted_scores = sorted(scores.items(), key=lambda x: (-x[1], x[0]))
        if len(sorted_scores) >= 2:
            dominant_score = sorted_scores[0][1]
            second_score = sorted_scores[1][1]
            confidence = max(0.0, dominant_score - second_score)  # Asegurar no negativo
        else:
            confidence = 1.0
        
        # Log trazable y determinista (motor local)
        logger.debug(
            f"[MOTOR LOCAL] [SENTIMENT] Texto analizado (longitud={len(full_text)} chars, idioma={detected_language}) | "
            f"Resultado: {sentiment_label} | "
            f"Scores: positive={scores['positive']:.6f}, negative={scores['negative']:.6f}, neutral={scores['neutral']:.6f} | "
            f"Confianza: {confidence:.6f} | "
            f"Método: dictionary_based (sin LLM)"
        )
        
        return {
            "sentiment": sentiment_label,
            "scores": scores,
            "confidence": round(confidence, 3),
            "method": "dictionary_based",
            "language": detected_language
        }
    
    def get_sentiment_label(
        self, 
        text: str, 
        title: Optional[str] = None,
        language: Optional[str] = None
    ) -> str:
        """
        Obtiene solo la etiqueta de sentimiento.
        
        Args:
            text: Cuerpo del texto
            title: Título (opcional)
            language: Idioma del texto
        
        Returns:
            "positive", "negative", o "neutral"
        """
        result = self.analyze_sentiment(text, title, language)
        return result["sentiment"]


# Instancia global del servicio
_sentiment_service_instance: Optional[SentimentService] = None


def get_sentiment_service() -> SentimentService:
    """Obtiene la instancia global del servicio de sentimiento."""
    global _sentiment_service_instance
    if _sentiment_service_instance is None:
        _sentiment_service_instance = SentimentService()
    return _sentiment_service_instance
