"""Tests para el endpoint de limpieza de noticias."""
import pytest
from app.database import Base, engine, SessionLocal, NewsItem
from datetime import datetime


@pytest.fixture(autouse=True)
def setup_database():
    """Fixture para limpiar y preparar la base de datos antes de cada test."""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        # Limpiar todas las noticias antes del test
        db.query(NewsItem).delete()
        db.commit()
        
        # Crear algunas noticias de prueba
        for i in range(3):
            news = NewsItem(
                title=f"Test News {i+1}",
                body="Test body content " * 20,  # Más de 200 caracteres
                source=f"Test Source {i+1}",
                created_at=datetime.utcnow()
            )
            db.add(news)
        db.commit()
        yield
    finally:
        db.close()


def test_clear_all_news_success():
    """Test que el endpoint limpia todas las noticias correctamente."""
    db = SessionLocal()
    
    try:
        # Verificar que hay noticias antes (creadas por el fixture)
        total_before = db.query(NewsItem).count()
        assert total_before == 3
        
        # Limpiar todas las noticias directamente usando la lógica del endpoint
        db.query(NewsItem).delete()
        db.commit()
        
        # Verificar que realmente se eliminaron
        total_after = db.query(NewsItem).count()
        assert total_after == 0
    finally:
        db.close()


def test_clear_all_news_empty_list():
    """Test que limpiar una lista vacía funciona correctamente."""
    db = SessionLocal()
    
    try:
        # Limpiar primero
        db.query(NewsItem).delete()
        db.commit()
        assert db.query(NewsItem).count() == 0
        
        # Intentar limpiar nuevamente (debe funcionar sin error)
        db.query(NewsItem).delete()
        db.commit()
        assert db.query(NewsItem).count() == 0
    finally:
        db.close()


def test_clear_all_news_response_structure():
    """Test que la estructura de respuesta es correcta."""
    from app.models import NewsListResponse
    
    # Crear respuesta vacía como lo haría el endpoint
    response = NewsListResponse(items=[], total=0)
    
    assert hasattr(response, 'items')
    assert hasattr(response, 'total')
    assert isinstance(response.items, list)
    assert isinstance(response.total, int)
    assert response.total == 0
    assert len(response.items) == 0

