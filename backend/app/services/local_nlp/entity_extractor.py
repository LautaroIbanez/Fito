"""Extractor de entidades usando spaCy."""
import logging
from typing import List, Dict, Optional
from app.services.local_nlp.nlp_processor import get_nlp_processor

logger = logging.getLogger(__name__)


class EntityExtractor:
    """Extractor de entidades nombradas usando spaCy."""
    
    def __init__(self):
        """Inicializa el extractor."""
        self.nlp_processor = get_nlp_processor()
    
    def extract_entities(self, text: str, language: Optional[str] = None) -> Dict[str, List[str]]:
        """
        Extrae entidades nombradas de un texto.
        
        Args:
            text: Texto a analizar
            language: Idioma del texto
        
        Returns:
            Diccionario con tipos de entidades y sus valores
        """
        if not text:
            return {
                "ORG": [],
                "PERSON": [],
                "GPE": [],
                "MONEY": [],
                "DATE": []
            }
        
        doc = self.nlp_processor.process_text(text, language)
        
        entities = {
            "ORG": [],      # Organizaciones
            "PERSON": [],   # Personas
            "GPE": [],      # Geopolíticas (países, ciudades)
            "MONEY": [],    # Montos monetarios
            "DATE": []      # Fechas
        }
        
        for ent in doc.ents:
            entity_type = ent.label_
            entity_text = ent.text.strip()
            
            if entity_type in entities:
                if entity_text not in entities[entity_type]:
                    entities[entity_type].append(entity_text)
            elif entity_type == "LOC":  # Localizaciones (spaCy español)
                if entity_text not in entities["GPE"]:
                    entities["GPE"].append(entity_text)
        
        return entities
    
    def extract_organizations(self, text: str, language: Optional[str] = None) -> List[str]:
        """Extrae organizaciones del texto."""
        entities = self.extract_entities(text, language)
        return entities.get("ORG", [])
    
    def extract_people(self, text: str, language: Optional[str] = None) -> List[str]:
        """Extrae personas del texto."""
        entities = self.extract_entities(text, language)
        return entities.get("PERSON", [])
    
    def extract_locations(self, text: str, language: Optional[str] = None) -> List[str]:
        """Extrae ubicaciones geográficas del texto."""
        entities = self.extract_entities(text, language)
        return entities.get("GPE", [])
    
    def extract_tickers(self, text: str) -> List[str]:
        """
        Extrae posibles tickers de acciones del texto.
        Basado en patrones comunes: símbolos en mayúsculas, códigos de bolsa, etc.
        
        Args:
            text: Texto a analizar
        
        Returns:
            Lista de posibles tickers
        """
        import re
        
        tickers = []
        
        # Patrón 1: Palabras en mayúsculas de 1-5 letras seguidas de punto y código de bolsa
        # Ej: AAPL, TSLA, MSFT, GGAL.BA
        pattern1 = r'\b([A-Z]{1,5}(?:\.[A-Z]{2,4})?)\b'
        matches1 = re.findall(pattern1, text)
        
        # Patrón 2: Símbolos seguidos de "stock", "shares", "equity", etc.
        pattern2 = r'\b([A-Z]{2,5})\s+(?:stock|shares|equity|acciones|título)'
        matches2 = re.findall(pattern2, text, re.IGNORECASE)
        
        # Combinar y limpiar
        all_matches = matches1 + matches2
        
        # Filtrar palabras comunes que no son tickers
        common_words = {"THE", "AND", "FOR", "ARE", "BUT", "NOT", "YOU", "ALL", "CAN", "HER", "WAS", "ONE", "OUR", "OUT", "DAY", "GET", "HAS", "HIM", "HIS", "HOW", "ITS", "MAY", "NEW", "NOW", "OLD", "SEE", "TWO", "WHO", "BOY", "DID", "ITS", "LET", "PUT", "SAY", "SHE", "TOO", "USE"}
        
        for match in all_matches:
            ticker = match.upper()
            if len(ticker) >= 1 and len(ticker) <= 6 and ticker not in common_words:
                if ticker not in tickers:
                    tickers.append(ticker)
        
        return tickers
