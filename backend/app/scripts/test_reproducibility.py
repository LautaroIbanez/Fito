"""Script para verificar reproducibilidad de análisis de sentimiento y sectores."""
import sys
from pathlib import Path

# Agregar el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import logging
from app.services.sentiment_service import get_sentiment_service
from app.services.sector_service import get_sector_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_reproducibility():
    """Verifica que los análisis sean reproducibles."""
    logger.info("=" * 60)
    logger.info("Prueba de Reproducibilidad - Sentimiento y Sectores")
    logger.info("=" * 60)
    
    sentiment_service = get_sentiment_service()
    sector_service = get_sector_service()
    
    # Textos de prueba
    test_texts = [
        "Apple anunció un crecimiento récord en sus ventas de iPhone, superando las expectativas del mercado. La empresa tecnológica reportó ganancias históricas en el último trimestre.",
        "La Reserva Federal aumentó las tasas de interés, generando preocupación en los mercados financieros. Los analistas prevén una desaceleración económica.",
        "Nueva tecnología de inteligencia artificial revoluciona el sector salud. Los inversores muestran optimismo ante las perspectivas de crecimiento."
    ]
    
    all_reproducible = True
    
    for idx, test_text in enumerate(test_texts, 1):
        logger.info(f"\n{'=' * 60}")
        logger.info(f"Prueba {idx}: Texto de {len(test_text)} caracteres")
        logger.info(f"{'=' * 60}")
        
        # Ejecutar análisis múltiples veces
        results_sentiment = []
        results_sector = []
        
        for run in range(5):
            sentiment_result = sentiment_service.analyze_sentiment(test_text)
            sector_result = sector_service.classify_sector(test_text)
            
            results_sentiment.append(sentiment_result)
            results_sector.append(sector_result)
        
        # Verificar reproducibilidad
        first_sentiment = results_sentiment[0]
        first_sector = results_sector[0]
        
        all_sentiment_same = all(
            r["sentiment"] == first_sentiment["sentiment"] and
            r["scores"] == first_sentiment["scores"] and
            r["confidence"] == first_sentiment["confidence"]
            for r in results_sentiment
        )
        
        all_sector_same = all(
            r["primary_sector"] == first_sector["primary_sector"] and
            r["sectors"] == first_sector["sectors"] and
            r["confidence"] == first_sector["confidence"]
            for r in results_sector
        )
        
        # Mostrar resultados
        logger.info(f"\nAnálisis de Sentimiento:")
        logger.info(f"  Resultado: {first_sentiment['sentiment']}")
        logger.info(f"  Scores: {first_sentiment['scores']}")
        logger.info(f"  Confianza: {first_sentiment['confidence']}")
        logger.info(f"  Reproducible: {'✓ SÍ' if all_sentiment_same else '✗ NO'}")
        
        logger.info(f"\nClasificación de Sector:")
        logger.info(f"  Sector principal: {first_sector['primary_sector']}")
        logger.info(f"  Sectores: {first_sector['sectors']}")
        logger.info(f"  Confianza: {first_sector['confidence']}")
        logger.info(f"  Reproducible: {'✓ SÍ' if all_sector_same else '✗ NO'}")
        
        if not all_sentiment_same or not all_sector_same:
            all_reproducible = False
            logger.error(f"  ⚠️ Prueba {idx} NO es reproducible")
        else:
            logger.info(f"  ✓ Prueba {idx} es reproducible")
    
    logger.info(f"\n{'=' * 60}")
    if all_reproducible:
        logger.info("✓ TODAS LAS PRUEBAS SON REPRODUCIBLES")
    else:
        logger.error("✗ ALGUNAS PRUEBAS NO SON REPRODUCIBLES")
    logger.info(f"{'=' * 60}")
    
    return all_reproducible


if __name__ == "__main__":
    success = test_reproducibility()
    sys.exit(0 if success else 1)
