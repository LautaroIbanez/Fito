"""Servicio para generar escenarios (base/riesgo/oportunidad) por driver usando GPT-4o."""
import logging
import json
from typing import List, Dict, Optional
from openai import OpenAI
from app.config import (
    OPENAI_API_KEY,
    OPENAI_MODEL,
    OPENAI_TEMPERATURE
)
from app.models import (
    Scenario,
    ScenarioAssumption,
    ScenarioRisk,
    ScenarioInvalidator
)

logger = logging.getLogger(__name__)


class ScenarioGenerationService:
    """Servicio para generar escenarios por driver usando GPT-4o."""
    
    def __init__(self):
        """Inicializa el cliente de OpenAI."""
        if not OPENAI_API_KEY or OPENAI_API_KEY == "your_openai_api_key_here":
            raise ValueError("OPENAI_API_KEY no está configurada correctamente en app/config.py")
        
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        self.model = OPENAI_MODEL
        self.temperature = OPENAI_TEMPERATURE
    
    def generate_scenarios(
        self, 
        driver: Dict,
        related_news_items: List[Dict]
    ) -> Dict[str, Scenario]:
        """
        Genera escenarios (base, riesgo, oportunidad) para un driver.
        
        Args:
            driver: Diccionario con información del driver (driver, description, related_news_ids)
            related_news_items: Lista de noticias relacionadas al driver
            
        Returns:
            Diccionario con escenarios: {"base": Scenario, "risk": Scenario, "opportunity": Scenario}
        """
        if not related_news_items:
            logger.warning(f"No hay noticias relacionadas para el driver '{driver.get('driver', 'unknown')}'")
            return {}
        
        try:
            prompt = self._build_scenario_generation_prompt(driver, related_news_items)
            
            logger.info(
                f"Generando escenarios para driver '{driver.get('driver')}': "
                f"{len(related_news_items)} noticias relacionadas"
            )
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Eres un estratega financiero experto especializado en generación de escenarios. "
                            "Generas escenarios realistas basados en datos y noticias del mercado. "
                            "Cada escenario incluye supuestos claros, riesgos identificados e invalidadores. "
                            "Eres preciso, evitas especulación sin fundamento, y siempre basas tus escenarios "
                            "en la información proporcionada."
                        )
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=self.temperature,
                response_format={"type": "json_object"},
                timeout=90.0
            )
            
            response_text = response.choices[0].message.content
            scenarios_dict = json.loads(response_text)
            
            # Validar y estructurar los escenarios
            scenarios = self._validate_and_structure_scenarios(scenarios_dict)
            
            logger.info(f"Escenarios generados exitosamente para driver '{driver.get('driver')}'")
            return scenarios
            
        except json.JSONDecodeError as e:
            logger.error(f"Error parseando JSON de respuesta de OpenAI: {e}")
            raise ValueError(f"Error procesando respuesta de OpenAI: formato JSON inválido")
        except Exception as e:
            error_str = str(e)
            logger.error(f"Error generando escenarios: {e}", exc_info=True)
            
            if "401" in error_str or "invalid_api_key" in error_str:
                raise ValueError(
                    "Error de autenticación con OpenAI. Verifica tu API key en app/config.py"
                )
            elif "429" in error_str or "rate_limit" in error_str:
                raise ValueError("Límite de tasa excedido. Por favor, intenta más tarde.")
            elif "insufficient_quota" in error_str:
                raise ValueError("Cuota de OpenAI agotada. Verifica tu cuenta.")
            else:
                raise ValueError(f"Error al generar escenarios: {error_str}")
    
    def _build_scenario_generation_prompt(self, driver: Dict, related_news_items: List[Dict]) -> str:
        """Construye el prompt para generación de escenarios."""
        driver_name = driver.get("driver", "Unknown")
        driver_description = driver.get("description", "")
        
        news_summaries = []
        for news in related_news_items:
            standardized_data = news.get("standardized_data", {})
            news_summaries.append({
                "summary": standardized_data.get("summary", ""),
                "sentiment": standardized_data.get("sentiment", "neutral"),
                "tickers": standardized_data.get("tickers", []),
                "categories": standardized_data.get("categories", [])
            })
        
        prompt = f"""Genera tres escenarios para el siguiente driver temático del mercado:

DRIVER: {driver_name}
DESCRIPCIÓN: {driver_description}

NOTICIAS RELACIONADAS:
{json.dumps(news_summaries, indent=2, ensure_ascii=False)}

Genera tres tipos de escenarios:

1. BASE (escenario base): El escenario más probable basado en las noticias actuales
2. RISK (escenario de riesgo): Un escenario negativo que podría materializarse
3. OPPORTUNITY (escenario de oportunidad): Un escenario positivo que podría materializarse

Para cada escenario, proporciona:
- title: Título conciso del escenario
- description: Descripción detallada (2-3 párrafos)
- assumptions: Lista de supuestos clave (mínimo 2, máximo 5)
- risks: Lista de riesgos asociados (mínimo 1, máximo 3)
- invalidators: Lista de condiciones que invalidarían el escenario (mínimo 1, máximo 3)
- confidence: Nivel de confianza (0.0-1.0)
- timeframe: Horizonte temporal estimado (ej: "3-6 meses", "1-2 semanas")
- market_impact: Impacto esperado en el mercado (1-2 oraciones breves, ej: "Caída del 5-10% en tech stocks")
- suggested_actions: Lista de acciones sugeridas (2-3 items, ej: ["Reducir exposición a tech", "Aumentar hedges con puts", "Monitorear indicadores técnicos"])
- triggers: Lista de eventos o condiciones trigger a monitorear (2-3 items, ej: ["FOMC statement del 15/03", "CPI release de marzo", "Earnings de AAPL"])

Responde en formato JSON con esta estructura:
{{
    "base": {{
        "title": "Título del escenario base",
        "description": "Descripción detallada...",
        "assumptions": [
            {{"description": "Supuesto 1", "probability": 0.7, "timeframe": "3 meses"}}
        ],
        "risks": [
            {{"description": "Riesgo 1", "severity": "medium", "mitigation": "Estrategia de mitigación"}}
        ],
        "invalidators": [
            {{"condition": "Condición que invalida", "description": "Por qué invalida"}}
        ],
        "confidence": 0.75,
        "timeframe": "3-6 meses",
        "market_impact": "Impacto esperado en el mercado...",
        "suggested_actions": ["Acción 1", "Acción 2"],
        "triggers": ["Evento 1", "Evento 2"]
    }},
    "risk": {{
        "title": "Título del escenario de riesgo",
        "description": "Descripción detallada...",
        "assumptions": [...],
        "risks": [...],
        "invalidators": [...],
        "confidence": 0.65,
        "timeframe": "1-3 meses",
        "market_impact": "Impacto esperado en el mercado...",
        "suggested_actions": ["Acción 1", "Acción 2"],
        "triggers": ["Evento 1", "Evento 2"]
    }},
    "opportunity": {{
        "title": "Título del escenario de oportunidad",
        "description": "Descripción detallada...",
        "assumptions": [...],
        "risks": [...],
        "invalidators": [...],
        "confidence": 0.60,
        "timeframe": "6-12 meses"
    }}
}}
"""
        return prompt
    
    def _validate_and_structure_scenarios(self, scenarios_dict: Dict) -> Dict[str, Scenario]:
        """Valida y estructura los escenarios generados."""
        scenarios = {}
        
        scenario_types = ["base", "risk", "opportunity"]
        
        for scenario_type in scenario_types:
            if scenario_type not in scenarios_dict:
                logger.warning(f"Escenario '{scenario_type}' no encontrado en respuesta")
                continue
            
            scenario_data = scenarios_dict[scenario_type]
            
            try:
                # Validar campos requeridos
                if not scenario_data.get("title") or not scenario_data.get("description"):
                    logger.warning(f"Escenario '{scenario_type}' incompleto, omitiendo")
                    continue
                
                # Procesar assumptions
                assumptions = []
                for assumption_data in scenario_data.get("assumptions", []):
                    assumptions.append(ScenarioAssumption(
                        description=assumption_data.get("description", ""),
                        probability=assumption_data.get("probability"),
                        timeframe=assumption_data.get("timeframe")
                    ))
                
                # Procesar risks
                risks = []
                for risk_data in scenario_data.get("risks", []):
                    risks.append(ScenarioRisk(
                        description=risk_data.get("description", ""),
                        severity=risk_data.get("severity", "medium").lower(),
                        mitigation=risk_data.get("mitigation")
                    ))
                
                # Procesar invalidators
                invalidators = []
                for inv_data in scenario_data.get("invalidators", []):
                    invalidators.append(ScenarioInvalidator(
                        condition=inv_data.get("condition", ""),
                        description=inv_data.get("description", "")
                    ))
                
                # Procesar market_impact, suggested_actions, triggers
                market_impact = scenario_data.get("market_impact")
                suggested_actions = scenario_data.get("suggested_actions", [])
                triggers = scenario_data.get("triggers", [])
                
                # Validar que suggested_actions y triggers sean listas
                if not isinstance(suggested_actions, list):
                    suggested_actions = []
                if not isinstance(triggers, list):
                    triggers = []
                
                # Crear Scenario
                scenario = Scenario(
                    scenario_type=scenario_type,
                    title=scenario_data.get("title", ""),
                    description=scenario_data.get("description", ""),
                    assumptions=assumptions,
                    risks=risks,
                    invalidators=invalidators,
                    confidence=max(0.0, min(1.0, scenario_data.get("confidence", 0.5))),
                    timeframe=scenario_data.get("timeframe"),
                    market_impact=market_impact,
                    suggested_actions=suggested_actions,
                    triggers=triggers
                )
                
                scenarios[scenario_type] = scenario
                
            except Exception as e:
                logger.error(f"Error procesando escenario '{scenario_type}': {e}", exc_info=True)
                continue
        
        return scenarios

