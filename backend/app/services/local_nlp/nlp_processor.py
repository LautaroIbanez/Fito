"""Procesador principal de NLP local usando spaCy."""
import logging
import os
from typing import Optional, Dict, List
import spacy
from spacy.lang.es import Spanish
from spacy.lang.en import English

logger = logging.getLogger(__name__)


class NLPProcessor:
    """Procesador principal de NLP local usando spaCy."""
    
    def __init__(self):
        """Inicializa los modelos de spaCy."""
        self.nlp_es: Optional[spacy.Language] = None
        self.nlp_en: Optional[spacy.Language] = None
        self._load_models()
    
    def _load_models(self):
        """Carga los modelos de spaCy para español e inglés."""
        try:
            # Intentar cargar modelos completos primero
            try:
                self.nlp_es = spacy.load("es_core_news_sm")
                logger.info("Modelo spaCy español (es_core_news_sm) cargado exitosamente")
            except OSError:
                # Si no está instalado, usar el modelo base
                logger.warning("Modelo es_core_news_sm no encontrado, usando modelo base español")
                self.nlp_es = Spanish()
                self.nlp_es.add_pipe("sentencizer")
            
            try:
                self.nlp_en = spacy.load("en_core_web_sm")
                logger.info("Modelo spaCy inglés (en_core_web_sm) cargado exitosamente")
            except OSError:
                logger.warning("Modelo en_core_web_sm no encontrado, usando modelo base inglés")
                self.nlp_en = English()
                self.nlp_en.add_pipe("sentencizer")
                
        except Exception as e:
            logger.error(f"Error cargando modelos de spaCy: {e}")
            # Fallback a modelos base sin dependencias externas
            self.nlp_es = Spanish()
            self.nlp_es.add_pipe("sentencizer")
            self.nlp_en = English()
            self.nlp_en.add_pipe("sentencizer")
            logger.info("Usando modelos base de spaCy (sin dependencias de red)")
    
    def detect_language(self, text: str) -> str:
        """
        Detecta el idioma del texto.
        
        Args:
            text: Texto a analizar
        
        Returns:
            Código de idioma ('es' o 'en')
        """
        if not text:
            return "es"  # Default a español
        
        # Detección simple basada en palabras comunes
        text_lower = text.lower()
        spanish_words = ["el", "la", "de", "que", "y", "en", "un", "es", "se", "no", "te", "lo", "le", "da", "su", "por", "son", "con", "para", "del", "una", "está", "más", "muy", "sin", "sobre", "también", "después", "hasta", "donde", "quien", "están", "estado", "estados", "ser", "son", "dos", "también", "fue", "había", "era", "muy", "años", "año", "años", "hasta", "desde", "está", "ser", "son", "más", "muy", "sin", "sobre", "también", "después", "hasta", "donde", "quien", "están", "estado", "estados", "ser", "son", "dos", "también", "fue", "había", "era", "muy", "años", "año", "años", "hasta", "desde"]
        english_words = ["the", "be", "to", "of", "and", "a", "in", "that", "have", "i", "it", "for", "not", "on", "with", "he", "as", "you", "do", "at", "this", "but", "his", "by", "from", "they", "we", "say", "her", "she", "or", "an", "will", "my", "one", "all", "would", "there", "their", "what", "so", "up", "out", "if", "about", "who", "get", "which", "go", "me", "when", "make", "can", "like", "time", "no", "just", "him", "know", "take", "people", "into", "year", "your", "good", "some", "could", "them", "see", "other", "than", "then", "now", "look", "only", "come", "its", "over", "think", "also", "back", "after", "use", "two", "how", "our", "work", "first", "well", "way", "even", "new", "want", "because", "any", "these", "give", "day", "most", "us"]
        
        spanish_count = sum(1 for word in spanish_words if word in text_lower)
        english_count = sum(1 for word in english_words if word in text_lower)
        
        return "es" if spanish_count > english_count else "en"
    
    def process_text(self, text: str, language: Optional[str] = None) -> spacy.tokens.Doc:
        """
        Procesa un texto con spaCy.
        
        Args:
            text: Texto a procesar
            language: Idioma del texto ('es' o 'en'). Si es None, se detecta automáticamente
        
        Returns:
            Documento procesado de spaCy
        """
        if not text:
            # Retornar documento vacío
            if language == "en" or (language is None and self.detect_language(text) == "en"):
                return self.nlp_en("")
            return self.nlp_es("")
        
        if language is None:
            language = self.detect_language(text)
        
        nlp = self.nlp_en if language == "en" else self.nlp_es
        return nlp(text)
    
    def normalize_text(self, text: str) -> str:
        """
        Normaliza un texto: lowercase, elimina espacios extra, etc.
        
        Args:
            text: Texto a normalizar
        
        Returns:
            Texto normalizado
        """
        if not text:
            return ""
        
        # Convertir a lowercase
        normalized = text.lower()
        
        # Eliminar espacios múltiples
        import re
        normalized = re.sub(r'\s+', ' ', normalized)
        
        # Eliminar espacios al inicio y final
        normalized = normalized.strip()
        
        return normalized
    
    def lemmatize(self, text: str, language: Optional[str] = None) -> List[str]:
        """
        Lematiza un texto (reduce palabras a su forma base).
        
        Args:
            text: Texto a lematizar
            language: Idioma del texto
        
        Returns:
            Lista de lemas
        """
        doc = self.process_text(text, language)
        lemmas = [token.lemma_.lower() for token in doc if not token.is_stop and not token.is_punct and token.is_alpha]
        return lemmas
    
    def extract_keywords(self, text: str, language: Optional[str] = None, max_keywords: int = 10) -> List[str]:
        """
        Extrae palabras clave de un texto.
        
        Args:
            text: Texto a analizar
            language: Idioma del texto
            max_keywords: Número máximo de keywords a retornar
        
        Returns:
            Lista de palabras clave
        """
        doc = self.process_text(text, language)
        
        # Filtrar: no stop words, no puntuación, solo alfanuméricos, longitud mínima
        keywords = [
            token.lemma_.lower() 
            for token in doc 
            if not token.is_stop 
            and not token.is_punct 
            and token.is_alpha 
            and len(token.lemma_) > 3
        ]
        
        # Contar frecuencia y retornar los más comunes
        from collections import Counter
        keyword_counts = Counter(keywords)
        top_keywords = [word for word, count in keyword_counts.most_common(max_keywords)]
        
        return top_keywords


# Instancia global del procesador
_nlp_processor_instance: Optional[NLPProcessor] = None


def get_nlp_processor() -> NLPProcessor:
    """Obtiene la instancia global del procesador NLP."""
    global _nlp_processor_instance
    if _nlp_processor_instance is None:
        _nlp_processor_instance = NLPProcessor()
    return _nlp_processor_instance
