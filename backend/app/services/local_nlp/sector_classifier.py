"""Clasificador de sectores basado en diccionarios."""
import logging
import json
from typing import List, Dict, Optional
from pathlib import Path
from app.services.local_nlp.nlp_processor import get_nlp_processor

logger = logging.getLogger(__name__)


class SectorClassifier:
    """Clasificador de sectores basado en diccionarios de palabras clave."""
    
    def __init__(self):
        """Inicializa el clasificador cargando los diccionarios."""
        self.nlp_processor = get_nlp_processor()
        self.sectors_dict: Dict = {}
        self._load_sectors_dictionary()
    
    def _load_sectors_dictionary(self):
        """Carga el diccionario de sectores desde archivo JSON."""
        try:
            config_dir = Path(__file__).parent.parent.parent / "nlp_config"
            sectors_file = config_dir / "sectors_dict.json"
            
            if sectors_file.exists():
                with open(sectors_file, 'r', encoding='utf-8') as f:
                    self.sectors_dict = json.load(f)
                logger.info(f"Diccionario de sectores cargado desde {sectors_file}")
            else:
                logger.warning(f"Archivo de diccionario de sectores no encontrado: {sectors_file}")
                self.sectors_dict = {"version": "1.0.0", "sectors": {}}
        except Exception as e:
            logger.error(f"Error cargando diccionario de sectores: {e}")
            self.sectors_dict = {"version": "1.0.0", "sectors": {}}
    
    def classify_sectors(self, text: str, language: Optional[str] = None, top_n: int = 3) -> List[Dict[str, float]]:
        """
        Clasifica el texto en sectores.
        
        Args:
            text: Texto a clasificar
            language: Idioma del texto
            top_n: Número de sectores principales a retornar
        
        Returns:
            Lista de diccionarios con sector y score: [{"sector": "tecnología", "score": 0.85}, ...]
        """
        if not text:
            return []
        
        if language is None:
            language = self.nlp_processor.detect_language(text)
        
        # Normalizar y lematizar
        normalized_text = self.nlp_processor.normalize_text(text)
        lemmas = self.nlp_processor.lemmatize(text, language)
        lemma_text = " " + " ".join(lemmas) + " "
        
        sector_scores = {}
        sectors = self.sectors_dict.get("sectors", {})
        
        for sector_name, sector_keywords in sectors.items():
            keywords = set(sector_keywords.get(language, []))
            
            if not keywords:
                continue
            
            # Contar matches
            matches = sum(1 for keyword in keywords if f" {keyword} " in lemma_text or keyword in normalized_text)
            
            if matches > 0:
                # Score basado en número de matches y longitud del texto
                score = matches / max(len(keywords), 1) * min(len(text) / 100, 1.0)
                sector_scores[sector_name] = score
        
        # Ordenar por score (descendente) y luego por nombre (ascendente) para desempate determinista
        # Usar score negativo para orden descendente, nombre para desempate alfabético
        sorted_sectors = sorted(
            sector_scores.items(),
            key=lambda x: (-x[1], x[0])  # Score negativo para orden descendente, nombre para desempate
        )[:top_n]
        
        return [
            {"sector": sector, "score": round(score, 3)}
            for sector, score in sorted_sectors
        ]
    
    def get_primary_sector(self, text: str, language: Optional[str] = None) -> Optional[str]:
        """
        Obtiene el sector principal del texto.
        
        Args:
            text: Texto a clasificar
            language: Idioma del texto
        
        Returns:
            Nombre del sector principal o None si no se encuentra
        """
        sectors = self.classify_sectors(text, language, top_n=1)
        return sectors[0]["sector"] if sectors else None
