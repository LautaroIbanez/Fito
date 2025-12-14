"""Mapeo de escenarios a cartera usando coincidencia de tickers/nombres y reglas simples."""
import logging
import re
from typing import List, Dict, Optional
from app.models import PortfolioAssetMapping

logger = logging.getLogger(__name__)


class RuleBasedPortfolioMapper:
    """Mapea escenarios a activos de la cartera usando reglas y coincidencias."""
    
    def __init__(self):
        """Inicializa el mapeador."""
        logger.info("RuleBasedPortfolioMapper inicializado (sin LLM)")
    
    def map_scenarios_to_portfolio(
        self,
        driver: Dict,
        scenarios: Dict,
        portfolio_items: List[Dict],
        related_news_items: List[Dict]
    ) -> List[PortfolioAssetMapping]:
        """
        Mapea escenarios a activos de la cartera usando coincidencias de tickers/nombres.
        
        Args:
            driver: Diccionario con información del driver (sector, keywords)
            scenarios: Diccionario con escenarios (base, risk, opportunity)
            portfolio_items: Lista de items de cartera (name, symbol, asset_type)
            related_news_items: Lista de noticias relacionadas (para extraer tickers mencionados)
        
        Returns:
            Lista de PortfolioAssetMapping con mapeos identificados
        """
        if not portfolio_items:
            logger.warning("No hay items de cartera para mapear")
            return []
        
        if not scenarios:
            logger.warning("No hay escenarios para mapear")
            return []
        
        logger.info(
            f"Mapeando escenarios a cartera para driver '{driver.get('driver')}': "
            f"{len(portfolio_items)} items de cartera, {len(scenarios)} escenarios"
        )
        
        mappings = []
        
        # Extraer tickers y nombres mencionados en las noticias
        mentioned_tickers, mentioned_names = self._extract_mentioned_assets(related_news_items)
        
        # Mapear por ticker directo
        ticker_mappings = self._map_by_ticker(
            portfolio_items,
            mentioned_tickers,
            driver,
            scenarios
        )
        mappings.extend(ticker_mappings)
        
        # Mapear por nombre/alias
        name_mappings = self._map_by_name(
            portfolio_items,
            mentioned_names,
            driver,
            scenarios
        )
        mappings.extend(name_mappings)
        
        # Mapear por sector
        sector_mappings = self._map_by_sector(
            portfolio_items,
            driver,
            scenarios
        )
        mappings.extend(sector_mappings)
        
        # Eliminar duplicados (mismo asset_type + identifier)
        unique_mappings = self._deduplicate_mappings(mappings)
        
        logger.info(f"[MOTOR LOCAL] Mapeo completado: {len(unique_mappings)} activos identificados (reglas locales, sin LLM)")
        
        return unique_mappings
    
    def _extract_mentioned_assets(self, news_items: List[Dict]) -> tuple:
        """Extrae tickers y nombres de activos mencionados en las noticias."""
        tickers = set()
        names = set()
        
        # Patrones para detectar tickers
        ticker_pattern = r'\b([A-Z]{1,5}(?:\.[A-Z]{1,3})?)\b'  # Ej: AAPL, AAPL.US, GGAL.BA
        
        for item in news_items:
            text = item.get("body") or item.get("text") or item.get("title", "")
            if not text:
                continue
            
            # Buscar tickers con patrón
            found_tickers = re.findall(ticker_pattern, text)
            tickers.update([t.upper() for t in found_tickers if len(t) >= 2])
            
            # Extraer nombres de empresas comunes (de entidades ORG)
            # Esto se puede mejorar con un diccionario de aliases
            # Por ahora, buscamos nombres comunes en mayúsculas
            org_pattern = r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b'
            found_orgs = re.findall(org_pattern, text)
            # Filtrar nombres muy cortos o muy largos
            names.update([n for n in found_orgs if 3 <= len(n) <= 50])
        
        return list(tickers), list(names)
    
    def _map_by_ticker(
        self,
        portfolio_items: List[Dict],
        mentioned_tickers: List[str],
        driver: Dict,
        scenarios: Dict
    ) -> List[PortfolioAssetMapping]:
        """Mapea activos por coincidencia directa de ticker."""
        mappings = []
        
        for item in portfolio_items:
            symbol = item.get("symbol", "").upper()
            if not symbol:
                continue
            
            # Verificar si el ticker está mencionado
            if symbol in mentioned_tickers or any(symbol.startswith(t) or t.startswith(symbol) for t in mentioned_tickers):
                # Calcular sensibilidad basada en sentimiento del driver
                driver_sentiment = driver.get("sentiment", "neutral")
                sensitivity = self._calculate_sensitivity(driver_sentiment, scenarios)
                
                # Calcular confianza
                confidence = 0.8  # Alta confianza para coincidencia directa
                
                # Descripción de impacto
                impact_description = self._generate_impact_description(
                    item,
                    driver,
                    scenarios,
                    "ticker"
                )
                
                mappings.append(PortfolioAssetMapping(
                    asset_type="ticker",
                    identifier=symbol,
                    name=item.get("name"),
                    sensitivity=sensitivity,
                    confidence=confidence,
                    impact_description=impact_description
                ))
        
        return mappings
    
    def _map_by_name(
        self,
        portfolio_items: List[Dict],
        mentioned_names: List[str],
        driver: Dict,
        scenarios: Dict
    ) -> List[PortfolioAssetMapping]:
        """Mapea activos por coincidencia de nombre/alias."""
        mappings = []
        
        for item in portfolio_items:
            name = item.get("name", "").upper()
            if not name:
                continue
            
            # Verificar coincidencias parciales
            for mentioned_name in mentioned_names:
                mentioned_upper = mentioned_name.upper()
                
                # Coincidencia exacta o parcial significativa
                if (mentioned_upper in name or name in mentioned_upper or
                    self._similarity_score(name, mentioned_upper) > 0.7):
                    
                    # Evitar duplicados (ya mapeado por ticker)
                    symbol = item.get("symbol", "").upper()
                    if any(m.identifier == symbol for m in mappings):
                        continue
                    
                    driver_sentiment = driver.get("sentiment", "neutral")
                    sensitivity = self._calculate_sensitivity(driver_sentiment, scenarios)
                    confidence = 0.6  # Media confianza para coincidencia por nombre
                    
                    impact_description = self._generate_impact_description(
                        item,
                        driver,
                        scenarios,
                        "name"
                    )
                    
                    mappings.append(PortfolioAssetMapping(
                        asset_type="ticker",
                        identifier=symbol or name,
                        name=item.get("name"),
                        sensitivity=sensitivity,
                        confidence=confidence,
                        impact_description=impact_description
                    ))
                    break  # Solo una coincidencia por item
        
        return mappings
    
    def _map_by_sector(
        self,
        portfolio_items: List[Dict],
        driver: Dict,
        scenarios: Dict
    ) -> List[PortfolioAssetMapping]:
        """Mapea activos por sector del driver."""
        mappings = []
        driver_sector = driver.get("sector")
        
        if not driver_sector:
            return mappings
        
        # Mapeo de sectores (simplificado, se puede expandir)
        sector_mapping = {
            "tecnología": ["TECH", "TECHNOLOGY", "SOFTWARE", "HARDWARE"],
            "finanzas": ["FINANCE", "BANKING", "FINANCIAL"],
            "energía": ["ENERGY", "OIL", "GAS"],
            "salud": ["HEALTH", "PHARMA", "BIOTECH"],
            "consumo": ["CONSUMER", "RETAIL"],
            "industria": ["INDUSTRIAL", "MANUFACTURING"],
            "telecomunicaciones": ["TELECOM", "TELECOMMUNICATIONS"],
            "bienes raíces": ["REAL_ESTATE", "REALTY"]
        }
        
        # Buscar items de cartera que coincidan con el sector
        # (esto requeriría que los items tengan campo de sector, por ahora es simplificado)
        # Por ahora, mapeamos todos los items con sensibilidad menor
        
        driver_sentiment = driver.get("sentiment", "neutral")
        sensitivity = self._calculate_sensitivity(driver_sentiment, scenarios) * 0.5  # Menor sensibilidad para sector
        
        for item in portfolio_items:
            # Evitar duplicados (ya mapeado por ticker o nombre)
            symbol = item.get("symbol", "").upper()
            if any(m.identifier == symbol for m in mappings):
                continue
            
            # Por ahora, solo mapeamos si no hay mapeo directo previo
            # En una implementación completa, se verificaría el sector del item
            
            confidence = 0.4  # Baja confianza para mapeo por sector genérico
            
            impact_description = f"Impacto indirecto a través del sector {driver_sector}"
            
            mappings.append(PortfolioAssetMapping(
                asset_type="sector",
                identifier=driver_sector,
                name=item.get("name"),
                sensitivity=sensitivity,
                confidence=confidence,
                impact_description=impact_description
            ))
        
        return mappings[:5]  # Limitar a 5 mapeos por sector para evitar sobrecarga
    
    def _calculate_sensitivity(self, sentiment: str, scenarios: Dict) -> float:
        """Calcula sensibilidad basada en sentimiento y escenarios."""
        base_sensitivity = 0.0
        
        if sentiment == "positive":
            base_sensitivity = 0.6
        elif sentiment == "negative":
            base_sensitivity = -0.6
        else:
            base_sensitivity = 0.0
        
        # Ajustar según escenarios
        if "risk" in scenarios:
            base_sensitivity -= 0.2  # Más negativo si hay escenario de riesgo
        if "opportunity" in scenarios:
            base_sensitivity += 0.2  # Más positivo si hay escenario de oportunidad
        
        # Limitar a rango [-1.0, 1.0]
        return max(-1.0, min(1.0, base_sensitivity))
    
    def _generate_impact_description(
        self,
        item: Dict,
        driver: Dict,
        scenarios: Dict,
        match_type: str
    ) -> str:
        """Genera descripción del impacto esperado."""
        driver_name = driver.get("driver", "driver")
        driver_sentiment = driver.get("sentiment", "neutral")
        
        parts = []
        parts.append(f"Activo identificado por coincidencia de {match_type}.")
        
        if driver_sentiment == "positive":
            parts.append("Impacto positivo esperado según el driver.")
        elif driver_sentiment == "negative":
            parts.append("Impacto negativo esperado según el driver.")
        
        if "risk" in scenarios:
            parts.append("Atención a escenarios de riesgo.")
        if "opportunity" in scenarios:
            parts.append("Posible oportunidad identificada.")
        
        return " ".join(parts)
    
    def _similarity_score(self, str1: str, str2: str) -> float:
        """Calcula similitud simple entre dos strings (Jaccard)."""
        words1 = set(str1.split())
        words2 = set(str2.split())
        
        if not words1 and not words2:
            return 1.0
        if not words1 or not words2:
            return 0.0
        
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        
        return intersection / union if union > 0 else 0.0
    
    def _deduplicate_mappings(self, mappings: List[PortfolioAssetMapping]) -> List[PortfolioAssetMapping]:
        """Elimina mapeos duplicados (mismo asset_type + identifier)."""
        seen = set()
        unique = []
        
        for mapping in mappings:
            key = (mapping.asset_type, mapping.identifier)
            if key not in seen:
                seen.add(key)
                unique.append(mapping)
        
        return unique
