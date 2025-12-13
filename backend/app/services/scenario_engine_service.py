"""Servicio principal del motor de escenarios que orquesta todos los componentes."""
import logging
from typing import List, Dict, Optional
from datetime import datetime
from app.services.scenario_driver_service import ScenarioDriverService
from app.services.scenario_generation_service import ScenarioGenerationService
from app.services.scenario_portfolio_mapping_service import ScenarioPortfolioMappingService
from app.models import (
    DriverScenarioResponse,
    ScenarioEngineResponse
)

logger = logging.getLogger(__name__)


class ScenarioEngineService:
    """Servicio principal del motor de escenarios."""
    
    def __init__(self):
        """Inicializa los servicios del motor de escenarios."""
        self.driver_service = ScenarioDriverService()
        self.scenario_service = ScenarioGenerationService()
        self.mapping_service = ScenarioPortfolioMappingService()
    
    def generate_scenarios(
        self,
        standardized_news_items: List[Dict],
        portfolio_items: Optional[List[Dict]] = None,
        max_drivers: int = 5,
        include_portfolio_mapping: bool = True
    ) -> ScenarioEngineResponse:
        """
        Genera escenarios completos: drivers → escenarios → mapeo a cartera.
        
        Args:
            standardized_news_items: Lista de noticias estandarizadas
            portfolio_items: Lista opcional de items de cartera
            max_drivers: Máximo número de drivers a generar
            include_portfolio_mapping: Si incluir mapeo a cartera
            
        Returns:
            ScenarioEngineResponse con todos los drivers y escenarios generados
        """
        drivers_responses = []
        warnings = []
        missing_fields = []
        partial_results = False
        
        try:
            # Paso 1: Identificar drivers temáticos
            logger.info(f"Iniciando generación de escenarios: {len(standardized_news_items)} noticias")
            
            drivers = self.driver_service.identify_drivers(standardized_news_items, max_drivers)
            
            if not drivers:
                logger.warning("No se identificaron drivers temáticos")
                warnings.append("No se pudieron identificar drivers temáticos")
                return ScenarioEngineResponse(
                    drivers=[],
                    total_drivers=0,
                    total_news_analyzed=len(standardized_news_items),
                    generated_at=datetime.utcnow().isoformat(),
                    partial_results=False,
                    missing_fields=[],
                    warnings=warnings
                )
            
            # Crear mapa de noticias por ID para acceso rápido
            news_map = {news.get("id", idx + 1): news for idx, news in enumerate(standardized_news_items)}
            
            # Paso 2: Generar escenarios para cada driver
            for driver in drivers:
                try:
                    # Obtener noticias relacionadas al driver
                    related_news_ids = driver.get("related_news_ids", [])
                    related_news_items = [
                        news_map[news_id] 
                        for news_id in related_news_ids 
                        if news_id in news_map
                    ]
                    
                    if not related_news_items:
                        logger.warning(f"No se encontraron noticias relacionadas para driver '{driver.get('driver')}'")
                        warnings.append(f"Driver '{driver.get('driver')}': noticias relacionadas no encontradas")
                        continue
                    
                    # Generar escenarios
                    scenarios = self.scenario_service.generate_scenarios(driver, related_news_items)
                    
                    if not scenarios:
                        logger.warning(f"No se generaron escenarios para driver '{driver.get('driver')}'")
                        warnings.append(f"Driver '{driver.get('driver')}': no se generaron escenarios")
                        continue
                    
                    # Verificar que todos los tipos de escenario estén presentes
                    scenario_types = ["base", "risk", "opportunity"]
                    missing_scenario_types = [st for st in scenario_types if st not in scenarios]
                    if missing_scenario_types:
                        missing_fields.extend([
                            f"Driver '{driver.get('driver')}': escenario '{st}' faltante"
                            for st in missing_scenario_types
                        ])
                    
                    # Paso 3: Mapear a cartera (si se solicita y hay cartera)
                    portfolio_mappings = []
                    if include_portfolio_mapping and portfolio_items:
                        try:
                            portfolio_mappings = self.mapping_service.map_scenarios_to_portfolio(
                                driver, scenarios, portfolio_items
                            )
                        except Exception as e:
                            logger.error(f"Error mapeando a cartera para driver '{driver.get('driver')}': {e}")
                            warnings.append(f"Driver '{driver.get('driver')}': error en mapeo a cartera")
                            missing_fields.append(f"Driver '{driver.get('driver')}': mapeo a cartera faltante")
                    elif include_portfolio_mapping and not portfolio_items:
                        warnings.append("Mapeo a cartera solicitado pero no hay items de cartera disponibles")
                    
                    # Construir respuesta del driver
                    driver_response = DriverScenarioResponse(
                        driver=driver.get("driver", "Unknown"),
                        driver_description=driver.get("description", ""),
                        related_news_ids=related_news_ids,
                        scenarios=scenarios,
                        portfolio_mappings=portfolio_mappings,
                        generated_at=datetime.utcnow().isoformat(),
                        metadata={
                            "related_news_count": len(related_news_items),
                            "scenarios_generated": len(scenarios),
                            "mappings_count": len(portfolio_mappings)
                        }
                    )
                    
                    drivers_responses.append(driver_response)
                    
                except Exception as e:
                    logger.error(f"Error procesando driver '{driver.get('driver')}': {e}", exc_info=True)
                    warnings.append(f"Driver '{driver.get('driver')}': error en procesamiento - {str(e)}")
                    partial_results = True
                    continue
            
            # Si hay resultados parciales o campos faltantes, marcar como parcial
            if missing_fields or warnings:
                partial_results = True
            
            logger.info(f"Generación de escenarios completada: {len(drivers_responses)} drivers generados")
            
            return ScenarioEngineResponse(
                drivers=drivers_responses,
                total_drivers=len(drivers_responses),
                total_news_analyzed=len(standardized_news_items),
                generated_at=datetime.utcnow().isoformat(),
                partial_results=partial_results,
                missing_fields=missing_fields,
                warnings=warnings
            )
            
        except Exception as e:
            logger.error(f"Error crítico en generación de escenarios: {e}", exc_info=True)
            warnings.append(f"Error crítico: {str(e)}")
            
            # Retornar resultados parciales si los hay
            return ScenarioEngineResponse(
                drivers=drivers_responses,
                total_drivers=len(drivers_responses),
                total_news_analyzed=len(standardized_news_items),
                generated_at=datetime.utcnow().isoformat(),
                partial_results=True,
                missing_fields=missing_fields,
                warnings=warnings
            )

