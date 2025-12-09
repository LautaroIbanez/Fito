"""Configuración de base de datos SQLite."""
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from app.config import DATABASE_URL

Base = declarative_base()


class NewsItem(Base):
    """Modelo de datos para noticias."""
    __tablename__ = "news_items"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=True)
    body = Column(Text, nullable=False)
    source = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def to_dict(self):
        """Convierte el modelo a diccionario."""
        return {
            "id": self.id,
            "title": self.title,
            "body": self.body,
            "source": self.source,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class PortfolioItem(Base):
    """Modelo de datos para items de cartera."""
    __tablename__ = "portfolio_items"

    id = Column(Integer, primary_key=True, index=True)
    asset_type = Column(String(50), nullable=False)  # acciones, bonos, etf, fondos, divisas
    name = Column(String(200), nullable=False)
    symbol = Column(String(50), nullable=True)  # Ticker o símbolo
    quantity = Column(String(50), nullable=True)  # Cantidad (puede ser decimal)
    price = Column(String(50), nullable=True)  # Precio unitario
    total_value = Column(String(50), nullable=True)  # Valor total
    currency = Column(String(10), nullable=True, default="USD")
    notes = Column(Text, nullable=True)  # Notas adicionales
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def to_dict(self):
        """Convierte el modelo a diccionario."""
        return {
            "id": self.id,
            "asset_type": self.asset_type,
            "name": self.name,
            "symbol": self.symbol,
            "quantity": self.quantity,
            "price": self.price,
            "total_value": self.total_value,
            "currency": self.currency,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


# Crear engine y sessionmaker
engine = create_engine(
    DATABASE_URL,
    connect_args={
        "check_same_thread": False  # Necesario para SQLite
    },
    echo=False
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Inicializa la base de datos creando las tablas."""
    Base.metadata.create_all(bind=engine)


def get_db():
    """Dependency para obtener sesión de base de datos."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

