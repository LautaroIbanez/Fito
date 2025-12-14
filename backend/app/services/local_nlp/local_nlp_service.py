"""Servicio unificado de NLP local que combina todas las funcionalidades."""
import logging
from typing import Dict, List, Optional
from app.services.local_nlp.nlp_processor import get_nlp_processor
from app.services.local_nlp.sentiment_analyzer import SentimentAnalyzer
from app.services.local_nlp.sector_classifier import SectorClassifier
from app.services.local_nlp.entity_extractor import EntityExtractor

logger = logging.getLogger(__name__)


class LocalNLPService:
    """Servicio unificado de NLP local."""
    
    def __init__(self):
        """Inicializa todos los componentes de NLP local."""
        logger.info("Inicializando servicio de NLP local...")
        self.nlp_processor = get_nlp_processor()
        self.sentiment_analyzer = SentimentAnalyzer()
        self.sector_classifier = SectorClassifier()
        self.entity_extractor = EntityExtractor()
        logger.info("Servicio de NLP local inicializado correctamente")
    
    def analyze_news(self, text: str, title: Optional[str] = None, language: Optional[str] = None) -> Dict:
        """
        Analiza una noticia completa usando todos los componentes de NLP local.
        
        Args:
            text: Cuerpo de la noticia
            title: Título de la noticia (opcional)
            language: Idioma del texto
        
        Returns:
            Diccionario con análisis completo:
            {
                "sentiment": {"positive": 0.0, "negative": 0.0, "neutral": 0.0},
                "sentiment_label": "positive|negative|neutral",
                "sectors": [{"sector": "...", "score": 0.0}, ...],
                "primary_sector": "...",
                "entities": {
                    "ORG": [...],
                    "PERSON": [...],
                    "GPE": [...],
                    "MONEY": [...],
                    "DATE": [...]
                },
                "tickers": [...],
                "keywords": [...],
                "language": "es|en"
            }
        """
        # Combinar título y texto
        full_text = f"{title} {text}" if title else text
        
        if not full_text:
            return {
                "sentiment": {"positive": 0.0, "negative": 0.0, "neutral": 1.0},
                "sentiment_label": "neutral",
                "sectors": [],
                "primary_sector": None,
                "entities": {"ORG": [], "PERSON": [], "GPE": [], "MONEY": [], "DATE": []},
                "tickers": [],
                "keywords": [],
                "language": "es"
            }
        
        # Detectar idioma si no se proporciona
        if language is None:
            language = self.nlp_processor.detect_language(full_text)
        
        # Análisis de sentimiento
        sentiment_scores = self.sentiment_analyzer.analyze_sentiment(full_text, language)
        sentiment_label = self.sentiment_analyzer.get_sentiment_label(full_text, language)
        
        # Clasificación de sectores
        sectors = self.sector_classifier.classify_sectors(full_text, language)
        primary_sector = self.sector_classifier.get_primary_sector(full_text, language)
        
        # Extracción de entidades
        entities = self.entity_extractor.extract_entities(full_text, language)
        tickers = self.entity_extractor.extract_tickers(full_text)
        
        # Extracción de keywords
        keywords = self.nlp_processor.extract_keywords(full_text, language)
        
        return {
            "sentiment": sentiment_scores,
            "sentiment_label": sentiment_label,
            "sectors": sectors,
            "primary_sector": primary_sector,
            "entities": entities,
            "tickers": tickers,
            "keywords": keywords,
            "language": language
        }
    
    def is_ready(self) -> bool:
        """
        Verifica si el servicio está listo para usar.
        
        Returns:
            True si todos los componentes están inicializados
        """
        try:
            return (
                self.nlp_processor is not None
                and self.sentiment_analyzer is not None
                and self.sector_classifier is not None
                and self.entity_extractor is not None
            )
        except Exception as e:
            logger.error(f"Error verificando estado del servicio NLP: {e}")
            return False


# Instancia global del servicio
_local_nlp_service_instance: Optional[LocalNLPService] = None


def get_local_nlp_service() -> LocalNLPService:
    """Obtiene la instancia global del servicio de NLP local."""
    global _local_nlp_service_instance
    if _local_nlp_service_instance is None:
        _local_nlp_service_instance = LocalNLPService()
    return _local_nlp_service_instance
