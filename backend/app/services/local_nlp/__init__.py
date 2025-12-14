"""Módulo de NLP local basado en reglas y modelos tradicionales."""
from app.services.local_nlp.nlp_processor import NLPProcessor, get_nlp_processor
from app.services.local_nlp.sentiment_analyzer import SentimentAnalyzer
from app.services.local_nlp.sector_classifier import SectorClassifier
from app.services.local_nlp.entity_extractor import EntityExtractor
from app.services.local_nlp.local_nlp_service import LocalNLPService, get_local_nlp_service
from app.services.local_nlp.dictionary_loader import DictionaryLoader, get_dictionary_loader

__all__ = [
    "NLPProcessor",
    "get_nlp_processor",
    "SentimentAnalyzer",
    "SectorClassifier",
    "EntityExtractor",
    "LocalNLPService",
    "get_local_nlp_service",
    "DictionaryLoader",
    "get_dictionary_loader"
]
