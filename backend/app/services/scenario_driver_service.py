"""Servicio para agrupar noticias en drivers temáticos."""
import logging
import json
from typing import List, Dict, Set
from openai import OpenAI
from app.config import (
    OPENAI_API_KEY,
    OPENAI_MODEL,
    OPENAI_TEMPERATURE
)

logger = logging.getLogger(__name__)


class ScenarioDriverService:
    """Servicio para identificar y agrupar noticias en drivers temáticos."""
    
    def __init__(self):
        """Inicializa el cliente de OpenAI."""
        if not OPENAI_API_KEY or OPENAI_API_KEY == "your_openai_api_key_here":
            raise ValueError("OPENAI_API_KEY no está configurada correctamente en app/config.py")
        
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        self.model = OPENAI_MODEL
        self.temperature = OPENAI_TEMPERATURE
    
    def identify_drivers(self, standardized_news_items: List[Dict], max_drivers: int = 5) -> List[Dict]:
        """
        Identifica drivers temáticos a partir de noticias estandarizadas.
        
        Args:
            standardized_news_items: Lista de diccionarios con datos estandarizados de noticias
            max_drivers: Máximo número de drivers a identificar
            
        Returns:
            Lista de diccionarios con drivers identificados, cada uno con:
            - driver: nombre del driver
            - description: descripción del driver
            - related_news_ids: lista de IDs de noticias relacionadas
        """
        if not standardized_news_items:
            logger.warning("No hay noticias para identificar drivers")
            return []
        
        try:
            prompt = self._build_driver_identification_prompt(standardized_news_items, max_drivers)
            
            logger.info(
                f"Identificando drivers temáticos: {len(standardized_news_items)} noticias, "
                f"máximo {max_drivers} drivers"
            )
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Eres un analista financiero experto especializado en identificar drivers temáticos "
                            "que mueven los mercados. Agrupas noticias relacionadas en temas coherentes que "
                            "representan fuerzas fundamentales del mercado. "
                            "Cada driver debe ser específico, accionable y basado en las noticias proporcionadas. "
                            "Evitas drivers genéricos o demasiado amplios."
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
            logger.info(f"Respuesta de OpenAI (primeros 500 chars): {response_text[:500]}")
            
            drivers_dict = json.loads(response_text)
            logger.info(f"Drivers parseados del JSON: {drivers_dict}")
            
            # Validar y estructurar la respuesta
            drivers = self._validate_and_structure_drivers(drivers_dict, standardized_news_items)
            
            logger.info(f"Identificados {len(drivers)} drivers temáticos")
            if len(drivers) == 0 and "drivers" in drivers_dict and len(drivers_dict["drivers"]) > 0:
                logger.warning(f"Se recibieron {len(drivers_dict['drivers'])} drivers de OpenAI pero ninguno pasó la validación")
            return drivers
            
        except json.JSONDecodeError as e:
            logger.error(f"Error parseando JSON de respuesta de OpenAI: {e}")
            raise ValueError(f"Error procesando respuesta de OpenAI: formato JSON inválido")
        except Exception as e:
            error_str = str(e)
            logger.error(f"Error identificando drivers: {e}", exc_info=True)
            
            if "401" in error_str or "invalid_api_key" in error_str:
                raise ValueError(
                    "Error de autenticación con OpenAI. Verifica tu API key en app/config.py"
                )
            elif "429" in error_str or "rate_limit" in error_str:
                raise ValueError("Límite de tasa excedido. Por favor, intenta más tarde.")
            elif "insufficient_quota" in error_str:
                raise ValueError("Cuota de OpenAI agotada. Verifica tu cuenta.")
            else:
                raise ValueError(f"Error al identificar drivers: {error_str}")
    
    def _build_driver_identification_prompt(self, standardized_news_items: List[Dict], max_drivers: int) -> str:
        """Construye el prompt para identificación de drivers."""
        news_summaries = []
        for idx, news in enumerate(standardized_news_items):
            news_id = news.get("id", idx + 1)
            standardized_data = news.get("standardized_data", {})
            
            # Si standardized_data es un objeto Pydantic, convertirlo a dict
            if hasattr(standardized_data, 'model_dump'):
                standardized_data = standardized_data.model_dump()
            elif hasattr(standardized_data, 'dict'):
                standardized_data = standardized_data.dict()
            
            summary = standardized_data.get("summary", "")
            sentiment = standardized_data.get("sentiment", "neutral")
            tickers = standardized_data.get("tickers", [])
            categories = standardized_data.get("categories", [])
            
            news_summaries.append({
                "id": news_id,
                "summary": summary,
                "sentiment": sentiment,
                "tickers": tickers,
                "categories": categories
            })
        
        # Log de IDs que se están enviando
        news_ids_sent = [ns["id"] for ns in news_summaries]
        logger.info(f"IDs de noticias enviados a OpenAI para identificación de drivers: {news_ids_sent}")
        
        prompt = f"""Analiza las siguientes noticias estandarizadas e identifica los drivers temáticos principales que las agrupan.

Un driver temático es una fuerza fundamental del mercado que agrupa múltiples noticias relacionadas. 
Ejemplos: "Política monetaria de la Fed", "Tensiones geopolíticas en Oriente Medio", "Evolución de IA y chips", etc.

Noticias a analizar:
{json.dumps(news_summaries, indent=2, ensure_ascii=False)}

Instrucciones:
1. Identifica entre 1 y {max_drivers} drivers temáticos principales
2. Cada driver debe agrupar al menos 2 noticias relacionadas
3. Los drivers deben ser específicos y accionables (no genéricos como "noticias del mercado")
4. Para cada driver, proporciona:
   - Un nombre claro y conciso
   - Una descripción breve (1-2 frases)
   - Los IDs de las noticias relacionadas

Responde en formato JSON con esta estructura:
{{
    "drivers": [
        {{
            "driver": "Nombre del driver",
            "description": "Descripción del driver",
            "related_news_ids": [1, 2, 3]
        }}
    ]
}}
"""
        return prompt
    
    def _validate_and_structure_drivers(self, drivers_dict: Dict, standardized_news_items: List[Dict]) -> List[Dict]:
        """Valida y estructura los drivers identificados."""
        drivers = []
        
        if "drivers" not in drivers_dict:
            logger.warning("Respuesta de OpenAI no contiene campo 'drivers'")
            logger.debug(f"Contenido recibido: {drivers_dict}")
            return drivers
        
        # Crear mapa de IDs válidos
        valid_news_ids = {news.get("id", idx + 1) for idx, news in enumerate(standardized_news_items)}
        logger.debug(f"IDs de noticias válidos: {valid_news_ids}")
        
        for idx, driver_data in enumerate(drivers_dict["drivers"]):
            if not isinstance(driver_data, dict):
                logger.warning(f"Driver en índice {idx} no es un diccionario: {driver_data}")
                continue
            
            driver_name = driver_data.get("driver", "").strip()
            driver_description = driver_data.get("description", "").strip()
            related_ids = driver_data.get("related_news_ids", [])
            
            logger.debug(f"Procesando driver '{driver_name}': IDs relacionados={related_ids}")
            
            if not driver_name:
                logger.warning(f"Driver en índice {idx} sin nombre, omitiendo")
                continue
            
            # Filtrar IDs inválidos
            valid_ids = [news_id for news_id in related_ids if news_id in valid_news_ids]
            
            if not valid_ids:
                logger.warning(
                    f"Driver '{driver_name}' no tiene noticias válidas asociadas. "
                    f"IDs recibidos: {related_ids}, IDs válidos: {valid_news_ids}"
                )
                continue
            
            drivers.append({
                "driver": driver_name,
                "description": driver_description,
                "related_news_ids": valid_ids
            })
        
        return drivers
