"""Servicio para mapear escenarios a activos de la cartera (tickers/sectores/FX)."""
import logging
import json
from typing import List, Dict, Set
from openai import OpenAI
from app.config import (
    OPENAI_API_KEY,
    OPENAI_MODEL,
    OPENAI_TEMPERATURE
)
from app.models import PortfolioAssetMapping

logger = logging.getLogger(__name__)


class ScenarioPortfolioMappingService:
    """Servicio para mapear escenarios a activos de la cartera."""
    
    def __init__(self):
        """Inicializa el cliente de OpenAI."""
        if not OPENAI_API_KEY or OPENAI_API_KEY == "your_openai_api_key_here":
            raise ValueError("OPENAI_API_KEY no está configurada correctamente en app/config.py")
        
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        self.model = OPENAI_MODEL
        self.temperature = OPENAI_TEMPERATURE
    
    def map_scenarios_to_portfolio(
        self,
        driver: Dict,
        scenarios: Dict,
        portfolio_items: List[Dict]
    ) -> List[PortfolioAssetMapping]:
        """
        Mapea escenarios a activos de la cartera.
        
        Args:
            driver: Diccionario con información del driver
            scenarios: Diccionario con escenarios (base, risk, opportunity)
            portfolio_items: Lista de items de cartera
            
        Returns:
            Lista de PortfolioAssetMapping con mapeos a tickers, sectores y FX
        """
        if not portfolio_items:
            logger.warning("No hay items de cartera para mapear")
            return []
        
        if not scenarios:
            logger.warning("No hay escenarios para mapear")
            return []
        
        try:
            prompt = self._build_mapping_prompt(driver, scenarios, portfolio_items)
            
            logger.info(
                f"Mapeando escenarios a cartera para driver '{driver.get('driver')}': "
                f"{len(portfolio_items)} items de cartera"
            )
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Eres un analista de cartera experto especializado en mapear escenarios de mercado "
                            "a activos específicos. Identificas qué tickers, sectores y pares FX serían afectados "
                            "por cada escenario y estimas la sensibilidad y confianza del impacto. "
                            "Eres preciso y basas tus mapeos en relaciones fundamentales claras."
                        )
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=self.temperature,
                response_format={"type": "json_object"},
                timeout=60.0
            )
            
            response_text = response.choices[0].message.content
            mappings_dict = json.loads(response_text)
            
            # Validar y estructurar los mapeos
            mappings = self._validate_and_structure_mappings(mappings_dict, portfolio_items)
            
            logger.info(f"Mapeo completado: {len(mappings)} activos identificados")
            return mappings
            
        except json.JSONDecodeError as e:
            logger.error(f"Error parseando JSON de respuesta de OpenAI: {e}")
            raise ValueError(f"Error procesando respuesta de OpenAI: formato JSON inválido")
        except Exception as e:
            error_str = str(e)
            logger.error(f"Error mapeando escenarios a cartera: {e}", exc_info=True)
            
            if "401" in error_str or "invalid_api_key" in error_str:
                raise ValueError(
                    "Error de autenticación con OpenAI. Verifica tu API key en app/config.py"
                )
            elif "429" in error_str or "rate_limit" in error_str:
                raise ValueError("Límite de tasa excedido. Por favor, intenta más tarde.")
            elif "insufficient_quota" in error_str:
                raise ValueError("Cuota de OpenAI agotada. Verifica tu cuenta.")
            else:
                raise ValueError(f"Error al mapear escenarios a cartera: {error_str}")
    
    def _build_mapping_prompt(
        self, 
        driver: Dict, 
        scenarios: Dict, 
        portfolio_items: List[Dict]
    ) -> str:
        """Construye el prompt para mapeo a cartera."""
        driver_name = driver.get("driver", "Unknown")
        
        # Resumir escenarios
        scenarios_summary = {}
        for scenario_type, scenario in scenarios.items():
            scenarios_summary[scenario_type] = {
                "title": scenario.title,
                "description": scenario.description[:200] + "..." if len(scenario.description) > 200 else scenario.description
            }
        
        # Preparar información de cartera
        portfolio_summary = []
        tickers = set()
        sectors = set()
        fx_pairs = set()
        
        for item in portfolio_items:
            symbol = item.get("symbol", "").upper()
            asset_type = item.get("asset_type", "").lower()
            name = item.get("name", "")
            
            portfolio_summary.append({
                "symbol": symbol,
                "name": name,
                "asset_type": asset_type
            })
            
            if symbol:
                tickers.add(symbol)
            
            # Extraer sectores de categorías si existen
            # (esto sería mejorado con un servicio de clasificación de sectores)
        
        prompt = f"""Mapea los siguientes escenarios de mercado a los activos de la cartera proporcionada.

DRIVER: {driver_name}

ESCENARIOS:
{json.dumps(scenarios_summary, indent=2, ensure_ascii=False)}

CARTERA:
{json.dumps(portfolio_summary, indent=2, ensure_ascii=False)}

TICKERS EN CARTERA: {', '.join(sorted(tickers)) if tickers else 'Ninguno identificado'}

Instrucciones:
1. Identifica qué activos de la cartera serían afectados por estos escenarios
2. Para cada activo afectado, proporciona:
   - asset_type: "ticker", "sector", o "fx"
   - identifier: El ticker (ej: "AAPL"), sector (ej: "Technology"), o par FX (ej: "USD/EUR")
   - name: Nombre descriptivo del activo
   - sensitivity: Sensibilidad estimada (-1.0 a 1.0, negativo=bajista, positivo=alcista)
   - confidence: Confianza en el mapeo (0.0-1.0)
   - impact_description: Descripción breve del impacto esperado

3. Incluye mapeos a:
   - Tickers específicos mencionados en la cartera
   - Sectores relevantes (si aplica)
   - Pares FX si el driver afecta divisas

4. Solo incluye mapeos con confianza >= 0.4

Responde en formato JSON con esta estructura:
{{
    "mappings": [
        {{
            "asset_type": "ticker",
            "identifier": "AAPL",
            "name": "Apple Inc.",
            "sensitivity": 0.7,
            "confidence": 0.8,
            "impact_description": "Impacto positivo por..."
        }},
        {{
            "asset_type": "sector",
            "identifier": "Technology",
            "name": "Sector Tecnológico",
            "sensitivity": 0.5,
            "confidence": 0.6,
            "impact_description": "Impacto moderado..."
        }}
    ]
}}
"""
        return prompt
    
    def _validate_and_structure_mappings(
        self, 
        mappings_dict: Dict, 
        portfolio_items: List[Dict]
    ) -> List[PortfolioAssetMapping]:
        """Valida y estructura los mapeos a cartera."""
        mappings = []
        
        if "mappings" not in mappings_dict:
            logger.warning("Respuesta de OpenAI no contiene campo 'mappings'")
            return mappings
        
        # Crear sets de identificadores válidos para validación
        valid_tickers = {item.get("symbol", "").upper() for item in portfolio_items if item.get("symbol")}
        
        for mapping_data in mappings_dict["mappings"]:
            if not isinstance(mapping_data, dict):
                continue
            
            asset_type = mapping_data.get("asset_type", "").lower()
            identifier = mapping_data.get("identifier", "").strip()
            sensitivity = mapping_data.get("sensitivity", 0.0)
            confidence = mapping_data.get("confidence", 0.0)
            
            # Validar campos requeridos
            if not identifier or asset_type not in ["ticker", "sector", "fx"]:
                logger.warning(f"Mapeo inválido: {mapping_data}")
                continue
            
            # Validar sensibilidad y confianza
            sensitivity = max(-1.0, min(1.0, float(sensitivity)))
            confidence = max(0.0, min(1.0, float(confidence)))
            
            # Filtrar mapeos con baja confianza
            if confidence < 0.4:
                logger.debug(f"Mapeo con baja confianza omitido: {identifier} (confianza: {confidence})")
                continue
            
            # Validar que el ticker existe en la cartera (solo para tipo "ticker")
            if asset_type == "ticker" and identifier.upper() not in valid_tickers:
                logger.warning(f"Ticker '{identifier}' no encontrado en cartera, omitiendo")
                continue
            
            try:
                mapping = PortfolioAssetMapping(
                    asset_type=asset_type,
                    identifier=identifier,
                    name=mapping_data.get("name"),
                    sensitivity=sensitivity,
                    confidence=confidence,
                    impact_description=mapping_data.get("impact_description")
                )
                mappings.append(mapping)
            except Exception as e:
                logger.error(f"Error creando PortfolioAssetMapping: {e}", exc_info=True)
                continue
        
        return mappings

