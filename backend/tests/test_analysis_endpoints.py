"""Tests para endpoints de análisis, especialmente manejo de standardized_data."""
import pytest
import json
import os
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, NewsItem, PortfolioItem
from app.routers.news import build_news_item_response
from app.models import NewsItemResponse, StandardizedNewsData


@pytest.fixture(scope="function")
def db():
    """Crea una base de datos en memoria para tests."""
    # Crear engine en memoria
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    
    # Crear todas las tablas
    Base.metadata.create_all(bind=engine)
    
    # Crear sesión
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


class TestAnalysisEndpoints:
    """Tests para endpoints de análisis."""
    
    def test_build_news_item_response_with_string_standardized_data(self, db: Session):
        """Test que build_news_item_response maneja standardized_data como string JSON."""
        # Crear noticia con standardized_data como string JSON
        standardized_data_dict = {
            "title": "Test News",
            "summary": ["Summary point 1", "Summary point 2"],
            "sentiment": "bullish",
            "tickers": ["AAPL"],
            "categories": ["Technology"]
        }
        standardized_data_json = json.dumps(standardized_data_dict, ensure_ascii=False)
        
        news_item = NewsItem(
            title="Test News Title",
            body="Test news body with enough content to pass validation. " * 10,
            source="Test Source",
            standardized_data=standardized_data_json,
            score=5.5,
            score_components=json.dumps({"base": 3.0, "ticker_matches": 2.5}),
            is_obsolete=False
        )
        db.add(news_item)
        db.commit()
        db.refresh(news_item)
        
        # Construir respuesta usando build_news_item_response
        response = build_news_item_response(news_item)
        
        # Verificar que la respuesta es válida
        assert isinstance(response, NewsItemResponse)
        assert response.id == news_item.id
        assert response.title == news_item.title
        assert response.body == news_item.body
        assert response.score == 5.5
        assert response.is_obsolete is False
        
        # Verificar que standardized_data se parseó correctamente
        assert response.standardized_data is not None
        assert isinstance(response.standardized_data, StandardizedNewsData)
        assert response.standardized_data.title == "Test News"
        assert response.standardized_data.sentiment == "bullish"
        assert "AAPL" in response.standardized_data.tickers
    
    def test_build_news_item_response_with_null_standardized_data(self, db: Session):
        """Test que build_news_item_response maneja standardized_data NULL."""
        news_item = NewsItem(
            title="Test News Title",
            body="Test news body with enough content to pass validation. " * 10,
            source="Test Source",
            standardized_data=None,
            score=None,
            score_components=None,
            is_obsolete=False
        )
        db.add(news_item)
        db.commit()
        db.refresh(news_item)
        
        # Construir respuesta usando build_news_item_response
        response = build_news_item_response(news_item)
        
        # Verificar que la respuesta es válida
        assert isinstance(response, NewsItemResponse)
        assert response.id == news_item.id
        assert response.standardized_data is None
        assert response.score is None
        assert response.score_components is None
        assert response.is_obsolete is False
    
    def test_build_news_item_response_with_invalid_json_standardized_data(self, db: Session):
        """Test que build_news_item_response maneja standardized_data con JSON inválido."""
        # Crear noticia con standardized_data como string JSON inválido
        invalid_json = "{invalid json}"
        
        news_item = NewsItem(
            title="Test News Title",
            body="Test news body with enough content to pass validation. " * 10,
            source="Test Source",
            standardized_data=invalid_json,
            score=None,
            score_components=None,
            is_obsolete=False
        )
        db.add(news_item)
        db.commit()
        db.refresh(news_item)
        
        # Construir respuesta usando build_news_item_response
        # No debería lanzar excepción, sino manejar el error gracefully
        response = build_news_item_response(news_item)
        
        # Verificar que la respuesta es válida pero standardized_data es None
        assert isinstance(response, NewsItemResponse)
        assert response.id == news_item.id
        assert response.standardized_data is None  # Debería ser None debido al JSON inválido
    
    def test_build_news_item_response_with_score_components_json(self, db: Session):
        """Test que build_news_item_response parsea score_components como JSON."""
        score_components_dict = {
            "base": 3.0,
            "ticker_matches": 2.5,
            "category_matches": 1.0,
            "sentiment_type": "bullish",
            "sentiment_score": 0.7,
            "temporal_decay": 0.9,
            "is_obsolete": False
        }
        score_components_json = json.dumps(score_components_dict)
        
        news_item = NewsItem(
            title="Test News Title",
            body="Test news body with enough content to pass validation. " * 10,
            source="Test Source",
            standardized_data=None,
            score=6.5,
            score_components=score_components_json,
            is_obsolete=False
        )
        db.add(news_item)
        db.commit()
        db.refresh(news_item)
        
        # Construir respuesta usando build_news_item_response
        response = build_news_item_response(news_item)
        
        # Verificar que score_components se parseó correctamente
        assert isinstance(response, NewsItemResponse)
        assert response.score == 6.5
        assert response.score_components is not None
        assert isinstance(response.score_components, dict)
        assert response.score_components["base"] == 3.0
        assert response.score_components["ticker_matches"] == 2.5
        assert response.score_components["sentiment_type"] == "bullish"
    
    def test_build_news_item_response_without_score_columns(self, db: Session):
        """Test que build_news_item_response maneja noticias sin columnas de score (backward compatibility)."""
        # Crear noticia sin especificar score, score_components, is_obsolete
        # Esto simula una noticia creada antes de que existieran esas columnas
        news_item = NewsItem(
            title="Old News Title",
            body="Old news body with enough content to pass validation. " * 10,
            source="Old Source"
            # No especificamos score, score_components, is_obsolete
        )
        db.add(news_item)
        db.commit()
        db.refresh(news_item)
        
        # Construir respuesta usando build_news_item_response
        # Debería manejar valores None gracefully usando getattr
        response = build_news_item_response(news_item)
        
        # Verificar que la respuesta es válida con valores por defecto
        assert isinstance(response, NewsItemResponse)
        assert response.id == news_item.id
        assert response.score is None  # Debería ser None, no AttributeError
        assert response.score_components is None
        assert response.is_obsolete is False  # Valor por defecto
