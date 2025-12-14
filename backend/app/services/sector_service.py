"""Servicio de clasificación de sectores sin LLM, basado en diccionarios."""
import logging
from typing import Dict, List, Optional, Any
from typing import Optional as Opt
from app.services.local_nlp import get_local_nlp_service

logger = logging.getLogger(__name__)


class SectorService:
    """Servicio para clasificación de sectores basado en reglas y diccionarios."""
    
    def __init__(self):
        """Inicializa el servicio."""
        self.nlp_service = get_local_nlp_service()
        logger.info("SectorService inicializado (sin LLM)")
    
    def classify_sector(
        self, 
        text: str, 
        title: Optional[str] = None,
        language: Optional[str] = None,
        top_n: int = 1
    ) -> Dict[str, Any]:
        """
        Clasifica el sector de un texto usando diccionarios locales.
        
        Args:
            text: Cuerpo del texto
            title: Título (opcional, se combina con el texto)
            language: Idioma del texto ('es' o 'en'). Si es None, se detecta automáticamente
            top_n: Número de sectores principales a retornar
        
        Returns:
            Diccionario con:
            {
                "primary_sector": "tecnología" | "finanzas" | ... | None,
                "sectors": [
                    {"sector": "...", "score": 0.0-1.0},
                    ...
                ],
                "confidence": 0.0-1.0,  # Confianza del sector principal
                "method": "dictionary_based",
                "language": "es" | "en"
            }
        """
        # Combinar título y texto
        full_text = f"{title} {text}" if title else text
        
        if not full_text:
            logger.warning("Texto vacío para clasificación de sector, retornando sin sector")
            return {
                "primary_sector": None,
                "sectors": [],
                "confidence": 0.0,
                "method": "dictionary_based",
                "language": language or "es"
            }
        
        # Analizar usando NLP local
        analysis = self.nlp_service.analyze_news(full_text, language=language)
        
        sectors = analysis["sectors"]
        primary_sector = analysis["primary_sector"]
        detected_language = analysis["language"]
        
        # Calcular confianza basada en el score del sector principal
        # Determinista: confianza = diferencia entre primer y segundo sector
        confidence = 0.0
        if sectors and len(sectors) > 0:
            primary_score = sectors[0]["score"]
            # Confianza aumenta si hay una diferencia clara con el segundo sector
            if len(sectors) > 1:
                second_score = sectors[1]["score"]
                confidence = max(0.0, primary_score - second_score)  # Asegurar no negativo
            else:
                confidence = primary_score
        
        # Log trazable y determinista (motor local)
        primary_score = sectors[0]['score'] if sectors and len(sectors) > 0 else 0.0
        logger.debug(
            f"[MOTOR LOCAL] [SECTOR] Texto analizado (longitud={len(full_text)} chars, idioma={detected_language}) | "
            f"Resultado: {primary_sector} | "
            f"Score: {primary_score:.6f} | "
            f"Confianza: {confidence:.6f} | "
            f"Sectores detectados: {len(sectors)} | "
            f"Método: dictionary_based (sin LLM)"
        )
        
        return {
            "primary_sector": primary_sector,
            "sectors": sectors[:top_n],
            "confidence": round(confidence, 3),
            "method": "dictionary_based",
            "language": detected_language
        }
    
    def get_primary_sector(
        self, 
        text: str, 
        title: Optional[str] = None,
        language: Optional[str] = None
    ) -> Optional[str]:
        """
        Obtiene solo el sector principal.
        
        Args:
            text: Cuerpo del texto
            title: Título (opcional)
            language: Idioma del texto
        
        Returns:
            Nombre del sector principal o None
        """
        result = self.classify_sector(text, title, language, top_n=1)
        return result["primary_sector"]


# Instancia global del servicio
_sector_service_instance: Optional[SectorService] = None


def get_sector_service() -> SectorService:
    """Obtiene la instancia global del servicio de sectores."""
    global _sector_service_instance
    if _sector_service_instance is None:
        _sector_service_instance = SectorService()
    return _sector_service_instance
