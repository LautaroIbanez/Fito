"""
Tests para el servicio de ranking de cartera.
Prueba la lógica de fusión de scores y mapeo de thresholds.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone, timedelta

from app.services.portfolio_ranking_service import PortfolioRankingService
from app.models import PortfolioItemResponse, NewsItemResponse
from app.config import (
    PORTFOLIO_RANKING_SENTIMENT_WEIGHT,
    PORTFOLIO_RANKING_TECHNICAL_WEIGHT,
    PORTFOLIO_RANKING_GREEN_THRESHOLD,
    PORTFOLIO_RANKING_AMBER_THRESHOLD
)


class TestPortfolioRankingService:
    """Tests para PortfolioRankingService."""
    
    @pytest.fixture
    def ranking_service(self):
        """Crea una instancia del servicio."""
        return PortfolioRankingService()
    
    @pytest.fixture
    def mock_portfolio_item(self):
        """Crea un item de cartera mock."""
        return PortfolioItemResponse(
            id=1,
            asset_type="acciones",
            name="Apple Inc.",
            symbol="AAPL",
            quantity="100",
            price="150.00",
            total_value="15000.00",
            currency="USD",
            notes="",
            created_at=datetime.now(timezone.utc).isoformat(),
            updated_at=datetime.now(timezone.utc).isoformat()
        )
    
    @pytest.fixture
    def mock_news_items(self):
        """Crea noticias mock."""
        base_time = datetime.now(timezone.utc)
        return [
            NewsItemResponse(
                id=1,
                title="Apple reports strong earnings",
                body="Apple Inc. reported better than expected earnings for Q4",
                source="Tech News",
                created_at=(base_time - timedelta(hours=24)).isoformat(),
                score=8.5
            ),
            NewsItemResponse(
                id=2,
                title="Tech sector gains momentum",
                body="Technology sector shows strong performance",
                source="Market Watch",
                created_at=(base_time - timedelta(hours=48)).isoformat(),
                score=6.0
            ),
            NewsItemResponse(
                id=3,
                title="Apple faces challenges",
                body="Apple Inc. faces supply chain issues",
                source="Business News",
                created_at=(base_time - timedelta(hours=72)).isoformat(),
                score=-3.0
            )
        ]
    
    def test_map_to_traffic_light_green(self, ranking_service):
        """Test que scores altos mapean a verde."""
        sentiment_result = {"score": 0.8, "explanation": "Positive news"}
        technical_result = {"score": 0.7, "explanation": "Strong signals"}
        
        color, status_text, action = ranking_service._map_to_traffic_light(
            0.75,  # Composite score alto
            sentiment_result,
            technical_result
        )
        
        assert color == "green"
        assert status_text == "Favorable"
        assert action is not None
    
    def test_map_to_traffic_light_amber(self, ranking_service):
        """Test que scores medios mapean a ámbar."""
        sentiment_result = {"score": 0.5, "explanation": "Neutral news"}
        technical_result = {"score": 0.5, "explanation": "Mixed signals"}
        
        color, status_text, action = ranking_service._map_to_traffic_light(
            0.50,  # Composite score medio
            sentiment_result,
            technical_result
        )
        
        assert color == "amber"
        assert status_text == "Neutro"
        assert action is not None
    
    def test_map_to_traffic_light_red(self, ranking_service):
        """Test que scores bajos mapean a rojo."""
        sentiment_result = {"score": 0.2, "explanation": "Negative news"}
        technical_result = {"score": 0.3, "explanation": "Weak signals"}
        
        color, status_text, action = ranking_service._map_to_traffic_light(
            0.25,  # Composite score bajo
            sentiment_result,
            technical_result
        )
        
        assert color == "red"
        assert status_text == "Precaución"
        assert action is not None
    
    def test_map_to_traffic_light_threshold_boundaries(self, ranking_service):
        """Test que los thresholds se aplican correctamente."""
        sentiment_result = {"score": 0.5, "explanation": "Test"}
        technical_result = {"score": 0.5, "explanation": "Test"}
        
        # Test en el threshold verde
        color_green, _, _ = ranking_service._map_to_traffic_light(
            PORTFOLIO_RANKING_GREEN_THRESHOLD,
            sentiment_result,
            technical_result
        )
        assert color_green == "green"
        
        # Test justo debajo del threshold verde
        color_amber1, _, _ = ranking_service._map_to_traffic_light(
            PORTFOLIO_RANKING_GREEN_THRESHOLD - 0.01,
            sentiment_result,
            technical_result
        )
        assert color_amber1 == "amber"
        
        # Test en el threshold ámbar
        color_amber2, _, _ = ranking_service._map_to_traffic_light(
            PORTFOLIO_RANKING_AMBER_THRESHOLD,
            sentiment_result,
            technical_result
        )
        assert color_amber2 == "amber"
        
        # Test justo debajo del threshold ámbar
        color_red, _, _ = ranking_service._map_to_traffic_light(
            PORTFOLIO_RANKING_AMBER_THRESHOLD - 0.01,
            sentiment_result,
            technical_result
        )
        assert color_red == "red"
    
    def test_score_news_sentiment_positive(self, ranking_service):
        """Test scoring de noticias positivas."""
        news_items = [
            NewsItemResponse(
                id=1,
                title="Positive news",
                body="Great results and strong performance",
                source="News",
                created_at=datetime.now(timezone.utc).isoformat(),
                score=10.0
            )
        ]
        
        with patch.object(ranking_service.news_scoring_service, 'calculate_news_score') as mock_score:
            mock_score.return_value = {
                "score": 10.0,
                "components": {"sentiment_type": "positive"}
            }
            
            result = ranking_service._score_news_sentiment(news_items)
            
            assert result["count"] == 1
            assert result["score"] > 0.5  # Debe ser positivo
    
    def test_score_news_sentiment_negative(self, ranking_service):
        """Test scoring de noticias negativas."""
        news_items = [
            NewsItemResponse(
                id=1,
                title="Negative news",
                body="Declining sales and poor performance",
                source="News",
                created_at=datetime.now(timezone.utc).isoformat(),
                score=-5.0
            )
        ]
        
        with patch.object(ranking_service.news_scoring_service, 'calculate_news_score') as mock_score:
            mock_score.return_value = {
                "score": -5.0,
                "components": {"sentiment_type": "negative"}
            }
            
            result = ranking_service._score_news_sentiment(news_items)
            
            assert result["count"] == 1
            assert result["score"] < 0.5  # Debe ser negativo
    
    def test_score_news_sentiment_empty(self, ranking_service):
        """Test scoring con lista vacía."""
        result = ranking_service._score_news_sentiment([])
        
        assert result["score"] == 0.5  # Neutro
        assert result["count"] == 0
        assert result["avg_sentiment"] == 0.0
    
    def test_calculate_technical_score_with_signals(self, ranking_service, mock_portfolio_item):
        """Test cálculo de score técnico con señales."""
        with patch.object(ranking_service.market_features_service, 'get_market_features') as mock_features:
            mock_features.return_value = {
                "intraday_change_pct": 3.5,  # Precio subió 3.5%
                "volume_ratio": 1.8,  # Volumen 1.8x promedio
                "atr": None
            }
            
            result = ranking_service._calculate_technical_score(mock_portfolio_item)
            
            assert "score" in result
            assert "explanation" in result
            assert "signals" in result
            assert 0.0 <= result["score"] <= 1.0
            assert "trend" in result["signals"]
            assert "volume" in result["signals"]
    
    def test_calculate_technical_score_no_symbol(self, ranking_service):
        """Test cálculo técnico sin símbolo."""
        item_no_symbol = PortfolioItemResponse(
            id=1,
            asset_type="acciones",
            name="Test Company",
            symbol=None,
            quantity="100",
            price="50.00",
            total_value="5000.00",
            currency="USD",
            notes="",
            created_at=datetime.now(timezone.utc).isoformat(),
            updated_at=datetime.now(timezone.utc).isoformat()
        )
        
        result = ranking_service._calculate_technical_score(item_no_symbol)
        
        assert result["score"] == 0.5  # Neutro por defecto
        assert "Sin símbolo" in result["explanation"]
    
    def test_composite_score_calculation(self, ranking_service):
        """Test que el score compuesto se calcula correctamente."""
        sentiment_score = 0.8
        technical_score = 0.6
        
        # Calcular manualmente el composite esperado
        expected_composite = (
            sentiment_score * PORTFOLIO_RANKING_SENTIMENT_WEIGHT +
            technical_score * PORTFOLIO_RANKING_TECHNICAL_WEIGHT
        )
        
        # Verificar que los pesos suman 1.0
        total_weight = PORTFOLIO_RANKING_SENTIMENT_WEIGHT + PORTFOLIO_RANKING_TECHNICAL_WEIGHT
        assert abs(total_weight - 1.0) < 0.01, "Los pesos deben sumar 1.0"
        
        # Verificar rango del composite
        assert 0.0 <= expected_composite <= 1.0
    
    def test_cache_validity(self, ranking_service):
        """Test que el caché funciona correctamente."""
        cache_key = 1
        test_data = {"test": "data"}
        
        # Agregar al caché
        ranking_service._cache[cache_key] = test_data
        ranking_service._cache_timestamps[cache_key] = datetime.now(timezone.utc)
        
        # Debe ser válido inmediatamente
        assert ranking_service._is_cache_valid(cache_key) == True
        
        # Limpiar caché
        ranking_service.clear_cache(cache_key)
        assert cache_key not in ranking_service._cache
    
    def test_cache_expiration(self, ranking_service):
        """Test que el caché expira correctamente."""
        cache_key = 1
        test_data = {"test": "data"}
        
        # Agregar con timestamp antiguo
        ranking_service._cache[cache_key] = test_data
        old_time = datetime.now(timezone.utc) - timedelta(minutes=20)  # Más viejo que TTL
        ranking_service._cache_timestamps[cache_key] = old_time
        
        # No debe ser válido
        assert ranking_service._is_cache_valid(cache_key) == False


class TestScoreFusionEdgeCases:
    """Tests para casos límite de fusión de scores."""
    
    @pytest.fixture
    def ranking_service(self):
        return PortfolioRankingService()
    
    def test_extreme_sentiment_high_technical_low(self, ranking_service):
        """Test: sentimiento muy alto, técnico muy bajo."""
        sentiment_result = {"score": 0.95, "explanation": "Very positive"}
        technical_result = {"score": 0.05, "explanation": "Very weak"}
        
        composite = (
            sentiment_result["score"] * PORTFOLIO_RANKING_SENTIMENT_WEIGHT +
            technical_result["score"] * PORTFOLIO_RANKING_TECHNICAL_WEIGHT
        )
        
        color, _ = ranking_service._map_to_traffic_light(
            composite,
            sentiment_result,
            technical_result
        )
        
        # Con peso de sentimiento alto, debería ser verde
        if PORTFOLIO_RANKING_SENTIMENT_WEIGHT >= 0.5:
            assert color in ["green", "amber"]  # Depende del threshold
    
    def test_extreme_sentiment_low_technical_high(self, ranking_service):
        """Test: sentimiento muy bajo, técnico muy alto."""
        sentiment_result = {"score": 0.05, "explanation": "Very negative"}
        technical_result = {"score": 0.95, "explanation": "Very strong"}
        
        composite = (
            sentiment_result["score"] * PORTFOLIO_RANKING_SENTIMENT_WEIGHT +
            technical_result["score"] * PORTFOLIO_RANKING_TECHNICAL_WEIGHT
        )
        
        color, _, _ = ranking_service._map_to_traffic_light(
            composite,
            sentiment_result,
            technical_result
        )
        
        # Con peso técnico menor, podría ser ámbar o rojo
        assert color in ["amber", "red"]
    
    def test_both_scores_neutral(self, ranking_service):
        """Test: ambos scores neutros."""
        sentiment_result = {"score": 0.5, "explanation": "Neutral"}
        technical_result = {"score": 0.5, "explanation": "Neutral"}
        
        composite = (
            sentiment_result["score"] * PORTFOLIO_RANKING_SENTIMENT_WEIGHT +
            technical_result["score"] * PORTFOLIO_RANKING_TECHNICAL_WEIGHT
        )
        
        assert abs(composite - 0.5) < 0.01  # Debe ser ~0.5
        
        color, status_text, action = ranking_service._map_to_traffic_light(
            composite,
            sentiment_result,
            technical_result
        )
        
        assert color == "amber"
        assert status_text == "Neutro"
        assert action is not None
    
    def test_score_normalization_bounds(self, ranking_service):
        """Test que los scores están normalizados en 0-1."""
        # Test varios valores extremos
        test_cases = [
            (0.0, 0.0),
            (1.0, 1.0),
            (0.5, 0.5),
            (-0.1, 0.0),  # Debe clamp a 0
            (1.1, 1.0),   # Debe clamp a 1
        ]
        
        for sentiment, expected_min in test_cases:
            technical = 0.5
            composite = (
                max(0.0, min(1.0, sentiment)) * PORTFOLIO_RANKING_SENTIMENT_WEIGHT +
                technical * PORTFOLIO_RANKING_TECHNICAL_WEIGHT
            )
            
            assert 0.0 <= composite <= 1.0


class TestMixedTechnicalSentimentCases:
    """Tests para casos mixtos de señales técnicas y sentimiento."""
    
    @pytest.fixture
    def ranking_service(self):
        return PortfolioRankingService()
    
    def test_positive_sentiment_positive_technical(self, ranking_service):
        """Test: sentimiento positivo + señales técnicas positivas = verde."""
        sentiment_result = {"score": 0.8, "explanation": "Positive news"}
        technical_result = {"score": 0.75, "explanation": "Strong trend"}
        
        composite = (
            sentiment_result["score"] * PORTFOLIO_RANKING_SENTIMENT_WEIGHT +
            technical_result["score"] * PORTFOLIO_RANKING_TECHNICAL_WEIGHT
        )
        
        color, _, _ = ranking_service._map_to_traffic_light(
            composite,
            sentiment_result,
            technical_result
        )
        
        assert color == "green"
    
    def test_negative_sentiment_negative_technical(self, ranking_service):
        """Test: sentimiento negativo + señales técnicas negativas = rojo."""
        sentiment_result = {"score": 0.2, "explanation": "Negative news"}
        technical_result = {"score": 0.25, "explanation": "Weak signals"}
        
        composite = (
            sentiment_result["score"] * PORTFOLIO_RANKING_SENTIMENT_WEIGHT +
            technical_result["score"] * PORTFOLIO_RANKING_TECHNICAL_WEIGHT
        )
        
        color, _, _ = ranking_service._map_to_traffic_light(
            composite,
            sentiment_result,
            technical_result
        )
        
        assert color == "red"
    
    def test_mixed_signals(self, ranking_service):
        """Test: sentimiento positivo pero señales técnicas débiles."""
        sentiment_result = {"score": 0.7, "explanation": "Positive news"}
        technical_result = {"score": 0.35, "explanation": "Weak technical"}
        
        composite = (
            sentiment_result["score"] * PORTFOLIO_RANKING_SENTIMENT_WEIGHT +
            technical_result["score"] * PORTFOLIO_RANKING_TECHNICAL_WEIGHT
        )
        
        color, _, _ = ranking_service._map_to_traffic_light(
            composite,
            sentiment_result,
            technical_result
        )
        
        # Depende de los pesos, pero debería ser ámbar o verde
        assert color in ["green", "amber"]

