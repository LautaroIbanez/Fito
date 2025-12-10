"""Scripts de migración de base de datos."""
import logging
from sqlalchemy import text
from app.database import engine

logger = logging.getLogger(__name__)


def add_standardized_data_column():
    """Agrega la columna standardized_data a la tabla news_items si no existe."""
    try:
        with engine.connect() as conn:
            # Verificar si la columna ya existe consultando el schema
            result = conn.execute(text("PRAGMA table_info(news_items)"))
            columns = [row[1] for row in result.fetchall()]  # row[1] es el nombre de la columna
            
            if 'standardized_data' not in columns:
                logger.info("Agregando columna standardized_data a news_items...")
                conn.execute(text("""
                    ALTER TABLE news_items 
                    ADD COLUMN standardized_data TEXT
                """))
                conn.commit()
                logger.info("Columna standardized_data agregada exitosamente")
            else:
                logger.debug("Columna standardized_data ya existe, omitiendo migración")
                
    except Exception as e:
        logger.error(f"Error al ejecutar migración: {e}", exc_info=True)
        raise


def add_sectors_and_catalog_tables():
    """Crea las tablas de sectores y catálogo de activos si no existen."""
    try:
        from app.database import Base, Sector, AssetCatalog, WatchlistItem, TradingRecommendation
        Base.metadata.create_all(
            bind=engine, 
            tables=[
                Sector.__table__, 
                AssetCatalog.__table__, 
                WatchlistItem.__table__,
                TradingRecommendation.__table__
            ]
        )
        logger.info("Tablas de sectores, catálogo, watchlist y recomendaciones creadas/verificadas")
    except Exception as e:
        logger.error(f"Error creando tablas de sectores/catálogo: {e}", exc_info=True)
        raise


def init_catalog_data():
    """Inicializa datos del catálogo si está vacío."""
    try:
        from app.database import Sector, AssetCatalog
        from app.scripts.init_catalog import init_catalog
        
        # Verificar si ya hay sectores
        with engine.connect() as conn:
            result = conn.execute(text("SELECT COUNT(*) FROM sectors"))
            sector_count = result.scalar()
            
            if sector_count == 0:
                logger.info("Inicializando catálogo de sectores y activos...")
                db = SessionLocal()
                try:
                    init_catalog(db)
                    logger.info("Catálogo inicializado exitosamente")
                finally:
                    db.close()
            else:
                logger.debug(f"Catálogo ya tiene {sector_count} sectores, omitiendo inicialización")
    except Exception as e:
        logger.warning(f"Error inicializando catálogo (puede ser normal si las tablas no existen aún): {e}")


def run_migrations():
    """Ejecuta todas las migraciones pendientes."""
    logger.info("Ejecutando migraciones de base de datos...")
    add_standardized_data_column()
    add_sectors_and_catalog_tables()
    
    # Intentar inicializar catálogo (puede fallar si las tablas no existen aún)
    try:
        init_catalog_data()
    except Exception as e:
        logger.debug(f"No se pudo inicializar catálogo aún: {e}")
    
    logger.info("Migraciones completadas")

