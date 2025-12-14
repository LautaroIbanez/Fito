"""Script para verificar reproducibilidad de análisis de sentimiento y sectores."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from app.services.sentiment_service import get_sentiment_service
from app.services.sector_service import get_sector_service


def test_reproducibility():
    """Verifica que los resultados sean reproducibles."""
    print("=" * 60)
    print("TEST DE REPRODUCIBILIDAD")
    print("=" * 60)
    
    test_text = "Apple anunció un crecimiento récord en sus ventas de iPhone, superando las expectativas del mercado. La empresa tecnológica reportó ganancias históricas en el último trimestre."
    
    sentiment_service = get_sentiment_service()
    sector_service = get_sector_service()
    
    # Ejecutar análisis múltiples veces
    results_sentiment = []
    results_sector = []
    
    for i in range(5):
        sentiment_result = sentiment_service.analyze_sentiment(test_text)
        sector_result = sector_service.classify_sector(test_text)
        
        results_sentiment.append(sentiment_result)
        results_sector.append(sector_result)
    
    # Verificar que todos los resultados sean idénticos
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
    
    print(f"\nAnálisis de Sentimiento:")
    print(f"  Resultado: {first_sentiment['sentiment']}")
    print(f"  Scores: {first_sentiment['scores']}")
    print(f"  Confianza: {first_sentiment['confidence']}")
    print(f"  Reproducible: {'✓ SÍ' if all_sentiment_same else '✗ NO'}")
    
    print(f"\nClasificación de Sector:")
    print(f"  Sector principal: {first_sector['primary_sector']}")
    print(f"  Sectores: {first_sector['sectors']}")
    print(f"  Confianza: {first_sector['confidence']}")
    print(f"  Reproducible: {'✓ SÍ' if all_sector_same else '✗ NO'}")
    
    print("\n" + "=" * 60)
    if all_sentiment_same and all_sector_same:
        print("✓ TODOS LOS TESTS PASARON: Los resultados son reproducibles")
        return True
    else:
        print("✗ TESTS FALLARON: Los resultados no son reproducibles")
        return False


if __name__ == "__main__":
    success = test_reproducibility()
    sys.exit(0 if success else 1)
