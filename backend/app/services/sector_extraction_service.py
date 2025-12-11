"""Servicio para extraer sectores y temas de noticias usando NER y keywords."""
import logging
import json
import re
from typing import List, Dict, Set
from app.models import NewsItemResponse, StandardizedNewsData

logger = logging.getLogger(__name__)

# Taxonomía de sectores con keywords
SECTOR_KEYWORDS = {
    "Tecnología": [
        "tecnología", "tech", "software", "hardware", "cloud", "nube", "IA", "inteligencia artificial",
        "AI", "machine learning", "datos", "data", "ciberseguridad", "semiconductores", "chips",
        "Apple", "Microsoft", "Google", "Amazon", "Meta", "NVIDIA", "AMD", "Intel", "TSMC"
    ],
    "Energía": [
        "energía", "petróleo", "oil", "gas", "renovable", "solar", "eólica", "nuclear",
        "Exxon", "Chevron", "BP", "Shell", "Tesla", "energía limpia"
    ],
    "Salud": [
        "salud", "farmacéutica", "pharma", "biotech", "medicina", "hospitales", "seguros médicos",
        "Pfizer", "Moderna", "Johnson & Johnson", "UnitedHealth"
    ],
    "Finanzas": [
        "bancos", "finanzas", "financiero", "bancario", "crédito", "préstamos", "inversión",
        "JPMorgan", "Bank of America", "Goldman Sachs", "Visa", "Mastercard"
    ],
    "Consumo": [
        "retail", "consumo", "venta al por menor", "e-commerce", "Amazon", "Walmart", "Target",
        "consumidor", "bienes de consumo"
    ],
    "Industriales": [
        "industrial", "manufactura", "infraestructura", "construcción", "aeronáutica", "defensa",
        "Boeing", "Caterpillar", "General Electric"
    ],
    "Materiales": [
        "materiales", "minería", "acero", "cobre", "oro", "commodities", "materias primas"
    ],
    "Bienes Raíces": [
        "inmobiliario", "real estate", "REIT", "propiedades", "construcción", "hipotecas"
    ],
    "Comunicaciones": [
        "telecomunicaciones", "telecom", "5G", "internet", "streaming", "Netflix", "Disney",
        "AT&T", "Verizon", "T-Mobile"
    ],
    "Utilidades": [
        "utilidades", "servicios públicos", "electricidad", "agua", "gas natural"
    ]
}

# Temas/trends adicionales
THEME_KEYWORDS = {
    "ESG": ["ESG", "sostenible", "sustentable", "medio ambiente", "carbono", "emisiones"],
    "Criptomonedas": ["bitcoin", "crypto", "blockchain", "NFT", "ethereum"],
    "Energía Limpia": ["energía limpia", "renovable", "solar", "eólica", "hidrógeno"],
    "Inteligencia Artificial": ["IA", "AI", "machine learning", "deep learning", "chatbot"],
    "E-commerce": ["e-commerce", "online", "digital", "plataforma", "marketplace"],
    "Salud Digital": ["telemedicina", "salud digital", "wearables", "fitness tech"]
}


class SectorExtractionService:
    """Servicio para extraer sectores y temas de noticias."""
    
    def __init__(self):
        """Inicializa el servicio."""
        self.sector_keywords = SECTOR_KEYWORDS
        self.theme_keywords = THEME_KEYWORDS
    
    def extract_sectors_and_themes(
        self,
        news_item: NewsItemResponse,
        standardized_data: StandardizedNewsData = None
    ) -> Dict:
        """
        Extrae sectores y temas afectados por una noticia.
        
        Returns:
            Dict con: sectors (List[str]), themes (List[str]), confidence_scores
        """
        # Combinar texto de título y cuerpo
        text_parts = []
        if news_item.title:
            text_parts.append(news_item.title)
        text_parts.append(news_item.body)
        
        # Si hay datos estandarizados, usar también
        if standardized_data:
            if standardized_data.key_people_companies:
                text_parts.extend(standardized_data.key_people_companies)
            if standardized_data.summary_bullets:
                text_parts.extend(standardized_data.summary_bullets)
        
        full_text = " ".join(text_parts).lower()
        
        # Detectar sectores
        detected_sectors = self._detect_sectors(full_text)
        
        # Detectar temas
        detected_themes = self._detect_themes(full_text)
        
        # Calcular scores de confianza
        sector_scores = self._calculate_sector_scores(full_text, detected_sectors)
        theme_scores = self._calculate_theme_scores(full_text, detected_themes)
        
        return {
            "sectors": detected_sectors,
            "themes": detected_themes,
            "sector_scores": sector_scores,
            "theme_scores": theme_scores,
            "extraction_method": "keyword_matching"
        }
    
    def _detect_sectors(self, text: str) -> List[str]:
        """Detecta sectores mencionados en el texto."""
        detected = []
        
        for sector, keywords in self.sector_keywords.items():
            matches = 0
            for keyword in keywords:
                # Buscar keyword como palabra completa
                pattern = r'\b' + re.escape(keyword.lower()) + r'\b'
                if re.search(pattern, text):
                    matches += 1
            
            if matches > 0:
                detected.append(sector)
        
        return detected
    
    def _detect_themes(self, text: str) -> List[str]:
        """Detecta temas/trends mencionados en el texto."""
        detected = []
        
        for theme, keywords in self.theme_keywords.items():
            matches = 0
            for keyword in keywords:
                pattern = r'\b' + re.escape(keyword.lower()) + r'\b'
                if re.search(pattern, text):
                    matches += 1
            
            if matches > 0:
                detected.append(theme)
        
        return detected
    
    def _calculate_sector_scores(self, text: str, sectors: List[str]) -> Dict[str, float]:
        """Calcula scores de confianza para sectores detectados."""
        scores = {}
        
        for sector in sectors:
            keywords = self.sector_keywords.get(sector, [])
            matches = 0
            total_keywords = len(keywords)
            
            for keyword in keywords:
                pattern = r'\b' + re.escape(keyword.lower()) + r'\b'
                if re.search(pattern, text):
                    matches += 1
            
            # Score basado en ratio de keywords encontradas
            score = min(1.0, matches / max(1, total_keywords / 3))  # Normalizar
            scores[sector] = round(score, 2)
        
        return scores
    
    def _calculate_theme_scores(self, text: str, themes: List[str]) -> Dict[str, float]:
        """Calcula scores de confianza para temas detectados."""
        scores = {}
        
        for theme in themes:
            keywords = self.theme_keywords.get(theme, [])
            matches = 0
            
            for keyword in keywords:
                pattern = r'\b' + re.escape(keyword.lower()) + r'\b'
                if re.search(pattern, text):
                    matches += 1
            
            # Score más simple para temas
            score = min(1.0, matches / 2.0)
            scores[theme] = round(score, 2)
        
        return scores


