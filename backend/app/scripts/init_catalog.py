"""Script para inicializar el catálogo de sectores y activos."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy.orm import Session
from app.database import SessionLocal, Sector, AssetCatalog
import logging

logger = logging.getLogger(__name__)

# Catálogo inicial de sectores
INITIAL_SECTORS = [
    {"name": "Tecnología", "category": "sector", "keywords": "tecnología,tech,software,hardware,cloud,IA,AI"},
    {"name": "Energía", "category": "sector", "keywords": "energía,petróleo,oil,gas,renovable,solar"},
    {"name": "Salud", "category": "sector", "keywords": "salud,farmacéutica,pharma,biotech,medicina"},
    {"name": "Finanzas", "category": "sector", "keywords": "bancos,finanzas,financiero,bancario,crédito"},
    {"name": "Consumo", "category": "sector", "keywords": "retail,consumo,venta al por menor,e-commerce"},
    {"name": "Industriales", "category": "sector", "keywords": "industrial,manufactura,infraestructura"},
    {"name": "Materiales", "category": "sector", "keywords": "materiales,minería,acero,cobre,oro"},
    {"name": "Bienes Raíces", "category": "sector", "keywords": "inmobiliario,real estate,REIT"},
    {"name": "Comunicaciones", "category": "sector", "keywords": "telecomunicaciones,telecom,5G,streaming"},
    {"name": "Utilidades", "category": "sector", "keywords": "utilidades,servicios públicos,electricidad"},
    {"name": "ESG", "category": "theme", "keywords": "ESG,sostenible,sustentable,medio ambiente"},
    {"name": "Criptomonedas", "category": "theme", "keywords": "bitcoin,crypto,blockchain,NFT"},
    {"name": "Energía Limpia", "category": "theme", "keywords": "energía limpia,renovable,solar,eólica"},
    {"name": "Inteligencia Artificial", "category": "theme", "keywords": "IA,AI,machine learning"},
    {"name": "E-commerce", "category": "theme", "keywords": "e-commerce,online,digital,plataforma"},
]

# Catálogo inicial de activos (ejemplos representativos)
INITIAL_ASSETS = [
    # Tecnología
    {"symbol": "AAPL", "name": "Apple Inc.", "asset_type": "stock", "sector": "Tecnología", "is_etf": False},
    {"symbol": "MSFT", "name": "Microsoft Corporation", "asset_type": "stock", "sector": "Tecnología", "is_etf": False},
    {"symbol": "GOOGL", "name": "Alphabet Inc.", "asset_type": "stock", "sector": "Tecnología", "is_etf": False},
    {"symbol": "NVDA", "name": "NVIDIA Corporation", "asset_type": "stock", "sector": "Tecnología", "is_etf": False},
    {"symbol": "XLK", "name": "Technology Select Sector SPDR Fund", "asset_type": "etf", "sector": "Tecnología", "is_etf": True},
    
    # Energía
    {"symbol": "XOM", "name": "Exxon Mobil Corporation", "asset_type": "stock", "sector": "Energía", "is_etf": False},
    {"symbol": "CVX", "name": "Chevron Corporation", "asset_type": "stock", "sector": "Energía", "is_etf": False},
    {"symbol": "XLE", "name": "Energy Select Sector SPDR Fund", "asset_type": "etf", "sector": "Energía", "is_etf": True},
    
    # Salud
    {"symbol": "JNJ", "name": "Johnson & Johnson", "asset_type": "stock", "sector": "Salud", "is_etf": False},
    {"symbol": "PFE", "name": "Pfizer Inc.", "asset_type": "stock", "sector": "Salud", "is_etf": False},
    {"symbol": "XLV", "name": "Health Care Select Sector SPDR Fund", "asset_type": "etf", "sector": "Salud", "is_etf": True},
    
    # Finanzas
    {"symbol": "JPM", "name": "JPMorgan Chase & Co.", "asset_type": "stock", "sector": "Finanzas", "is_etf": False},
    {"symbol": "BAC", "name": "Bank of America Corp", "asset_type": "stock", "sector": "Finanzas", "is_etf": False},
    {"symbol": "XLF", "name": "Financial Select Sector SPDR Fund", "asset_type": "etf", "sector": "Finanzas", "is_etf": True},
    
    # Consumo
    {"symbol": "AMZN", "name": "Amazon.com Inc.", "asset_type": "stock", "sector": "Consumo", "is_etf": False},
    {"symbol": "WMT", "name": "Walmart Inc.", "asset_type": "stock", "sector": "Consumo", "is_etf": False},
    {"symbol": "XLP", "name": "Consumer Staples Select Sector SPDR Fund", "asset_type": "etf", "sector": "Consumo", "is_etf": True},
    
    # ETFs temáticos
    {"symbol": "ARKK", "name": "ARK Innovation ETF", "asset_type": "etf", "sector": "Inteligencia Artificial", "is_etf": True},
    {"symbol": "ICLN", "name": "iShares Global Clean Energy ETF", "asset_type": "etf", "sector": "Energía Limpia", "is_etf": True},
]


def init_catalog(db: Session):
    """Inicializa el catálogo de sectores y activos."""
    try:
        # Crear sectores
        sectors_created = 0
        sector_map = {}
        
        for sector_data in INITIAL_SECTORS:
            existing = db.query(Sector).filter(Sector.name == sector_data["name"]).first()
            if not existing:
                sector = Sector(
                    name=sector_data["name"],
                    category=sector_data["category"],
                    keywords=sector_data["keywords"]
                )
                db.add(sector)
                db.flush()
                sector_map[sector_data["name"]] = sector.id
                sectors_created += 1
            else:
                sector_map[sector_data["name"]] = existing.id
        
        db.commit()
        logger.info(f"Creados {sectors_created} sectores nuevos")
        
        # Crear activos
        assets_created = 0
        
        for asset_data in INITIAL_ASSETS:
            existing = db.query(AssetCatalog).filter(AssetCatalog.symbol == asset_data["symbol"]).first()
            if not existing:
                sector_id = sector_map.get(asset_data["sector"])
                if sector_id:
                    asset = AssetCatalog(
                        symbol=asset_data["symbol"],
                        name=asset_data["name"],
                        asset_type=asset_data["asset_type"],
                        sector_id=sector_id,
                        is_etf=asset_data["is_etf"]
                    )
                    db.add(asset)
                    assets_created += 1
        
        db.commit()
        logger.info(f"Creados {assets_created} activos nuevos en el catálogo")
        
        return {"sectors_created": sectors_created, "assets_created": assets_created}
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error inicializando catálogo: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    db = SessionLocal()
    try:
        result = init_catalog(db)
        print(f"Catálogo inicializado: {result['sectors_created']} sectores, {result['assets_created']} activos")
    finally:
        db.close()


