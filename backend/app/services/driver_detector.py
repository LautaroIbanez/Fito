"""Servicio para detectar drivers temáticos agrupando noticias por keywords/entidades."""
import logging
from typing import List, Dict, Set, Tuple
from collections import Counter, defaultdict
from app.services.local_nlp import get_local_nlp_service
from app.services.sentiment_service import get_sentiment_service
from app.services.sector_service import get_sector_service

logger = logging.getLogger(__name__)


class DriverDetector:
    """Detecta drivers temáticos agrupando noticias por keywords, entidades y sectores comunes."""
    
    def __init__(self):
        """Inicializa los servicios de NLP local."""
        self.nlp_service = get_local_nlp_service()
        self.sentiment_service = get_sentiment_service()
        self.sector_service = get_sector_service()
        logger.info("DriverDetector inicializado (sin LLM)")
    
    def detect_drivers(
        self,
        news_items: List[Dict],
        max_drivers: int = 5,
        min_news_per_driver: int = 1  # Reducido a 1 para ser más permisivo
    ) -> List[Dict]:
        """
        Detecta drivers temáticos agrupando noticias por términos comunes.
        
        Args:
            news_items: Lista de diccionarios con noticias (debe tener 'id', 'title', 'body' o 'text')
            max_drivers: Máximo número de drivers a detectar
            min_news_per_driver: Mínimo de noticias por driver para considerarlo válido
        
        Returns:
            Lista de diccionarios con drivers, cada uno con:
            - driver: nombre del driver
            - description: descripción del driver
            - related_news_ids: lista de IDs de noticias relacionadas
            - keywords: keywords principales del driver
            - sector: sector principal del driver
            - sentiment: sentimiento dominante
        """
        if not news_items:
            logger.warning("No hay noticias para detectar drivers")
            return []
        
        logger.info(f"Detectando drivers: {len(news_items)} noticias, máximo {max_drivers} drivers")
        
        # Analizar todas las noticias
        news_analyses = []
        for item in news_items:
            text = item.get("body") or item.get("text") or item.get("title", "")
            if not text:
                continue
            
            analysis = self.nlp_service.analyze_news(text)
            sentiment_result = self.sentiment_service.analyze_sentiment(text, item.get("title"))
            sector_result = self.sector_service.classify_sector(text, item.get("title"))
            
            news_analyses.append({
                "id": item.get("id"),
                "title": item.get("title", ""),
                "text": text,
                "analysis": analysis,
                "sentiment": sentiment_result,
                "sector": sector_result,
                "item": item
            })
        
        if len(news_analyses) < min_news_per_driver:
            logger.warning(f"[MOTOR LOCAL] No hay suficientes noticias para detectar drivers (mínimo {min_news_per_driver}, encontradas {len(news_analyses)})")
            return []
        
        # Agrupar por sectores dominantes
        sector_groups = self._group_by_sector(news_analyses)
        
        # Agrupar por keywords/entidades comunes
        keyword_groups = self._group_by_keywords(news_analyses)
        
        # Combinar grupos y seleccionar top drivers
        drivers = self._combine_and_rank_groups(
            sector_groups,
            keyword_groups,
            news_analyses,
            max_drivers,
            min_news_per_driver
        )
        
        logger.info(f"[MOTOR LOCAL] Drivers detectados: {len(drivers)} drivers (procesamiento local, sin LLM)")
        for driver in drivers:
            logger.debug(
                f"Driver '{driver['driver']}': {len(driver['related_news_ids'])} noticias, "
                f"sector={driver.get('sector')}, sentiment={driver.get('sentiment')}"
            )
        
        return drivers
    
    def _group_by_sector(self, news_analyses: List[Dict]) -> Dict[str, List[Dict]]:
        """Agrupa noticias por sector principal."""
        sector_groups = defaultdict(list)
        
        for news in news_analyses:
            primary_sector = news["sector"].get("primary_sector")
            if primary_sector:
                sector_groups[primary_sector].append(news)
        
        logger.debug(f"[MOTOR LOCAL] Agrupación por sectores: {len(sector_groups)} sectores únicos encontrados")
        for sector, news_list in sector_groups.items():
            logger.debug(f"  - {sector}: {len(news_list)} noticias")
        
        return dict(sector_groups)
    
    def _group_by_keywords(self, news_analyses: List[Dict]) -> Dict[str, List[Dict]]:
        """Agrupa noticias por keywords y entidades comunes."""
        # Extraer todas las keywords y entidades
        all_keywords = []
        all_entities = defaultdict(list)
        
        for news in news_analyses:
            analysis = news["analysis"]
            keywords = analysis.get("keywords", [])
            all_keywords.extend(keywords)
            
            entities = analysis.get("entities", {})
            for entity_type, entity_list in entities.items():
                all_entities[entity_type].extend(entity_list)
        
        # Contar frecuencia de keywords
        keyword_counter = Counter(all_keywords)
        # Reducir umbral: aceptar keywords que aparezcan al menos 1 vez (más permisivo)
        top_keywords = [kw for kw, count in keyword_counter.most_common(10) if count >= 1]
        logger.debug(f"[MOTOR LOCAL] Top keywords encontradas: {len(top_keywords)} (total keywords: {len(all_keywords)})")
        
        # Contar frecuencia de entidades
        entity_counter = Counter(all_entities.get("ORG", []) + all_entities.get("PERSON", []))
        # Reducir umbral: aceptar entidades que aparezcan al menos 1 vez (más permisivo)
        top_entities = [ent for ent, count in entity_counter.most_common(10) if count >= 1]
        logger.debug(f"[MOTOR LOCAL] Top entidades encontradas: {len(top_entities)} (total entidades: {len(all_entities.get('ORG', []) + all_entities.get('PERSON', []))})")
        
        # Agrupar noticias que comparten keywords/entidades
        keyword_groups = defaultdict(list)
        
        for news in news_analyses:
            analysis = news["analysis"]
            keywords = analysis.get("keywords", [])
            entities = analysis.get("entities", {})
            orgs = entities.get("ORG", [])
            persons = entities.get("PERSON", [])
            
            # Buscar coincidencias con top keywords/entidades
            matched_terms = []
            for kw in top_keywords:
                if kw.lower() in " ".join(keywords).lower():
                    matched_terms.append(kw)
            
            for ent in top_entities:
                if ent in orgs or ent in persons:
                    matched_terms.append(ent)
            
            # Agrupar por término más frecuente
            if matched_terms:
                # Usar el término más frecuente como clave
                primary_term = matched_terms[0]
                keyword_groups[primary_term].append(news)
        
        logger.debug(f"[MOTOR LOCAL] Agrupación por keywords: {len(keyword_groups)} grupos encontrados")
        for keyword, news_list in keyword_groups.items():
            logger.debug(f"  - '{keyword}': {len(news_list)} noticias")
        
        return dict(keyword_groups)
    
    def _combine_and_rank_groups(
        self,
        sector_groups: Dict[str, List[Dict]],
        keyword_groups: Dict[str, List[Dict]],
        news_analyses: List[Dict],
        max_drivers: int,
        min_news_per_driver: int
    ) -> List[Dict]:
        """Combina grupos de sectores y keywords, y selecciona top drivers."""
        all_groups = []
        
        # Agregar grupos de sectores
        for sector, news_list in sector_groups.items():
            if len(news_list) >= min_news_per_driver:
                logger.debug(f"[MOTOR LOCAL] Grupo de sector '{sector}': {len(news_list)} noticias")
                # Calcular sentimiento dominante
                sentiments = [n["sentiment"]["sentiment"] for n in news_list]
                sentiment_counter = Counter(sentiments)
                dominant_sentiment = sentiment_counter.most_common(1)[0][0] if sentiment_counter else "neutral"
                
                # Extraer keywords principales
                all_keywords = []
                for news in news_list:
                    keywords = news["analysis"].get("keywords", [])
                    all_keywords.extend(keywords)
                top_keywords = [kw for kw, _ in Counter(all_keywords).most_common(5)]
                
                all_groups.append({
                    "name": f"Sector: {sector}",
                    "type": "sector",
                    "news_list": news_list,
                    "sector": sector,
                    "sentiment": dominant_sentiment,
                    "keywords": top_keywords,
                    "score": len(news_list) * 2  # Peso mayor para sectores
                })
        
        # Agregar grupos de keywords
        for keyword, news_list in keyword_groups.items():
            if len(news_list) >= min_news_per_driver:
                logger.debug(f"[MOTOR LOCAL] Grupo de keyword '{keyword}': {len(news_list)} noticias")
                # Calcular sector dominante
                sectors = [n["sector"].get("primary_sector") for n in news_list if n["sector"].get("primary_sector")]
                sector_counter = Counter(sectors)
                dominant_sector = sector_counter.most_common(1)[0][0] if sector_counter else None
                
                # Calcular sentimiento dominante
                sentiments = [n["sentiment"]["sentiment"] for n in news_list]
                sentiment_counter = Counter(sentiments)
                dominant_sentiment = sentiment_counter.most_common(1)[0][0] if sentiment_counter else "neutral"
                
                all_groups.append({
                    "name": f"Tema: {keyword}",
                    "type": "keyword",
                    "news_list": news_list,
                    "sector": dominant_sector,
                    "sentiment": dominant_sentiment,
                    "keywords": [keyword],
                    "score": len(news_list)  # Peso menor para keywords individuales
                })
        
        # Ordenar por score y seleccionar top N
        all_groups.sort(key=lambda x: x["score"], reverse=True)
        top_groups = all_groups[:max_drivers]
        
        logger.debug(
            f"[MOTOR LOCAL] Grupos encontrados: {len(all_groups)} totales, "
            f"{len(sector_groups)} sectores, {len(keyword_groups)} keywords, "
            f"seleccionando top {len(top_groups)}"
        )
        
        # Si no hay grupos, crear un driver genérico con todas las noticias
        if not top_groups and news_analyses:
            logger.info(f"[MOTOR LOCAL] No se encontraron grupos específicos, creando driver genérico con {len(news_analyses)} noticias")
            # Agrupar todas las noticias en un driver genérico
            sentiments = [n["sentiment"]["sentiment"] for n in news_analyses]
            sentiment_counter = Counter(sentiments)
            dominant_sentiment = sentiment_counter.most_common(1)[0][0] if sentiment_counter else "neutral"
            
            all_keywords = []
            for news in news_analyses:
                keywords = news["analysis"].get("keywords", [])
                all_keywords.extend(keywords)
            top_keywords = [kw for kw, _ in Counter(all_keywords).most_common(5)]
            
            # Obtener sector más común
            sectors = [n["sector"].get("primary_sector") for n in news_analyses if n["sector"].get("primary_sector")]
            sector_counter = Counter(sectors)
            dominant_sector = sector_counter.most_common(1)[0][0] if sector_counter else None
            
            top_groups = [{
                "name": f"Noticias del día" if not dominant_sector else f"Sector: {dominant_sector}",
                "type": "generic",
                "news_list": news_analyses,
                "sector": dominant_sector,
                "sentiment": dominant_sentiment,
                "keywords": top_keywords,
                "score": len(news_analyses)
            }]
        
        # Convertir a formato de driver
        drivers = []
        for group in top_groups:
            news_ids = [n["id"] for n in group["news_list"] if n.get("id")]
            
            # Generar descripción
            description = self._generate_driver_description(group)
            
            drivers.append({
                "driver": group["name"],
                "description": description,
                "related_news_ids": news_ids,
                "keywords": group["keywords"],
                "sector": group["sector"],
                "sentiment": group["sentiment"],
                "news_count": len(news_ids)
            })
        
        return drivers
    
    def _generate_driver_description(self, group: Dict) -> str:
        """Genera una descripción del driver basada en el grupo."""
        news_list = group["news_list"]
        sector = group.get("sector")
        sentiment = group.get("sentiment")
        keywords = group.get("keywords", [])
        
        parts = []
        
        if sector:
            parts.append(f"Noticias del sector {sector}")
        
        if keywords:
            parts.append(f"relacionadas con {', '.join(keywords[:3])}")
        
        if sentiment == "positive":
            parts.append("con tendencia positiva")
        elif sentiment == "negative":
            parts.append("con tendencia negativa")
        
        description = ". ".join(parts) + "."
        
        # Agregar contexto adicional si hay muchas noticias
        if len(news_list) >= 5:
            description += f" Agrupa {len(news_list)} noticias relacionadas."
        
        return description
