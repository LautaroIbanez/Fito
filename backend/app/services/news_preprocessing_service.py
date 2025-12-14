"""Servicio para preprocesar y estandarizar noticias usando NLP local (sin LLM)."""
import logging
import json
import re
from typing import Dict, List, Optional
from datetime import datetime, timezone
from app.config import (
    STANDARDIZED_NEWS_MAX_BULLET_LENGTH,
    STANDARDIZED_NEWS_MIN_BULLETS,
    STANDARDIZED_NEWS_MAX_BULLETS,
    STANDARDIZED_NEWS_SENTIMENT_ENUM
)
from app.models import StandardizedNewsData
from app.services.local_nlp import get_local_nlp_service
from app.services.sentiment_service import get_sentiment_service
from app.services.sector_service import get_sector_service

logger = logging.getLogger(__name__)


class NewsPreprocessingService:
    """Servicio para preprocesar y estandarizar noticias usando NLP local."""
    
    def __init__(self):
        """Inicializa los servicios de NLP local."""
        self.nlp_service = get_local_nlp_service()
        self.sentiment_service = get_sentiment_service()
        self.sector_service = get_sector_service()
        logger.info("NewsPreprocessingService inicializado (sin LLM, usando NLP local)")
    
    def standardize_news(self, article_text: str) -> StandardizedNewsData:
        """
        Estandariza una noticia usando NLP local (sin LLM).
        
        Args:
            article_text: Texto completo del artículo
            
        Returns:
            StandardizedNewsData: Datos estandarizados de la noticia
        """
        if not article_text or not article_text.strip():
            raise ValueError("El texto del artículo no puede estar vacío")
        
        try:
            logger.info(f"Estandarizando noticia usando NLP local (sin LLM)")
            
            # Analizar noticia completa con NLP local
            analysis = self.nlp_service.analyze_news(article_text)
            
            # Extraer título (primera línea o primeros 100 caracteres)
            title = self._extract_title(article_text)
            
            # Extraer fecha de publicación (buscar patrones de fecha)
            publication_date = self._extract_publication_date(article_text)
            
            # Extraer fuente (buscar al inicio del texto)
            source = self._extract_source(article_text)
            
            # Generar bullets de resumen (primeras oraciones del texto)
            summary_bullets = self._generate_summary_bullets(article_text)
            
            # Extraer personas y empresas clave (entidades)
            key_people_companies = self._extract_key_entities(article_text, analysis)
            
            # Extraer números y métricas
            quoted_numbers_metrics = self._extract_numbers_metrics(article_text)
            
            # Analizar sentimiento (usar servicio local)
            sentiment_result = self.sentiment_service.analyze_sentiment(article_text)
            sentiment = self._map_sentiment_to_enum(sentiment_result["sentiment"])
            
            # Generar "why_it_matters" básico
            why_it_matters = self._generate_why_it_matters(article_text, analysis, sentiment_result)
            
            # Construir datos estandarizados
            standardized_dict = {
                "title": title,
                "publication_date": publication_date,
                "source": source,
                "summary_bullets": summary_bullets,
                "key_people_companies": key_people_companies,
                "quoted_numbers_metrics": quoted_numbers_metrics,
                "sentiment": sentiment,
                "why_it_matters": why_it_matters
            }
            
            # Validar y limpiar los datos
            standardized_data = self._validate_and_clean_standardized_data(standardized_dict)
            
            logger.info(
                f"Noticia estandarizada exitosamente (sin LLM): "
                f"sentiment={sentiment}, sector={analysis.get('primary_sector', 'N/A')}, "
                f"bullets={len(summary_bullets)}, entities={len(key_people_companies)}"
            )
            return standardized_data
            
        except Exception as e:
            logger.error(f"Error estandarizando noticia con NLP local: {e}", exc_info=True)
            raise ValueError(f"Error al estandarizar noticia: {str(e)}")
    
    def _extract_title(self, text: str) -> str:
        """Extrae el título del artículo (primera línea o primeros 100 caracteres)."""
        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            if line and len(line) > 10 and len(line) < 200:
                return line
        
        # Si no hay línea adecuada, usar primeros caracteres
        title = text[:100].strip()
        if title.endswith('...'):
            title = title[:-3]
        return title or "Sin título"
    
    def _extract_publication_date(self, text: str) -> Optional[str]:
        """Extrae fecha de publicación usando patrones regex."""
        # Patrones comunes de fecha
        date_patterns = [
            r'\b(\d{4}-\d{2}-\d{2})\b',  # YYYY-MM-DD
            r'\b(\d{2}/\d{2}/\d{4})\b',  # DD/MM/YYYY
            r'\b(\d{2}-\d{2}-\d{4})\b',  # DD-MM-YYYY
            r'\b(\w+\s+\d{1,2},\s+\d{4})\b',  # Month DD, YYYY
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, text[:500])  # Buscar en primeros 500 caracteres
            if match:
                try:
                    date_str = match.group(1)
                    # Intentar parsear
                    if '-' in date_str and len(date_str) == 10:
                        return date_str
                except:
                    pass
        
        return None
    
    def _extract_source(self, text: str) -> Optional[str]:
        """Extrae la fuente del artículo (buscar al inicio)."""
        # Buscar patrones comunes de fuente
        source_patterns = [
            r'^(?:Por|By|Fuente|Source):\s*([A-Z][A-Za-z\s]+)',
            r'^([A-Z][A-Za-z\s]+)\s*[-–]\s*',  # Nombre - inicio
        ]
        
        first_lines = text.split('\n')[:3]
        for line in first_lines:
            for pattern in source_patterns:
                match = re.search(pattern, line)
                if match:
                    source = match.group(1).strip()
                    if len(source) > 2 and len(source) < 100:
                        return source
        
        return None
    
    def _generate_summary_bullets(self, text: str) -> List[str]:
        """Genera bullets de resumen desde las primeras oraciones."""
        # Dividir en oraciones
        sentences = re.split(r'[.!?]+', text)
        bullets = []
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            # Limitar longitud de palabras
            words = sentence.split()
            if len(words) > STANDARDIZED_NEWS_MAX_BULLET_LENGTH:
                words = words[:STANDARDIZED_NEWS_MAX_BULLET_LENGTH]
                sentence = " ".join(words) + "..."
            
            if len(sentence) > 20:  # Mínimo de caracteres
                bullets.append(sentence)
                if len(bullets) >= STANDARDIZED_NEWS_MAX_BULLETS:
                    break
        
        # Asegurar mínimo de bullets
        if len(bullets) < STANDARDIZED_NEWS_MIN_BULLETS:
            # Usar primeros caracteres del texto
            remaining = STANDARDIZED_NEWS_MIN_BULLETS - len(bullets)
            text_remaining = text[len(" ".join(bullets)):].strip()
            words = text_remaining.split()[:STANDARDIZED_NEWS_MAX_BULLET_LENGTH * remaining]
            if words:
                additional = " ".join(words)
                if len(additional) > 20:
                    bullets.append(additional)
        
        return bullets[:STANDARDIZED_NEWS_MAX_BULLETS]
    
    def _extract_key_entities(self, text: str, analysis: Dict) -> List[str]:
        """Extrae personas y empresas clave de las entidades."""
        entities = []
        
        # Agregar organizaciones
        entities.extend(analysis.get("entities", {}).get("ORG", []))
        
        # Agregar personas
        entities.extend(analysis.get("entities", {}).get("PERSON", []))
        
        # Limitar y limpiar
        entities = [e.strip() for e in entities if e and len(e.strip()) > 2]
        entities = list(dict.fromkeys(entities))  # Eliminar duplicados manteniendo orden
        
        return entities[:10]  # Máximo 10 entidades
    
    def _extract_numbers_metrics(self, text: str) -> List[str]:
        """Extrae números y métricas usando regex."""
        metrics = []
        
        # Patrones para métricas financieras
        patterns = [
            r'\$[\d,]+(?:\.\d+)?[BMK]?',  # Montos en dólares
            r'\d+\.?\d*\s*%',  # Porcentajes
            r'\d+\.?\d*\s*(?:millones|millón|billones|billón|millones de|billones de)',  # Montos en español
            r'Q\d',  # Trimestres (Q1, Q2, etc.)
            r'\d{4}',  # Años
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            metrics.extend(matches)
        
        # Limpiar y limitar
        metrics = [m.strip() for m in metrics if m]
        metrics = list(dict.fromkeys(metrics))  # Eliminar duplicados
        
        return metrics[:10]  # Máximo 10 métricas
    
    def _map_sentiment_to_enum(self, sentiment: str) -> str:
        """Mapea sentimiento de NLP local a enum requerido."""
        sentiment_lower = sentiment.lower()
        
        if sentiment_lower == "positive":
            return "bullish"
        elif sentiment_lower == "negative":
            return "bearish"
        else:
            return "neutral"
    
    def _generate_why_it_matters(self, text: str, analysis: Dict, sentiment_result: Dict) -> str:
        """Genera una línea básica de 'why_it_matters'."""
        sector = analysis.get("primary_sector")
        sentiment = sentiment_result["sentiment"]
        
        # Construir mensaje básico
        parts = []
        
        if sector:
            parts.append(f"Impacto en sector {sector}")
        
        if sentiment == "positive":
            parts.append("tendencia positiva")
        elif sentiment == "negative":
            parts.append("riesgo identificado")
        else:
            parts.append("desarrollo relevante")
        
        # Agregar información de tickers si hay
        tickers = analysis.get("tickers", [])
        if tickers:
            parts.append(f"afecta a {', '.join(tickers[:3])}")
        
        why_it_matters = ". ".join(parts) + "."
        
        # Limitar a 100 palabras
        words = why_it_matters.split()
        if len(words) > 100:
            words = words[:100]
            why_it_matters = " ".join(words)
        
        return why_it_matters if why_it_matters else "Noticia relevante para inversores."
    
    def _validate_and_clean_standardized_data(self, data: Dict) -> StandardizedNewsData:
        """
        Valida y limpia los datos estandarizados.
        Asegura que cumplan con los requisitos del modelo.
        """
        # Validar campos requeridos
        if "title" not in data or not data["title"]:
            raise ValueError("El título es requerido y no puede estar vacío")
        
        if "sentiment" not in data:
            raise ValueError("El sentimiento es requerido")
        
        if "summary_bullets" not in data or not isinstance(data["summary_bullets"], list):
            raise ValueError("summary_bullets debe ser un array")
        
        if "why_it_matters" not in data or not data["why_it_matters"]:
            raise ValueError("why_it_matters es requerido y no puede estar vacío")
        
        # Limpiar y validar bullets
        bullets = data["summary_bullets"]
        cleaned_bullets = []
        for bullet in bullets:
            if isinstance(bullet, str) and bullet.strip():
                # Truncar si excede el límite de palabras
                words = bullet.strip().split()
                if len(words) > STANDARDIZED_NEWS_MAX_BULLET_LENGTH:
                    words = words[:STANDARDIZED_NEWS_MAX_BULLET_LENGTH]
                    cleaned_bullet = " ".join(words)
                    logger.warning(f"Bullet truncado a {STANDARDIZED_NEWS_MAX_BULLET_LENGTH} palabras")
                else:
                    cleaned_bullet = bullet.strip()
                cleaned_bullets.append(cleaned_bullet)
        
        # Validar cantidad de bullets
        if len(cleaned_bullets) < STANDARDIZED_NEWS_MIN_BULLETS:
            raise ValueError(f"Se requieren al menos {STANDARDIZED_NEWS_MIN_BULLETS} bullets, se encontraron {len(cleaned_bullets)}")
        if len(cleaned_bullets) > STANDARDIZED_NEWS_MAX_BULLETS:
            cleaned_bullets = cleaned_bullets[:STANDARDIZED_NEWS_MAX_BULLETS]
            logger.warning(f"Se truncaron bullets a {STANDARDIZED_NEWS_MAX_BULLETS}")
        
        # Limpiar arrays opcionales
        key_people_companies = data.get("key_people_companies", [])
        if not isinstance(key_people_companies, list):
            key_people_companies = []
        
        quoted_numbers_metrics = data.get("quoted_numbers_metrics", [])
        if not isinstance(quoted_numbers_metrics, list):
            quoted_numbers_metrics = []
        
        # Validar sentimiento
        sentiment = data["sentiment"].lower()
        if sentiment not in [s.lower() for s in STANDARDIZED_NEWS_SENTIMENT_ENUM]:
            raise ValueError(f"Sentimiento inválido: {sentiment}. Debe ser uno de {STANDARDIZED_NEWS_SENTIMENT_ENUM}")
        
        # Truncar why_it_matters si es muy largo
        why_it_matters = data["why_it_matters"].strip()
        words = why_it_matters.split()
        if len(words) > 100:
            words = words[:100]
            why_it_matters = " ".join(words)
            logger.warning("why_it_matters truncado a 100 palabras")
        
        return StandardizedNewsData(
            title=data["title"].strip(),
            publication_date=data.get("publication_date"),
            source=data.get("source"),
            summary_bullets=cleaned_bullets,
            key_people_companies=[str(item).strip() for item in key_people_companies if item],
            quoted_numbers_metrics=[str(item).strip() for item in quoted_numbers_metrics if item],
            sentiment=sentiment,
            why_it_matters=why_it_matters
        )




