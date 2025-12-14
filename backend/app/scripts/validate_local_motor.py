"""Script para validar que el motor local funciona sin llamadas HTTP externas."""
import sys
from pathlib import Path
import logging
import requests
from unittest.mock import patch, MagicMock

# Agregar el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_no_http_calls():
    """Verifica que no se realizan llamadas HTTP externas."""
    logger.info("=" * 60)
    logger.info("Validación: Sin llamadas HTTP externas")
    logger.info("=" * 60)
    
    # Mock de requests para detectar llamadas HTTP
    original_request = requests.request
    http_calls = []
    
    def mock_request(*args, **kwargs):
        url = args[1] if len(args) > 1 else kwargs.get('url', '')
        http_calls.append(url)
        logger.warning(f"⚠️ Llamada HTTP detectada: {url}")
        # Retornar mock response para evitar errores
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {}
        return mock_response
    
    with patch('requests.request', side_effect=mock_request):
        try:
            # Importar servicios locales
            from app.services.situation_summary_service import SituationSummaryService
            from app.services.driver_detector import DriverDetector
            from app.services.template_scenario_generator import TemplateScenarioGenerator
            from app.services.rule_based_portfolio_mapper import RuleBasedPortfolioMapper
            from app.services.scenario_engine_service import ScenarioEngineService
            
            # Crear servicios (deben usar motor local por defecto)
            summary_service = SituationSummaryService()
            driver_detector = DriverDetector()
            scenario_generator = TemplateScenarioGenerator()
            portfolio_mapper = RuleBasedPortfolioMapper()
            scenario_service = ScenarioEngineService()
            
            # Verificar que usan motor local
            assert summary_service.use_extractive == True, "SituationSummaryService debe usar extractivo por defecto"
            assert scenario_service.use_rule_based == True, "ScenarioEngineService debe usar reglas por defecto"
            
            logger.info("✓ Servicios inicializados con motor local")
            
            # Test con datos de ejemplo
            test_news = [
                {
                    "id": 1,
                    "title": "Apple anuncia crecimiento récord",
                    "body": "Apple Inc. reportó un crecimiento récord en sus ventas de iPhone, superando las expectativas del mercado. La empresa tecnológica reportó ganancias históricas en el último trimestre.",
                    "text": "Apple Inc. reportó un crecimiento récord en sus ventas de iPhone, superando las expectativas del mercado. La empresa tecnológica reportó ganancias históricas en el último trimestre."
                },
                {
                    "id": 2,
                    "title": "Reserva Federal aumenta tasas",
                    "body": "La Reserva Federal aumentó las tasas de interés, generando preocupación en los mercados financieros. Los analistas prevén una desaceleración económica.",
                    "text": "La Reserva Federal aumentó las tasas de interés, generando preocupación en los mercados financieros. Los analistas prevén una desaceleración económica."
                }
            ]
            
            # Test 1: Resumen extractivo
            logger.info("\n[Test 1] Generando resumen extractivo...")
            summary_result = summary_service.generate_summary(test_news, use_batching=False)
            assert summary_result.get("method") == "extractive", "Debe usar método extractivo"
            assert summary_result.get("summary"), "Debe generar resumen"
            logger.info(f"✓ Resumen generado: {len(summary_result.get('summary', ''))} caracteres")
            
            # Test 2: Detección de drivers
            logger.info("\n[Test 2] Detectando drivers...")
            drivers = driver_detector.detect_drivers(test_news, max_drivers=3)
            assert len(drivers) > 0, "Debe detectar al menos un driver"
            logger.info(f"✓ Drivers detectados: {len(drivers)}")
            
            # Test 3: Generación de escenarios
            if drivers:
                logger.info("\n[Test 3] Generando escenarios...")
                driver = drivers[0]
                related_news = [n for n in test_news if n["id"] in driver.get("related_news_ids", [])]
                scenarios = scenario_generator.generate_scenarios(driver, related_news)
                assert len(scenarios) > 0, "Debe generar al menos un escenario"
                logger.info(f"✓ Escenarios generados: {list(scenarios.keys())}")
            
            # Test 4: Mapeo a cartera
            logger.info("\n[Test 4] Mapeando a cartera...")
            portfolio_items = [
                {"name": "Apple Inc", "symbol": "AAPL", "asset_type": "stock"},
                {"name": "Tesla Inc", "symbol": "TSLA", "asset_type": "stock"}
            ]
            if drivers and scenarios:
                mappings = portfolio_mapper.map_scenarios_to_portfolio(
                    drivers[0], scenarios, portfolio_items, test_news
                )
                logger.info(f"✓ Mapeos generados: {len(mappings)}")
            
            # Test 5: Servicio completo de escenarios
            logger.info("\n[Test 5] Generando escenarios completos...")
            scenario_response = scenario_service.generate_scenarios(
                test_news,
                portfolio_items,
                max_drivers=3
            )
            assert scenario_response.total_drivers > 0, "Debe generar al menos un driver"
            logger.info(f"✓ Escenarios completos generados: {scenario_response.total_drivers} drivers")
            
        except Exception as e:
            logger.error(f"✗ Error durante validación: {e}", exc_info=True)
            return False
    
    # Verificar que no hubo llamadas HTTP
    if http_calls:
        logger.error("=" * 60)
        logger.error("✗ VALIDACIÓN FALLIDA: Se detectaron llamadas HTTP externas")
        logger.error(f"  Llamadas detectadas: {len(http_calls)}")
        for call in http_calls:
            logger.error(f"    - {call}")
        logger.error("=" * 60)
        return False
    else:
        logger.info("=" * 60)
        logger.info("✓ VALIDACIÓN EXITOSA: No se detectaron llamadas HTTP externas")
        logger.info("=" * 60)
        return True


def test_endpoints_local():
    """Verifica que los endpoints usan motor local."""
    logger.info("\n" + "=" * 60)
    logger.info("Validación: Endpoints usan motor local")
    logger.info("=" * 60)
    
    try:
        from app.routers.news import get_situation_summary
        from app.routers.scenarios import generate_scenarios
        from app.services.situation_summary_service import SituationSummaryService
        from app.services.scenario_engine_service import ScenarioEngineService
        
        # Verificar que los servicios se instancian con motor local
        summary_service = SituationSummaryService()
        scenario_service = ScenarioEngineService()
        
        assert summary_service.use_extractive == True, "Endpoint de summary debe usar extractivo"
        assert scenario_service.use_rule_based == True, "Endpoint de scenarios debe usar reglas"
        
        logger.info("✓ Endpoints configurados para usar motor local")
        return True
        
    except Exception as e:
        logger.error(f"✗ Error validando endpoints: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    logger.info("\n" + "=" * 60)
    logger.info("VALIDACIÓN DEL MOTOR LOCAL")
    logger.info("=" * 60)
    
    test1_passed = test_no_http_calls()
    test2_passed = test_endpoints_local()
    
    if test1_passed and test2_passed:
        logger.info("\n" + "=" * 60)
        logger.info("✓ TODAS LAS VALIDACIONES PASARON")
        logger.info("  - Sin llamadas HTTP externas")
        logger.info("  - Endpoints usan motor local")
        logger.info("  - Servicios funcionan correctamente")
        logger.info("=" * 60)
        sys.exit(0)
    else:
        logger.error("\n" + "=" * 60)
        logger.error("✗ ALGUNAS VALIDACIONES FALLARON")
        logger.error("=" * 60)
        sys.exit(1)
