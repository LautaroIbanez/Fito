"""Analizador de sentimiento basado en diccionarios."""
import logging
import json
import os
from typing import Dict, Optional
from pathlib import Path
from app.services.local_nlp.nlp_processor import get_nlp_processor

logger = logging.getLogger(__name__)


class SentimentAnalyzer:
    """Analizador de sentimiento basado en diccionarios de palabras clave."""
    
    def __init__(self):
        """Inicializa el analizador cargando los diccionarios."""
        self.nlp_processor = get_nlp_processor()
        self.sentiment_dict: Dict = {}
        self._load_sentiment_dictionary()
    
    def _load_sentiment_dictionary(self):
        """Carga el diccionario de sentimiento desde archivo JSON."""
        try:
            # Obtener ruta del archivo de configuración
            config_dir = Path(__file__).parent.parent.parent / "nlp_config"
            sentiment_file = config_dir / "sentiment_dict.json"
            
            if sentiment_file.exists():
                with open(sentiment_file, 'r', encoding='utf-8') as f:
                    self.sentiment_dict = json.load(f)
                logger.info(f"Diccionario de sentimiento cargado desde {sentiment_file}")
            else:
                logger.warning(f"Archivo de diccionario de sentimiento no encontrado: {sentiment_file}")
                self.sentiment_dict = {
                    "version": "1.0.0",
                    "positive": {"es": [], "en": []},
                    "negative": {"es": [], "en": []},
                    "neutral": {"es": [], "en": []}
                }
        except Exception as e:
            logger.error(f"Error cargando diccionario de sentimiento: {e}")
            self.sentiment_dict = {
                "version": "1.0.0",
                "positive": {"es": [], "en": []},
                "negative": {"es": [], "en": []},
                "neutral": {"es": [], "en": []}
            }
    
    def analyze_sentiment(self, text: str, language: Optional[str] = None) -> Dict[str, float]:
        """
        Analiza el sentimiento de un texto.
        
        Args:
            text: Texto a analizar
            language: Idioma del texto ('es' o 'en'). Si es None, se detecta automáticamente
        
        Returns:
            Diccionario con scores de sentimiento: {"positive": 0.0-1.0, "negative": 0.0-1.0, "neutral": 0.0-1.0}
        """
        if not text:
            return {"positive": 0.0, "negative": 0.0, "neutral": 1.0}
        
        if language is None:
            language = self.nlp_processor.detect_language(text)
        
        # Normalizar texto
        normalized_text = self.nlp_processor.normalize_text(text)
        
        # Obtener lemas para mejor matching
        lemmas = self.nlp_processor.lemmatize(text, language)
        lemma_text = " " + " ".join(lemmas) + " "
        
        # Obtener diccionarios para el idioma
        positive_words = set(self.sentiment_dict.get("positive", {}).get(language, []))
        negative_words = set(self.sentiment_dict.get("negative", {}).get(language, []))
        neutral_words = set(self.sentiment_dict.get("neutral", {}).get(language, []))
        
        # Contar ocurrencias
        positive_count = sum(1 for word in positive_words if f" {word} " in lemma_text or word in normalized_text)
        negative_count = sum(1 for word in negative_words if f" {word} " in lemma_text or word in normalized_text)
        neutral_count = sum(1 for word in neutral_words if f" {word} " in lemma_text or word in normalized_text)
        
        # Calcular scores (normalizados y deterministas)
        total_count = positive_count + negative_count + neutral_count
        
        if total_count == 0:
            # Sin palabras de sentimiento detectadas, retornar neutral
            return {"positive": 0.0, "negative": 0.0, "neutral": 1.0}
        
        # Scores basados en frecuencia (determinista)
        positive_score = positive_count / total_count
        negative_score = negative_count / total_count
        neutral_score = neutral_count / total_count
        
        # Asegurar que sumen 1.0 (normalización determinista)
        total_score = positive_score + negative_score + neutral_score
        if total_score > 0:
            positive_score = round(positive_score / total_score, 6)
            negative_score = round(negative_score / total_score, 6)
            neutral_score = round(neutral_score / total_score, 6)
        else:
            # Fallback si total_score es 0 (no debería pasar)
            positive_score = 0.0
            negative_score = 0.0
            neutral_score = 1.0
        
        # Retornar scores con precisión suficiente para reproducibilidad
        return {
            "positive": round(positive_score, 6),
            "negative": round(negative_score, 6),
            "neutral": round(neutral_score, 6)
        }
    
    def get_sentiment_label(self, text: str, language: Optional[str] = None) -> str:
        """
        Obtiene la etiqueta de sentimiento dominante.
        
        Args:
            text: Texto a analizar
            language: Idioma del texto
        
        Returns:
            Etiqueta: "positive", "negative", o "neutral"
        """
        scores = self.analyze_sentiment(text, language)
        
        # Retornar el sentimiento con mayor score
        max_sentiment = max(scores.items(), key=lambda x: x[1])
        return max_sentiment[0]
