"""Generador de escenarios usando plantillas 'si-entonces' basadas en sentimiento, sector y señales."""
import logging
from typing import List, Dict, Optional
from app.models import Scenario, ScenarioAssumption, ScenarioRisk, ScenarioInvalidator
from app.services.local_nlp import get_local_nlp_service
from app.services.sentiment_service import get_sentiment_service

logger = logging.getLogger(__name__)


class TemplateScenarioGenerator:
    """Genera escenarios usando plantillas 'si-entonces' sin LLM."""
    
    def __init__(self):
        """Inicializa los servicios de NLP local."""
        self.nlp_service = get_local_nlp_service()
        self.sentiment_service = get_sentiment_service()
        logger.info("TemplateScenarioGenerator inicializado (sin LLM)")
    
    def generate_scenarios(
        self,
        driver: Dict,
        related_news_items: List[Dict]
    ) -> Dict[str, Scenario]:
        """
        Genera escenarios (base, riesgo, oportunidad) para un driver usando plantillas.
        
        Args:
            driver: Diccionario con información del driver (driver, description, sentiment, sector, keywords)
            related_news_items: Lista de noticias relacionadas
        
        Returns:
            Diccionario con escenarios: {"base": Scenario, "risk": Scenario, "opportunity": Scenario}
        """
        if not related_news_items:
            logger.warning(f"No hay noticias relacionadas para el driver '{driver.get('driver', 'unknown')}'")
            return {}
        
        driver_name = driver.get("driver", "Unknown")
        driver_sentiment = driver.get("sentiment", "neutral")
        driver_sector = driver.get("sector")
        driver_keywords = driver.get("keywords", [])
        
        logger.info(
            f"Generando escenarios para driver '{driver_name}': "
            f"{len(related_news_items)} noticias, sentiment={driver_sentiment}, sector={driver_sector}"
        )
        
        # Analizar noticias relacionadas para extraer señales
        signals = self._extract_signals(related_news_items)
        
        # Generar escenario base
        base_scenario = self._generate_base_scenario(driver, signals)
        
        # Generar escenario de riesgo
        risk_scenario = self._generate_risk_scenario(driver, signals)
        
        # Generar escenario de oportunidad
        opportunity_scenario = self._generate_opportunity_scenario(driver, signals)
        
        scenarios = {}
        if base_scenario:
            scenarios["base"] = base_scenario
        if risk_scenario:
            scenarios["risk"] = risk_scenario
        if opportunity_scenario:
            scenarios["opportunity"] = opportunity_scenario
        
        logger.info(f"[MOTOR LOCAL] Escenarios generados para driver '{driver_name}': {list(scenarios.keys())} (plantillas locales, sin LLM)")
        
        return scenarios
    
    def _extract_signals(self, news_items: List[Dict]) -> Dict:
        """Extrae señales de riesgo/oportunidad de las noticias."""
        risk_signals = []
        opportunity_signals = []
        metrics = []
        entities = []
        
        for item in news_items:
            text = item.get("body") or item.get("text") or item.get("title", "")
            if not text:
                continue
            
            # Analizar con NLP local
            analysis = self.nlp_service.analyze_news(text)
            sentiment_result = self.sentiment_service.analyze_sentiment(text, item.get("title"))
            
            # Extraer entidades
            news_entities = analysis.get("entities", {})
            entities.extend(news_entities.get("ORG", []))
            entities.extend(news_entities.get("PERSON", []))
            
            # Extraer métricas (números)
            import re
            numbers = re.findall(r'\d+[.,]?\d*[%$BMK]?', text)
            metrics.extend(numbers[:3])  # Limitar a 3 por noticia
            
            # Clasificar señales según sentimiento
            sentiment = sentiment_result["sentiment"]
            if sentiment == "negative":
                risk_signals.append({
                    "text": text[:200],  # Primeros 200 caracteres
                    "sentiment": sentiment,
                    "confidence": sentiment_result["confidence"]
                })
            elif sentiment == "positive":
                opportunity_signals.append({
                    "text": text[:200],
                    "sentiment": sentiment,
                    "confidence": sentiment_result["confidence"]
                })
        
        return {
            "risk_signals": risk_signals[:5],  # Top 5
            "opportunity_signals": opportunity_signals[:5],  # Top 5
            "metrics": list(set(metrics))[:10],  # Únicos, top 10
            "entities": list(set(entities))[:10]  # Únicos, top 10
        }
    
    def _generate_base_scenario(self, driver: Dict, signals: Dict) -> Optional[Scenario]:
        """Genera escenario base usando plantilla."""
        driver_name = driver.get("driver", "Unknown")
        driver_sentiment = driver.get("sentiment", "neutral")
        driver_sector = driver.get("sector")
        driver_keywords = driver.get("keywords", [])
        
        # Construir descripción base
        description_parts = []
        description_parts.append(f"El driver '{driver_name}' agrupa noticias relacionadas.")
        
        if driver_sector:
            description_parts.append(f"El sector principal es {driver_sector}.")
        
        if driver_sentiment == "positive":
            description_parts.append("Las noticias muestran una tendencia positiva.")
        elif driver_sentiment == "negative":
            description_parts.append("Las noticias muestran una tendencia negativa.")
        else:
            description_parts.append("Las noticias muestran una tendencia neutral.")
        
        if driver_keywords:
            description_parts.append(f"Términos clave: {', '.join(driver_keywords[:3])}.")
        
        description = " ".join(description_parts)
        
        # Generar supuestos
        assumptions = []
        if driver_sector:
            assumptions.append(ScenarioAssumption(
                description=f"El sector {driver_sector} mantiene su tendencia actual",
                probability=0.7,
                timeframe="3-6 meses"
            ))
        
        if driver_sentiment != "neutral":
            assumptions.append(ScenarioAssumption(
                description=f"El sentimiento {driver_sentiment} se mantiene o se intensifica",
                probability=0.6,
                timeframe="1-3 meses"
            ))
        
        # Generar supuesto adicional si hay métricas
        if signals.get("metrics"):
            assumptions.append(ScenarioAssumption(
                description="Las métricas reportadas reflejan tendencias sostenibles",
                probability=0.65,
                timeframe="2-4 meses"
            ))
        
        # Generar riesgos
        risks = []
        if driver_sentiment == "positive":
            risks.append(ScenarioRisk(
                description="Posible corrección si las expectativas no se cumplen",
                severity="medium",
                mitigation="Monitorear indicadores clave y establecer stop-loss"
            ))
        elif driver_sentiment == "negative":
            risks.append(ScenarioRisk(
                description="Posible intensificación de la tendencia negativa",
                severity="high",
                mitigation="Considerar posiciones defensivas o hedges"
            ))
        
        # Generar invalidadores
        invalidators = []
        if driver_sector:
            invalidators.append(ScenarioInvalidator(
                condition=f"Cambio estructural en el sector {driver_sector}",
                description="Un cambio regulatorio o tecnológico podría invalidar el escenario"
            ))
        
        invalidators.append(ScenarioInvalidator(
            condition="Cambio de sentimiento dominante",
            description="Si el sentimiento cambia significativamente, el escenario base se invalida"
        ))
        
        # Calcular confianza
        confidence = 0.65  # Base
        if len(assumptions) >= 2:
            confidence += 0.1
        if driver_sector:
            confidence += 0.05
        
        confidence = min(confidence, 0.85)  # Máximo 0.85
        
        # Impacto en mercado
        market_impact = f"Impacto moderado en {driver_sector if driver_sector else 'el mercado'}. "
        if driver_sentiment == "positive":
            market_impact += "Tendencia alcista esperada."
        elif driver_sentiment == "negative":
            market_impact += "Tendencia bajista esperada."
        else:
            market_impact += "Movimientos laterales esperados."
        
        # Acciones sugeridas
        suggested_actions = []
        if driver_sentiment == "positive":
            suggested_actions.append("Considerar posiciones largas en activos del sector")
            suggested_actions.append("Monitorear indicadores técnicos para entrada")
        elif driver_sentiment == "negative":
            suggested_actions.append("Considerar posiciones defensivas o reducción de exposición")
            suggested_actions.append("Evaluar hedges apropiados")
        else:
            suggested_actions.append("Mantener posición neutral y monitorear desarrollo")
        
        # Triggers
        triggers = []
        if driver_sector:
            triggers.append(f"Reportes de resultados del sector {driver_sector}")
        triggers.append("Indicadores macroeconómicos relevantes")
        triggers.append("Cambios en políticas regulatorias")
        
        return Scenario(
            scenario_type="base",
            title=f"Escenario Base: {driver_name}",
            description=description,
            assumptions=assumptions,
            risks=risks,
            invalidators=invalidators,
            confidence=round(confidence, 2),
            timeframe="3-6 meses",
            market_impact=market_impact,
            suggested_actions=suggested_actions,
            triggers=triggers
        )
    
    def _generate_risk_scenario(self, driver: Dict, signals: Dict) -> Optional[Scenario]:
        """Genera escenario de riesgo usando plantilla."""
        driver_name = driver.get("driver", "Unknown")
        driver_sentiment = driver.get("sentiment", "neutral")
        driver_sector = driver.get("sector")
        risk_signals = signals.get("risk_signals", [])
        
        if not risk_signals and driver_sentiment != "negative":
            # Solo generar si hay señales de riesgo o sentimiento negativo
            return None
        
        description_parts = []
        description_parts.append(f"Escenario de riesgo para '{driver_name}':")
        description_parts.append("Las condiciones actuales podrían deteriorarse significativamente.")
        
        if driver_sector:
            description_parts.append(f"El sector {driver_sector} podría enfrentar presiones adicionales.")
        
        if risk_signals:
            description_parts.append(f"Se identificaron {len(risk_signals)} señales de riesgo en las noticias.")
        
        description = " ".join(description_parts)
        
        # Supuestos
        assumptions = [
            ScenarioAssumption(
                description="Las condiciones adversas se intensifican",
                probability=0.4,
                timeframe="1-3 meses"
            )
        ]
        
        if driver_sector:
            assumptions.append(ScenarioAssumption(
                description=f"El sector {driver_sector} enfrenta desafíos estructurales",
                probability=0.35,
                timeframe="2-4 meses"
            ))
        
        # Riesgos
        risks = [
            ScenarioRisk(
                description="Pérdidas significativas en posiciones expuestas",
                severity="high",
                mitigation="Reducir exposición y establecer hedges"
            ),
            ScenarioRisk(
                description="Correlación negativa entre activos relacionados",
                severity="medium",
                mitigation="Diversificar y evitar concentración"
            )
        ]
        
        # Invalidadores
        invalidators = [
            ScenarioInvalidator(
                condition="Mejora inesperada en condiciones fundamentales",
                description="Si los indicadores mejoran, el escenario de riesgo se invalida"
            )
        ]
        
        confidence = 0.55  # Menor confianza para escenarios de riesgo
        
        market_impact = f"Impacto negativo significativo en {driver_sector if driver_sector else 'el mercado'}. "
        market_impact += "Posible corrección o tendencia bajista."
        
        suggested_actions = [
            "Reducir exposición a activos relacionados",
            "Considerar posiciones cortas o hedges",
            "Aumentar liquidez y posiciones defensivas"
        ]
        
        triggers = [
            "Indicadores económicos negativos",
            "Eventos geopolíticos adversos",
            "Cambios regulatorios restrictivos"
        ]
        
        return Scenario(
            scenario_type="risk",
            title=f"Escenario de Riesgo: {driver_name}",
            description=description,
            assumptions=assumptions,
            risks=risks,
            invalidators=invalidators,
            confidence=confidence,
            timeframe="1-3 meses",
            market_impact=market_impact,
            suggested_actions=suggested_actions,
            triggers=triggers
        )
    
    def _generate_opportunity_scenario(self, driver: Dict, signals: Dict) -> Optional[Scenario]:
        """Genera escenario de oportunidad usando plantilla."""
        driver_name = driver.get("driver", "Unknown")
        driver_sentiment = driver.get("sentiment", "neutral")
        driver_sector = driver.get("sector")
        opportunity_signals = signals.get("opportunity_signals", [])
        
        if not opportunity_signals and driver_sentiment != "positive":
            # Solo generar si hay señales de oportunidad o sentimiento positivo
            return None
        
        description_parts = []
        description_parts.append(f"Escenario de oportunidad para '{driver_name}':")
        description_parts.append("Las condiciones actuales podrían mejorar significativamente.")
        
        if driver_sector:
            description_parts.append(f"El sector {driver_sector} podría experimentar crecimiento.")
        
        if opportunity_signals:
            description_parts.append(f"Se identificaron {len(opportunity_signals)} señales de oportunidad en las noticias.")
        
        description = " ".join(description_parts)
        
        # Supuestos
        assumptions = [
            ScenarioAssumption(
                description="Las condiciones favorables se intensifican",
                probability=0.4,
                timeframe="2-6 meses"
            )
        ]
        
        if driver_sector:
            assumptions.append(ScenarioAssumption(
                description=f"El sector {driver_sector} experimenta crecimiento sostenido",
                probability=0.35,
                timeframe="3-6 meses"
            ))
        
        # Riesgos (incluso en oportunidades hay riesgos)
        risks = [
            ScenarioRisk(
                description="Sobrevaluación si el crecimiento no se materializa",
                severity="medium",
                mitigation="Monitorear valuaciones y establecer objetivos de precio"
            )
        ]
        
        # Invalidadores
        invalidators = [
            ScenarioInvalidator(
                condition="Deterioro inesperado en condiciones fundamentales",
                description="Si los indicadores empeoran, el escenario de oportunidad se invalida"
            )
        ]
        
        confidence = 0.55  # Menor confianza para escenarios de oportunidad
        
        market_impact = f"Impacto positivo significativo en {driver_sector if driver_sector else 'el mercado'}. "
        market_impact += "Posible tendencia alcista o rally."
        
        suggested_actions = [
            "Considerar posiciones largas en activos relacionados",
            "Aumentar exposición gradualmente",
            "Monitorear indicadores técnicos para confirmación"
        ]
        
        triggers = [
            "Indicadores económicos positivos",
            "Anuncios de crecimiento o expansión",
            "Cambios regulatorios favorables"
        ]
        
        return Scenario(
            scenario_type="opportunity",
            title=f"Escenario de Oportunidad: {driver_name}",
            description=description,
            assumptions=assumptions,
            risks=risks,
            invalidators=invalidators,
            confidence=confidence,
            timeframe="2-6 meses",
            market_impact=market_impact,
            suggested_actions=suggested_actions,
            triggers=triggers
        )
