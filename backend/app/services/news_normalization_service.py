"""Servicio para normalizar noticias en esquema unificado."""
import logging
import json
import re
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.database import NewsItem, NormalizedNews
from app.models import NewsItemResponse, StandardizedNewsData
from app.config import (
    NORMALIZED_NEWS_REQUIRED_FIELDS,
    NORMALIZED_NEWS_MIN_IMPACT_SCORE,
    NORMALIZED_NEWS_MAX_IMPACT_SCORE,
    NORMALIZED_NEWS_VALID_SENTIMENTS,
    NORMALIZED_NEWS_MIN_SUMMARY_LENGTH,
    NORMALIZED_NEWS_MAX_SUMMARY_LENGTH,
    NORMALIZED_NEWS_REJECT_ON_CRITICAL_ERROR,
    NORMALIZED_NEWS_REQUIRE_TICKERS_OR_ENTITIES
)

logger = logging.getLogger(__name__)


class NewsNormalizationService:
    """Servicio para normalizar noticias en esquema unificado."""
    
    def normalize_news(
        self,
        news_item: NewsItemResponse,
        standardized_data: Optional[StandardizedNewsData] = None
    ) -> Tuple[Dict, List[str]]:
        """
        Normaliza una noticia al esquema unificado.
        
        Args:
            news_item: Noticia a normalizar
            standardized_data: Datos estandarizados opcionales (si ya existen)
        
        Returns:
            Tuple[Dict, List[str]]: (datos normalizados, lista de errores de validación)
        """
        errors = []
        normalized = {}
        
        # 1. Source (obligatorio)
        source = news_item.source or standardized_data.source if standardized_data else None
        if not source:
            errors.append("Campo 'source' es obligatorio y no se encontró")
            source = "Unknown"
        normalized["source"] = source
        
        # 2. Timestamp (obligatorio)
        try:
            if news_item.created_at:
                if isinstance(news_item.created_at, str):
                    timestamp = datetime.fromisoformat(news_item.created_at.replace('Z', '+00:00'))
                else:
                    timestamp = news_item.created_at
            elif standardized_data and standardized_data.publication_date:
                timestamp = datetime.fromisoformat(standardized_data.publication_date.replace('Z', '+00:00'))
            else:
                timestamp = datetime.now(timezone.utc)
                errors.append("Campo 'timestamp' no encontrado, usando fecha actual")
        except (ValueError, AttributeError) as e:
            timestamp = datetime.now(timezone.utc)
            errors.append(f"Error parseando timestamp: {str(e)}, usando fecha actual")
        normalized["timestamp"] = timestamp
        
        # 3. Summary (obligatorio)
        if standardized_data and standardized_data.summary_bullets:
            summary = " ".join(standardized_data.summary_bullets)
        elif news_item.title:
            summary = news_item.title
        else:
            # Extraer primeros caracteres del body
            summary = news_item.body[:200] + "..." if len(news_item.body) > 200 else news_item.body
        
        # Validar longitud
        if len(summary) < NORMALIZED_NEWS_MIN_SUMMARY_LENGTH:
            errors.append(f"Summary demasiado corto ({len(summary)} caracteres, mínimo {NORMALIZED_NEWS_MIN_SUMMARY_LENGTH})")
        elif len(summary) > NORMALIZED_NEWS_MAX_SUMMARY_LENGTH:
            summary = summary[:NORMALIZED_NEWS_MAX_SUMMARY_LENGTH - 3] + "..."
            errors.append(f"Summary truncado a {NORMALIZED_NEWS_MAX_SUMMARY_LENGTH} caracteres")
        
        normalized["summary"] = summary
        
        # 4. Sentiment (obligatorio)
        if standardized_data and standardized_data.sentiment:
            sentiment = standardized_data.sentiment.lower()
        else:
            # Intentar inferir del texto
            sentiment = self._infer_sentiment(news_item.body)
            errors.append("Sentiment inferido del texto (no estandarizado)")
        
        if sentiment not in [s.lower() for s in NORMALIZED_NEWS_VALID_SENTIMENTS]:
            errors.append(f"Sentiment inválido: {sentiment}, usando 'neutral'")
            sentiment = "neutral"
        normalized["sentiment"] = sentiment
        
        # 5. Impact Score (obligatorio)
        if news_item.score is not None:
            impact_score = min(max(news_item.score / 10.0, 0.0), 1.0)  # Normalizar score a 0-1
        else:
            # Calcular score básico basado en sentimiento y longitud
            impact_score = self._calculate_basic_impact_score(news_item, sentiment)
            errors.append("Impact score calculado básico (score original no disponible)")
        
        if impact_score < NORMALIZED_NEWS_MIN_IMPACT_SCORE or impact_score > NORMALIZED_NEWS_MAX_IMPACT_SCORE:
            errors.append(f"Impact score fuera de rango: {impact_score}, ajustando a rango válido")
            impact_score = max(NORMALIZED_NEWS_MIN_IMPACT_SCORE, min(impact_score, NORMALIZED_NEWS_MAX_IMPACT_SCORE))
        
        normalized["impact_score"] = round(impact_score, 3)
        
        # 6. Tickers (opcional pero recomendado)
        tickers = self._extract_tickers(news_item, standardized_data)
        normalized["tickers"] = tickers
        
        # 7. Entities (opcional pero recomendado)
        entities = self._extract_entities(news_item, standardized_data)
        normalized["entities"] = entities
        
        # Validar que haya tickers o entities si es requerido
        if NORMALIZED_NEWS_REQUIRE_TICKERS_OR_ENTITIES and not tickers and not entities:
            errors.append("Advertencia: No se encontraron tickers ni entities (requerido para cruzar con cartera)")
        
        # 8. Campos opcionales
        normalized["title"] = news_item.title or (standardized_data.title if standardized_data else None)
        normalized["original_text"] = news_item.body
        normalized["categories"] = self._extract_categories(news_item, standardized_data)
        normalized["metadata"] = {
            "original_news_id": news_item.id,
            "has_standardized_data": standardized_data is not None,
            "normalization_method": "automatic"
        }
        
        return normalized, errors
    
    def _infer_sentiment(self, text: str) -> str:
        """Infiere sentimiento del texto."""
        text_lower = text.lower()
        
        positive_words = ["crece", "aumenta", "sube", "positivo", "favorable", "ganancias", "éxito", "bullish", "up"]
        negative_words = ["cae", "baja", "negativo", "pérdida", "riesgo", "crisis", "bearish", "down", "drop"]
        
        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)
        
        if positive_count > negative_count:
            return "bullish"
        elif negative_count > positive_count:
            return "bearish"
        else:
            return "neutral"
    
    def _calculate_basic_impact_score(self, news_item: NewsItemResponse, sentiment: str) -> float:
        """Calcula un score de impacto básico."""
        base_score = 0.5
        
        # Ajustar por sentimiento
        if sentiment == "bullish":
            base_score += 0.1
        elif sentiment == "bearish":
            base_score += 0.1
        
        # Ajustar por longitud (noticias más largas pueden ser más importantes)
        if len(news_item.body) > 500:
            base_score += 0.1
        
        return min(1.0, base_score)
    
    def _extract_tickers(self, news_item: NewsItemResponse, standardized_data: Optional[StandardizedNewsData]) -> List[str]:
        """Extrae tickers de la noticia."""
        tickers = set()
        
        # Patrón para tickers (1-5 letras mayúsculas)
        ticker_pattern = re.compile(r'\b([A-Z]{1,5})(?:\.[A-Z]{1,2})?\b')
        
        # Buscar en título y cuerpo
        text_to_search = f"{news_item.title or ''} {news_item.body}".upper()
        matches = ticker_pattern.findall(text_to_search)
        
        # Filtrar palabras comunes
        common_words = {'THE', 'AND', 'FOR', 'ARE', 'BUT', 'NOT', 'YOU', 'ALL', 'CAN', 'HER', 'WAS', 'ONE', 'OUR', 'OUT', 'DAY', 'GET', 'HAS', 'HIM', 'HIS', 'HOW', 'ITS', 'MAY', 'NEW', 'NOW', 'OLD', 'SEE', 'TWO', 'WHO', 'WAY', 'USE', 'SHE', 'MAN', 'HAD'}
        
        for match in matches:
            if match not in common_words and len(match) >= 2:
                tickers.add(match)
        
        # Si hay datos estandarizados, usar también empresas clave
        if standardized_data and standardized_data.key_people_companies:
            for entity in standardized_data.key_people_companies:
                # Buscar posibles tickers en las entidades
                entity_matches = ticker_pattern.findall(entity.upper())
                tickers.update([m for m in entity_matches if m not in common_words and len(m) >= 2])
        
        return sorted(list(tickers))
    
    def _extract_entities(self, news_item: NewsItemResponse, standardized_data: Optional[StandardizedNewsData]) -> List[str]:
        """Extrae entidades (personas, empresas, sectores) de la noticia."""
        entities = []
        
        # Si hay datos estandarizados, usar empresas clave
        if standardized_data and standardized_data.key_people_companies:
            entities.extend(standardized_data.key_people_companies)
        
        # Buscar nombres propios comunes (empresas conocidas)
        known_companies = ["Apple", "Microsoft", "Google", "Amazon", "Tesla", "NVIDIA", "Meta", "JPMorgan", "Goldman Sachs"]
        text_lower = (news_item.title or "" + " " + news_item.body).lower()
        
        for company in known_companies:
            if company.lower() in text_lower:
                entities.append(company)
        
        # Eliminar duplicados manteniendo orden
        seen = set()
        unique_entities = []
        for entity in entities:
            entity_lower = entity.lower()
            if entity_lower not in seen:
                seen.add(entity_lower)
                unique_entities.append(entity)
        
        return unique_entities
    
    def _extract_categories(self, news_item: NewsItemResponse, standardized_data: Optional[StandardizedNewsData]) -> List[str]:
        """Extrae categorías/sectores de la noticia."""
        categories = []
        
        # Sectores comunes
        sectors = ["Tecnología", "Energía", "Salud", "Finanzas", "Consumo", "Industriales", "Materiales"]
        text_lower = (news_item.title or "" + " " + news_item.body).lower()
        
        for sector in sectors:
            if sector.lower() in text_lower:
                categories.append(sector)
        
        return categories
    
    def validate_normalized_news(self, normalized: Dict) -> Tuple[bool, List[str]]:
        """
        Valida una noticia normalizada.
        
        Returns:
            Tuple[bool, List[str]]: (es_válida, lista_de_errores)
        """
        errors = []
        
        # Validar campos obligatorios
        for field in NORMALIZED_NEWS_REQUIRED_FIELDS:
            if field not in normalized or normalized[field] is None:
                errors.append(f"Campo obligatorio '{field}' faltante")
        
        # Validar tipos y rangos
        if "impact_score" in normalized:
            score = normalized["impact_score"]
            if not isinstance(score, (int, float)):
                errors.append(f"Impact score debe ser numérico, recibido: {type(score)}")
            elif score < NORMALIZED_NEWS_MIN_IMPACT_SCORE or score > NORMALIZED_NEWS_MAX_IMPACT_SCORE:
                errors.append(f"Impact score fuera de rango: {score} (debe estar entre {NORMALIZED_NEWS_MIN_IMPACT_SCORE} y {NORMALIZED_NEWS_MAX_IMPACT_SCORE})")
        
        if "sentiment" in normalized:
            sentiment = normalized["sentiment"]
            if sentiment not in [s.lower() for s in NORMALIZED_NEWS_VALID_SENTIMENTS]:
                errors.append(f"Sentiment inválido: {sentiment} (debe ser uno de: {', '.join(NORMALIZED_NEWS_VALID_SENTIMENTS)})")
        
        if "summary" in normalized:
            summary = normalized["summary"]
            if len(summary) < NORMALIZED_NEWS_MIN_SUMMARY_LENGTH:
                errors.append(f"Summary demasiado corto: {len(summary)} caracteres (mínimo: {NORMALIZED_NEWS_MIN_SUMMARY_LENGTH})")
            elif len(summary) > NORMALIZED_NEWS_MAX_SUMMARY_LENGTH:
                errors.append(f"Summary demasiado largo: {len(summary)} caracteres (máximo: {NORMALIZED_NEWS_MAX_SUMMARY_LENGTH})")
        
        # Validar que haya tickers o entities si es requerido
        if NORMALIZED_NEWS_REQUIRE_TICKERS_OR_ENTITIES:
            tickers = normalized.get("tickers", [])
            entities = normalized.get("entities", [])
            if not tickers and not entities:
                errors.append("Se requiere al menos un ticker o entity para cruzar con cartera")
        
        # Determinar si es crítico
        critical_errors = [e for e in errors if "obligatorio" in e.lower() or "faltante" in e.lower()]
        is_valid = len(critical_errors) == 0
        
        return is_valid, errors
    
    def save_normalized_news(
        self,
        db: Session,
        normalized: Dict,
        validation_errors: List[str],
        original_news_id: Optional[int] = None
    ) -> NormalizedNews:
        """
        Guarda una noticia normalizada en la base de datos.
        
        Args:
            db: Sesión de base de datos
            normalized: Datos normalizados
            validation_errors: Lista de errores de validación
            original_news_id: ID de la noticia original (opcional)
        
        Returns:
            NormalizedNews: Noticia normalizada guardada
        """
        # Determinar estado
        is_valid, _ = self.validate_normalized_news(normalized)
        
        if NORMALIZED_NEWS_REJECT_ON_CRITICAL_ERROR and not is_valid:
            status = "error"
        elif validation_errors:
            status = "warning"
        else:
            status = "valid"
        
        # Preparar datos para guardar
        db_item = NormalizedNews(
            source=normalized["source"],
            timestamp=normalized["timestamp"],
            summary=normalized["summary"],
            sentiment=normalized["sentiment"],
            impact_score=normalized["impact_score"],
            tickers=json.dumps(normalized.get("tickers", []), ensure_ascii=False),
            entities=json.dumps(normalized.get("entities", []), ensure_ascii=False),
            title=normalized.get("title"),
            original_text=normalized.get("original_text"),
            categories=json.dumps(normalized.get("categories", []), ensure_ascii=False),
            metadata_json=json.dumps(normalized.get("metadata", {}), ensure_ascii=False),
            status=status,
            error_details="; ".join(validation_errors) if validation_errors else None,
            validation_errors=json.dumps(validation_errors, ensure_ascii=False) if validation_errors else None,
            original_news_id=original_news_id
        )
        
        db.add(db_item)
        db.commit()
        db.refresh(db_item)
        
        logger.info(f"Noticia normalizada guardada: ID {db_item.id}, status: {status}, errores: {len(validation_errors)}")
        
        return db_item


