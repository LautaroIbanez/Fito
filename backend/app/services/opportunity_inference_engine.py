"""Motor de inferencia: evento -> sectores -> tickers con puntuación de impacto."""
import logging
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from app.database import Sector, AssetCatalog
from app.models import NewsItemResponse, StandardizedNewsData
from app.services.sector_extraction_service import SectorExtractionService
from app.config import (
    OPPORTUNITIES_MIN_SCORE,
    OPPORTUNITIES_MIN_ASSETS_PER_NEWS,
    OPPORTUNITIES_MAX_ASSETS_PER_NEWS
)

logger = logging.getLogger(__name__)


class OpportunityInferenceEngine:
    """Motor de inferencia para generar oportunidades correlacionadas."""
    
    def __init__(self):
        """Inicializa el motor."""
        self.sector_extractor = SectorExtractionService()
    
    def infer_opportunities(
        self,
        db: Session,
        news_item: NewsItemResponse,
        standardized_data: Optional[StandardizedNewsData] = None
    ) -> List[Dict]:
        """
        Infiere oportunidades de activos fuera de cartera basadas en la noticia.
        
        Proceso:
        1. Extraer sectores/temas afectados
        2. Determinar impacto positivo/negativo
        3. Buscar activos en esos sectores
        4. Calcular puntuación de impacto
        5. Generar justificación
        
        Returns:
            List[Dict]: Lista de oportunidades con symbol, name, impact_score, signal, justification
        """
        # Paso 1: Extraer sectores y temas
        extraction_result = self.sector_extractor.extract_sectors_and_themes(
            news_item,
            standardized_data
        )
        
        sectors = extraction_result["sectors"]
        themes = extraction_result["themes"]
        
        if not sectors and not themes:
            logger.info(f"No se detectaron sectores/temas para noticia {news_item.id}")
            return []
        
        # Paso 2: Determinar señal (positiva/negativa)
        signal = self._determine_signal(news_item, standardized_data)
        
        # Paso 3: Buscar activos en sectores detectados
        opportunities = []
        
        # Buscar por sectores
        for sector_name in sectors:
            sector_assets = self._get_assets_by_sector(db, sector_name)
            sector_score = extraction_result["sector_scores"].get(sector_name, 0.5)
            
            for asset in sector_assets:
                impact_score = self._calculate_impact_score(
                    sector_score,
                    signal,
                    standardized_data
                )
                
                if impact_score >= OPPORTUNITIES_MIN_SCORE:
                    opportunity = {
                        "symbol": asset.symbol,
                        "name": asset.name,
                        "asset_type": asset.asset_type,
                        "sector": sector_name,
                        "is_etf": asset.is_etf,
                        "impact_score": impact_score,
                        "signal": signal,
                        "justification": self._generate_justification(
                            sector_name,
                            signal,
                            news_item,
                            standardized_data
                        )
                    }
                    opportunities.append(opportunity)
        
        # Buscar por temas (si hay ETFs temáticos)
        for theme_name in themes:
            theme_assets = self._get_assets_by_theme(db, theme_name)
            theme_score = extraction_result["theme_scores"].get(theme_name, 0.5)
            
            for asset in theme_assets:
                impact_score = self._calculate_impact_score(
                    theme_score,
                    signal,
                    standardized_data
                )
                
                if impact_score >= OPPORTUNITIES_MIN_SCORE:
                    opportunity = {
                        "symbol": asset.symbol,
                        "name": asset.name,
                        "asset_type": asset.asset_type,
                        "sector": theme_name,
                        "is_etf": asset.is_etf,
                        "impact_score": impact_score,
                        "signal": signal,
                        "justification": self._generate_justification(
                            theme_name,
                            signal,
                            news_item,
                            standardized_data
                        )
                    }
                    opportunities.append(opportunity)
        
        # Eliminar duplicados (mismo símbolo)
        seen_symbols = set()
        unique_opportunities = []
        for opp in opportunities:
            if opp["symbol"] not in seen_symbols:
                unique_opportunities.append(opp)
                seen_symbols.add(opp["symbol"])
        
        # Ordenar por impact_score descendente
        unique_opportunities.sort(key=lambda x: x["impact_score"], reverse=True)
        
        # Limitar cantidad
        max_assets = OPPORTUNITIES_MAX_ASSETS_PER_NEWS
        min_assets = OPPORTUNITIES_MIN_ASSETS_PER_NEWS
        
        if len(unique_opportunities) < min_assets:
            # Si no hay suficientes, agregar más genéricos del sector principal
            if sectors:
                additional = self._get_additional_assets(
                    db,
                    sectors[0],
                    min_assets - len(unique_opportunities),
                    seen_symbols
                )
                unique_opportunities.extend(additional)
        
        return unique_opportunities[:max_assets]
    
    def _determine_signal(
        self,
        news_item: NewsItemResponse,
        standardized_data: Optional[StandardizedNewsData] = None
    ) -> str:
        """Determina si la señal es positiva o negativa."""
        # Usar sentimiento estandarizado si está disponible
        if standardized_data and standardized_data.sentiment:
            sentiment = standardized_data.sentiment.lower()
            if sentiment == "bullish" or sentiment == "positive":
                return "positive"
            elif sentiment == "bearish" or sentiment == "negative":
                return "negative"
        
        # Fallback: analizar texto
        text = (news_item.title or "") + " " + news_item.body
        text_lower = text.lower()
        
        positive_words = ["crece", "aumenta", "sube", "positivo", "favorable", "ganancias", "éxito"]
        negative_words = ["cae", "baja", "negativo", "pérdida", "riesgo", "crisis"]
        
        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)
        
        if positive_count > negative_count:
            return "positive"
        elif negative_count > positive_count:
            return "negative"
        else:
            return "neutral"
    
    def _get_assets_by_sector(self, db: Session, sector_name: str) -> List[AssetCatalog]:
        """Obtiene activos de un sector específico."""
        sector = db.query(Sector).filter(Sector.name == sector_name).first()
        if not sector:
            return []
        
        assets = db.query(AssetCatalog).filter(AssetCatalog.sector_id == sector.id).all()
        return assets
    
    def _get_assets_by_theme(self, db: Session, theme_name: str) -> List[AssetCatalog]:
        """Obtiene activos relacionados con un tema."""
        # Por ahora, buscar por nombre de sector que coincida con tema
        # En producción, podrías tener una tabla de temas separada
        sector = db.query(Sector).filter(
            Sector.name.ilike(f"%{theme_name}%")
        ).first()
        
        if not sector:
            return []
        
        assets = db.query(AssetCatalog).filter(AssetCatalog.sector_id == sector.id).all()
        return assets
    
    def _calculate_impact_score(
        self,
        sector_score: float,
        signal: str,
        standardized_data: Optional[StandardizedNewsData] = None
    ) -> float:
        """
        Calcula puntuación de impacto (0.0 a 1.0).
        
        Factores:
        - Score del sector/tema detectado
        - Fuerza de la señal (positiva/negativa)
        - Relevancia de la noticia (si está estandarizada)
        """
        base_score = sector_score
        
        # Ajustar por señal
        if signal == "positive" or signal == "negative":
            base_score *= 1.2  # Señales claras aumentan score
        elif signal == "neutral":
            base_score *= 0.8  # Señales neutras reducen score
        
        # Limitar entre 0.0 y 1.0
        return min(1.0, max(0.0, base_score))
    
    def _generate_justification(
        self,
        sector_theme: str,
        signal: str,
        news_item: NewsItemResponse,
        standardized_data: Optional[StandardizedNewsData] = None
    ) -> str:
        """Genera justificación breve para la oportunidad."""
        signal_text = {
            "positive": "impacto positivo",
            "negative": "impacto negativo",
            "neutral": "impacto"
        }.get(signal, "impacto")
        
        justification = f"Noticia relacionada con {sector_theme} con {signal_text}. "
        
        if standardized_data and standardized_data.why_it_matters:
            # Usar el "why it matters" si está disponible
            why_matters = standardized_data.why_it_matters
            if len(why_matters) > 100:
                why_matters = why_matters[:97] + "..."
            justification += why_matters
        else:
            # Fallback genérico
            if signal == "positive":
                justification += "Oportunidad potencial identificada."
            elif signal == "negative":
                justification += "Riesgo potencial identificado."
            else:
                justification += "Monitorear evolución."
        
        return justification
    
    def _get_additional_assets(
        self,
        db: Session,
        sector_name: str,
        count: int,
        exclude_symbols: set
    ) -> List[Dict]:
        """Obtiene activos adicionales del sector para completar mínimo."""
        sector_assets = self._get_assets_by_sector(db, sector_name)
        
        additional = []
        for asset in sector_assets:
            if asset.symbol not in exclude_symbols and len(additional) < count:
                additional.append({
                    "symbol": asset.symbol,
                    "name": asset.name,
                    "asset_type": asset.asset_type,
                    "sector": sector_name,
                    "is_etf": asset.is_etf,
                    "impact_score": OPPORTUNITIES_MIN_SCORE,
                    "signal": "neutral",
                    "justification": f"Activo del sector {sector_name} relacionado con la noticia."
                })
        
        return additional



