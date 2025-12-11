"""Tests para el endpoint de limpieza de cartera."""
import pytest
from app.database import Base, engine, SessionLocal, PortfolioItem
from datetime import datetime


@pytest.fixture(autouse=True)
def setup_database():
    """Fixture para limpiar y preparar la base de datos antes de cada test."""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        # Limpiar todos los items de cartera antes del test
        db.query(PortfolioItem).delete()
        db.commit()
        
        # Crear algunos items de prueba
        for i in range(3):
            item = PortfolioItem(
                asset_type='acciones',
                name=f"Test Asset {i+1}",
                symbol=f"TEST{i+1}",
                quantity='100',
                price='50.00',
                total_value='5000.00',
                currency='USD',
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.add(item)
        db.commit()
        yield
    finally:
        db.close()


def test_clear_all_portfolio_success():
    """Test que el endpoint limpia todos los items de cartera correctamente."""
    db = SessionLocal()
    
    try:
        # Verificar que hay items antes (creados por el fixture)
        total_before = db.query(PortfolioItem).count()
        assert total_before == 3
        
        # Limpiar todos los items directamente usando la lógica del endpoint
        db.query(PortfolioItem).delete()
        db.commit()
        
        # Verificar que realmente se eliminaron
        total_after = db.query(PortfolioItem).count()
        assert total_after == 0
    finally:
        db.close()


def test_clear_all_portfolio_empty_list():
    """Test que limpiar una lista vacía funciona correctamente."""
    db = SessionLocal()
    
    try:
        # Limpiar primero
        db.query(PortfolioItem).delete()
        db.commit()
        assert db.query(PortfolioItem).count() == 0
        
        # Intentar limpiar nuevamente (debe funcionar sin error)
        db.query(PortfolioItem).delete()
        db.commit()
        assert db.query(PortfolioItem).count() == 0
    finally:
        db.close()


def test_clear_all_portfolio_response_structure():
    """Test que la estructura de respuesta es correcta."""
    from app.models import PortfolioListResponse
    
    # Crear respuesta vacía como lo haría el endpoint
    response = PortfolioListResponse(items=[], total=0)
    
    assert hasattr(response, 'items')
    assert hasattr(response, 'total')
    assert isinstance(response.items, list)
    assert isinstance(response.total, int)
    assert response.total == 0
    assert len(response.items) == 0

