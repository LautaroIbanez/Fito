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


def run_migrations():
    """Ejecuta todas las migraciones pendientes."""
    logger.info("Ejecutando migraciones de base de datos...")
    add_standardized_data_column()
    logger.info("Migraciones completadas")

