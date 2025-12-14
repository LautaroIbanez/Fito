"""Script para inicializar y verificar el sistema de NLP local."""
import sys
import os
from pathlib import Path

# Agregar el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import logging
from app.services.local_nlp import get_local_nlp_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    """Inicializa y verifica el sistema de NLP local."""
    logger.info("=" * 60)
    logger.info("Inicializando sistema de NLP local...")
    logger.info("=" * 60)
    
    try:
        # Inicializar servicio
        nlp_service = get_local_nlp_service()
        
        # Verificar que está listo
        if not nlp_service.is_ready():
            logger.error("El servicio de NLP no está listo")
            return False
        
        logger.info("✓ Servicio de NLP inicializado correctamente")
        
        # Prueba con texto de ejemplo
        test_text_es = "Apple anunció un crecimiento récord en sus ventas de iPhone, superando las expectativas del mercado. La empresa tecnológica reportó ganancias históricas en el último trimestre."
        test_text_en = "Apple announced record growth in iPhone sales, exceeding market expectations. The technology company reported historic profits in the last quarter."
        
        logger.info("\n" + "=" * 60)
        logger.info("Prueba con texto en español:")
        logger.info("=" * 60)
        result_es = nlp_service.analyze_news(test_text_es)
        logger.info(f"Sentimiento: {result_es['sentiment_label']} (scores: {result_es['sentiment']})")
        logger.info(f"Sectores: {result_es['sectors']}")
        logger.info(f"Sector principal: {result_es['primary_sector']}")
        logger.info(f"Entidades ORG: {result_es['entities']['ORG']}")
        logger.info(f"Tickers: {result_es['tickers']}")
        logger.info(f"Keywords: {result_es['keywords'][:5]}")
        
        logger.info("\n" + "=" * 60)
        logger.info("Prueba con texto en inglés:")
        logger.info("=" * 60)
        result_en = nlp_service.analyze_news(test_text_en)
        logger.info(f"Sentimiento: {result_en['sentiment_label']} (scores: {result_en['sentiment']})")
        logger.info(f"Sectores: {result_en['sectors']}")
        logger.info(f"Sector principal: {result_en['primary_sector']}")
        logger.info(f"Entidades ORG: {result_en['entities']['ORG']}")
        logger.info(f"Tickers: {result_en['tickers']}")
        logger.info(f"Keywords: {result_en['keywords'][:5]}")
        
        logger.info("\n" + "=" * 60)
        logger.info("✓ Sistema de NLP local funcionando correctamente")
        logger.info("=" * 60)
        
        return True
        
    except Exception as e:
        logger.error(f"Error inicializando sistema de NLP local: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
