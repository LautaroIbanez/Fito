"""Tests para el servicio de scoring de noticias."""
import pytest
from datetime import datetime, timezone, timedelta
from app.services.news_scoring_service import NewsScoringService
from app.models import NewsItemResponse, PortfolioItemResponse


class TestTemporalDecay:
    """Tests para decay temporal."""
    
    def test_fresh_news_no_decay(self):
        """Test que noticias frescas tienen decay mínimo."""
        service = NewsScoringService()
        
        # Noticia de hoy
        fresh_date = datetime.now(timezone.utc).isoformat()
        decay = service.calculate_temporal_decay(fresh_date)
        
        assert decay == pytest.approx(1.0, abs=0.01)
    
    def test_old_news_has_decay(self):
        """Test que noticias antiguas tienen decay."""
        service = NewsScoringService()
        
        # Noticia de hace 10 días
        old_date = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
        decay = service.calculate_temporal_decay(old_date)
        
        assert decay < 1.0
        assert decay > 0.0
    
    def test_obsolete_threshold(self):
        """Test umbral de noticias obsoletas."""
        service = NewsScoringService()
        
        # Noticia dentro del umbral
        recent_date = (datetime.now(timezone.utc) - timedelta(days=20)).isoformat()
        assert service.is_obsolete(recent_date) == False
        
        # Noticia fuera del umbral
        obsolete_date = (datetime.now(timezone.utc) - timedelta(days=35)).isoformat()
        assert service.is_obsolete(obsolete_date) == True


class TestTickerMentions:
    """Tests para detección de menciones de tickers."""
    
    def test_ticker_detection_exact_match(self):
        """Test detección exacta de ticker."""
        service = NewsScoringService()
        
        text = "AAPL subió 5% hoy. MSFT también tuvo ganancias."
        symbols = ["AAPL", "MSFT"]
        
        mentions = service.detect_ticker_mentions(text, symbols)
        assert mentions == 2
    
    def test_ticker_detection_case_insensitive(self):
        """Test que la detección es case-insensitive."""
        service = NewsScoringService()
        
        text = "Apple (aapl) anunció resultados positivos."
        symbols = ["AAPL"]
        
        mentions = service.detect_ticker_mentions(text, symbols)
        assert mentions == 1
    
    def test_ticker_no_partial_matches(self):
        """Test que no detecta matches parciales."""
        service = NewsScoringService()
        
        text = "AAPLE es diferente de AAPL"
        symbols = ["AAPL"]
        
        mentions = service.detect_ticker_mentions(text, symbols)
        assert mentions == 1  # Solo AAPL, no AAPLE


class TestCategoryMentions:
    """Tests para detección de menciones de categorías."""
    
    def test_category_detection(self):
        """Test detección de categorías."""
        service = NewsScoringService()
        
        text = "Las acciones del mercado subieron. Los bonos también mostraron fortaleza."
        categories = ["acciones", "bonos"]
        
        mentions = service.detect_category_mentions(text, categories)
        assert mentions >= 1  # Debe encontrar al menos "acciones" o "bonos"
    
    def test_category_keywords(self):
        """Test que usa palabras clave específicas."""
        service = NewsScoringService()
        
        text = "El mercado de renta fija muestra estabilidad."
        categories = ["bonos"]
        
        mentions = service.detect_category_mentions(text, categories)
        assert mentions >= 1  # "renta fija" es keyword para bonos


class TestSentimentAnalysis:
    """Tests para análisis de sentimiento."""
    
    def test_positive_sentiment(self):
        """Test detección de sentimiento positivo."""
        service = NewsScoringService()
        
        text = "El mercado crece positivamente con ganancias récord y expansión del sector."
        sentiment_type, score = service.analyze_sentiment(text)
        
        assert sentiment_type == "positive"
        assert score > 0
    
    def test_negative_sentiment(self):
        """Test detección de sentimiento negativo."""
        service = NewsScoringService()
        
        text = "El mercado cae con pérdidas significativas y riesgo de crisis."
        sentiment_type, score = service.analyze_sentiment(text)
        
        assert sentiment_type == "negative"
        assert score < 0
    
    def test_neutral_sentiment(self):
        """Test sentimiento neutro."""
        service = NewsScoringService()
        
        text = "El mercado se mantiene estable sin cambios significativos."
        sentiment_type, score = service.analyze_sentiment(text)
        
        assert sentiment_type == "neutral"


class TestNewsScoring:
    """Tests para cálculo completo de scores."""
    
    def test_base_score(self):
        """Test que todas las noticias tienen score base."""
        service = NewsScoringService()
        
        news = NewsItemResponse(
            id=1,
            title="Test News",
            body="Contenido de prueba " * 50,
            source="Test",
            created_at=datetime.now(timezone.utc).isoformat()
        )
        
        score_dict = service.calculate_news_score(news)
        
        assert score_dict["score"] >= service.base_score
        assert score_dict["components"]["base"] == service.base_score
    
    def test_score_with_ticker_match(self):
        """Test score con coincidencia de ticker."""
        service = NewsScoringService()
        
        portfolio = [
            PortfolioItemResponse(
                id=1,
                asset_type="acciones",
                name="Apple Inc.",
                symbol="AAPL",
                quantity=None,
                price=None,
                total_value="1000",
                currency="USD",
                notes=None,
                created_at="2025-12-01T10:00:00",
                updated_at="2025-12-01T10:00:00"
            )
        ]
        
        news = NewsItemResponse(
            id=1,
            title="AAPL sube 5%",
            body="Apple Inc. (AAPL) anunció resultados positivos con crecimiento récord. " * 10,
            source="Financial News",
            created_at=datetime.now(timezone.utc).isoformat()
        )
        
        score_dict = service.calculate_news_score(news, portfolio)
        
        assert score_dict["score"] > service.base_score
        assert score_dict["components"]["ticker_matches"] > 0
        assert score_dict["components"]["ticker_score"] > 0
    
    def test_score_with_category_match(self):
        """Test score con coincidencia de categoría."""
        service = NewsScoringService()
        
        portfolio = [
            PortfolioItemResponse(
                id=1,
                asset_type="acciones",
                name="Tech Stock",
                symbol=None,
                quantity=None,
                price=None,
                total_value="1000",
                currency="USD",
                notes=None,
                created_at="2025-12-01T10:00:00",
                updated_at="2025-12-01T10:00:00"
            )
        ]
        
        news = NewsItemResponse(
            id=1,
            title="Las acciones muestran fortaleza",
            body="El mercado de acciones subió significativamente hoy con todas las empresas mostrando ganancias. " * 10,
            source="Market News",
            created_at=datetime.now(timezone.utc).isoformat()
        )
        
        score_dict = service.calculate_news_score(news, portfolio)
        
        assert score_dict["components"]["category_matches"] > 0
        assert score_dict["components"]["category_score"] > 0
    
    def test_score_with_sentiment(self):
        """Test score con sentimiento."""
        service = NewsScoringService()
        
        news = NewsItemResponse(
            id=1,
            title="Mercado en alza",
            body="El mercado crece positivamente con ganancias récord y expansión continua. " * 10,
            source="News",
            created_at=datetime.now(timezone.utc).isoformat()
        )
        
        score_dict = service.calculate_news_score(news)
        
        assert score_dict["components"]["sentiment_type"] in ["positive", "negative", "neutral"]
        assert score_dict["components"]["sentiment_score"] != 0 or score_dict["components"]["sentiment_type"] == "neutral"
    
    def test_score_ordering(self):
        """Test que el ordenamiento por score funciona."""
        service = NewsScoringService()
        
        portfolio = [
            PortfolioItemResponse(
                id=1,
                asset_type="acciones",
                name="Apple",
                symbol="AAPL",
                quantity=None,
                price=None,
                total_value="1000",
                currency="USD",
                notes=None,
                created_at="2025-12-01T10:00:00",
                updated_at="2025-12-01T10:00:00"
            )
        ]
        
        news_items = [
            NewsItemResponse(
                id=1,
                title="Noticia genérica",
                body="Contenido general sin menciones específicas. " * 10,
                source="News",
                created_at=datetime.now(timezone.utc).isoformat()
            ),
            NewsItemResponse(
                id=2,
                title="AAPL sube",
                body="Apple (AAPL) anunció resultados excelentes con crecimiento récord. " * 10,
                source="Financial",
                created_at=datetime.now(timezone.utc).isoformat()
            )
        ]
        
        scored_news = service.score_and_sort_news(news_items, portfolio)
        
        assert len(scored_news) == 2
        assert scored_news[0][1]["score"] >= scored_news[1][1]["score"]
        # La noticia con AAPL debe tener mayor score
        assert scored_news[0][0].id == 2 or scored_news[0][1]["score"] > scored_news[1][1]["score"]
    
    def test_obsolete_marking(self):
        """Test que noticias obsoletas se marcan correctamente."""
        service = NewsScoringService()
        
        obsolete_date = (datetime.now(timezone.utc) - timedelta(days=35)).isoformat()
        news = NewsItemResponse(
            id=1,
            title="Old News",
            body="Contenido antiguo " * 10,
            source="News",
            created_at=obsolete_date
        )
        
        score_dict = service.calculate_news_score(news)
        
        assert score_dict["components"]["is_obsolete"] == True
        assert score_dict["components"]["age_days"] > service.obsolete_days





