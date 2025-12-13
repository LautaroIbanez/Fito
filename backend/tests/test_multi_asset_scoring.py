"""
Tests para el servicio de scoring multi-asset diferenciado por tipo de activo.
Valida scoring específico para acciones, bonos, FX y commodities, y manejo de datos faltantes.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone, timedelta

from app.services.multi_asset_scoring_service import MultiAssetScoringService
from app.models import PortfolioItemResponse, NewsItemResponse


class TestMultiAssetScoringService:
    """Tests para MultiAssetScoringService."""
    
    @pytest.fixture
    def scoring_service(self):
        """Crea una instancia del servicio."""
        return MultiAssetScoringService()
    
    @pytest.fixture
    def mock_db(self):
        """Crea una sesión de base de datos mock."""
        return Mock()
    
    @pytest.fixture
    def stock_item(self):
        """Crea un item de acciones."""
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
    def bond_item(self):
        """Crea un item de bonos."""
        return PortfolioItemResponse(
            id=2,
            asset_type="bonos",
            name="US Treasury 10Y",
            symbol="US10Y",
            quantity="1000",
            price="98.50",
            total_value="98500.00",
            currency="USD",
            notes="",
            created_at=datetime.now(timezone.utc).isoformat(),
            updated_at=datetime.now(timezone.utc).isoformat()
        )
    
    @pytest.fixture
    def fx_item(self):
        """Crea un item de divisas."""
        return PortfolioItemResponse(
            id=3,
            asset_type="divisas",
            name="EUR/USD",
            symbol="EURUSD",
            quantity="10000",
            price="1.10",
            total_value="11000.00",
            currency="USD",
            notes="",
            created_at=datetime.now(timezone.utc).isoformat(),
            updated_at=datetime.now(timezone.utc).isoformat()
        )
    
    @pytest.fixture
    def commodity_item(self):
        """Crea un item de commodities."""
        return PortfolioItemResponse(
            id=4,
            asset_type="commodities",
            name="Gold",
            symbol="XAUUSD",
            quantity="10",
            price="2000.00",
            total_value="20000.00",
            currency="USD",
            notes="",
            created_at=datetime.now(timezone.utc).isoformat(),
            updated_at=datetime.now(timezone.utc).isoformat()
        )
    
    @pytest.fixture
    def positive_news(self):
        """Crea noticias positivas."""
        base_time = datetime.now(timezone.utc)
        return [
            NewsItemResponse(
                id=1,
                title="Strong earnings report",
                body="Company reports excellent quarterly results with strong growth",
                source="Financial News",
                created_at=(base_time - timedelta(hours=12)).isoformat(),
                score=8.5
            ),
            NewsItemResponse(
                id=2,
                title="Market gains momentum",
                body="Sector shows positive trends and investor confidence",
                source="Market Watch",
                created_at=(base_time - timedelta(hours=24)).isoformat(),
                score=7.0
            )
        ]
    
    @pytest.fixture
    def negative_news(self):
        """Crea noticias negativas."""
        base_time = datetime.now(timezone.utc)
        return [
            NewsItemResponse(
                id=3,
                title="Declining sales",
                body="Company faces challenges with decreasing revenue",
                source="Business News",
                created_at=(base_time - timedelta(hours=12)).isoformat(),
                score=-5.0
            )
        ]
    
    @pytest.fixture
    def no_news(self):
        """Lista vacía de noticias."""
        return []
    
    def test_stock_scoring_with_news(self, scoring_service, mock_db, stock_item, positive_news):
        """Test scoring para acciones con noticias disponibles."""
        with patch.object(scoring_service.news_scoring_service, 'calculate_news_score') as mock_score, \
             patch.object(scoring_service.market_features_service, 'get_market_features') as mock_features:
            
            # Mock scoring de noticias
            mock_score.return_value = {
                "score": 8.0,
                "components": {"sentiment_type": "positive"}
            }
            
            # Mock features de mercado
            mock_features.return_value = {
                "intraday_change_pct": 2.5,
                "volume_ratio": 1.5
            }
            
            result = scoring_service.calculate_asset_score(
                mock_db, stock_item, positive_news, lookback_hours=168
            )
            
            assert result["asset_type"] == "acciones"
            assert "composite_score" in result
            assert 0.0 <= result["composite_score"] <= 1.0
            assert "breakdown" in result
            assert "sentiment" in result["breakdown"]
            assert "technical" in result["breakdown"]
            assert "freshness" in result["breakdown"]
            assert "coverage" in result["breakdown"]
            assert "data_sufficiency" in result
            
            # Verificar pesos específicos para acciones
            assert result["breakdown"]["sentiment"]["weight"] == 0.4
            assert result["breakdown"]["technical"]["weight"] == 0.4
    
    def test_bond_scoring_with_news(self, scoring_service, mock_db, bond_item, positive_news):
        """Test scoring para bonos con noticias disponibles."""
        with patch.object(scoring_service.news_scoring_service, 'calculate_news_score') as mock_score:
            mock_score.return_value = {
                "score": 7.0,
                "components": {"sentiment_type": "positive"}
            }
            
            result = scoring_service.calculate_asset_score(
                mock_db, bond_item, positive_news, lookback_hours=168
            )
            
            assert result["asset_type"] == "bonos"
            assert "composite_score" in result
            # Verificar pesos específicos para bonos (más peso en macro)
            assert result["breakdown"]["sentiment"]["weight"] == 0.5
            assert result["breakdown"]["technical"]["weight"] == 0.3
    
    def test_fx_scoring_with_news(self, scoring_service, mock_db, fx_item, positive_news):
        """Test scoring para divisas con noticias disponibles."""
        with patch.object(scoring_service.news_scoring_service, 'calculate_news_score') as mock_score:
            mock_score.return_value = {
                "score": 6.5,
                "components": {"sentiment_type": "positive"}
            }
            
            result = scoring_service.calculate_asset_score(
                mock_db, fx_item, positive_news, lookback_hours=168
            )
            
            assert result["asset_type"] == "divisas"
            assert "composite_score" in result
            # Verificar pesos específicos para FX
            assert result["breakdown"]["sentiment"]["weight"] == 0.45
            assert result["breakdown"]["technical"]["weight"] == 0.35
    
    def test_commodity_scoring_with_news(self, scoring_service, mock_db, commodity_item, positive_news):
        """Test scoring para commodities con noticias disponibles."""
        with patch.object(scoring_service.news_scoring_service, 'calculate_news_score') as mock_score:
            mock_score.return_value = {
                "score": 7.5,
                "components": {"sentiment_type": "positive"}
            }
            
            result = scoring_service.calculate_asset_score(
                mock_db, commodity_item, positive_news, lookback_hours=168
            )
            
            assert result["asset_type"] == "commodities"
            assert "composite_score" in result
            # Verificar pesos balanceados para commodities
            assert result["breakdown"]["sentiment"]["weight"] == 0.4
            assert result["breakdown"]["technical"]["weight"] == 0.4
    
    def test_insufficient_data_marking(self, scoring_service, mock_db, stock_item, no_news):
        """Test que marca explícitamente 'datos insuficientes' cuando no hay noticias."""
        with patch.object(scoring_service.market_features_service, 'get_market_features') as mock_features:
            mock_features.return_value = {}  # Sin features de mercado
            
            result = scoring_service.calculate_asset_score(
                mock_db, stock_item, no_news, lookback_hours=168
            )
            
            # Verificar que marca datos insuficientes
            assert "data_sufficiency" in result
            assert result["data_sufficiency"]["sufficient"] == False
            assert "DATOS INSUFICIENTES" in result["data_sufficiency"]["message"] or \
                   "insufficient" in result["data_sufficiency"]["message"].lower()
            
            # Verificar que los breakdowns indican datos insuficientes
            assert result["breakdown"]["sentiment"]["details"]["data_quality"] == "insufficient"
            assert result["breakdown"]["coverage"]["details"]["data_quality"] in ["low", "insufficient"]
    
    def test_freshness_calculation(self, scoring_service, mock_db, stock_item):
        """Test cálculo de frescura de noticias."""
        base_time = datetime.now(timezone.utc)
        old_news = [
            NewsItemResponse(
                id=1,
                title="Old news",
                body="Very old news item",
                source="News",
                created_at=(base_time - timedelta(hours=200)).isoformat(),  # 8+ días
                score=5.0
            )
        ]
        
        fresh_news = [
            NewsItemResponse(
                id=2,
                title="Fresh news",
                body="Very recent news item",
                source="News",
                created_at=(base_time - timedelta(hours=2)).isoformat(),  # 2 horas
                score=5.0
            )
        ]
        
        # Noticias viejas deberían tener menor score de frescura
        with patch.object(scoring_service.news_scoring_service, 'calculate_news_score') as mock_score, \
             patch.object(scoring_service.market_features_service, 'get_market_features') as mock_features:
            mock_score.return_value = {
                "score": 5.0,
                "components": {"sentiment_type": "neutral"}
            }
            mock_features.return_value = {}
            
            result_old = scoring_service.calculate_asset_score(
                mock_db, stock_item, old_news, lookback_hours=168
            )
            result_fresh = scoring_service.calculate_asset_score(
                mock_db, stock_item, fresh_news, lookback_hours=168
            )
            
            freshness_old = result_old["breakdown"]["freshness"]["score"]
            freshness_fresh = result_fresh["breakdown"]["freshness"]["score"]
            
            assert freshness_fresh > freshness_old, "Noticias frescas deben tener mayor score de frescura"
    
    def test_coverage_breakdown(self, scoring_service, mock_db, stock_item, positive_news):
        """Test desglose de cobertura de datos."""
        with patch.object(scoring_service.news_scoring_service, 'calculate_news_score') as mock_score, \
             patch.object(scoring_service.market_features_service, 'get_market_features') as mock_features:
            mock_score.return_value = {
                "score": 7.0,
                "components": {"sentiment_type": "positive"}
            }
            mock_features.return_value = {
                "intraday_change_pct": 2.0,
                "volume_ratio": 1.3
            }
            
            result = scoring_service.calculate_asset_score(
                mock_db, stock_item, positive_news, lookback_hours=168
            )
            
            coverage = result["breakdown"]["coverage"]
            assert "score" in coverage
            assert "details" in coverage
            assert "news_count" in coverage["details"]
            assert "technical_signals_count" in coverage["details"]
            assert "data_quality" in coverage["details"]
    
    def test_contribution_breakdown(self, scoring_service, mock_db, stock_item, positive_news):
        """Test que las contribuciones se calculan correctamente."""
        with patch.object(scoring_service.news_scoring_service, 'calculate_news_score') as mock_score, \
             patch.object(scoring_service.market_features_service, 'get_market_features') as mock_features:
            mock_score.return_value = {
                "score": 8.0,
                "components": {"sentiment_type": "positive"}
            }
            mock_features.return_value = {
                "intraday_change_pct": 3.0,
                "volume_ratio": 1.8
            }
            
            result = scoring_service.calculate_asset_score(
                mock_db, stock_item, positive_news, lookback_hours=168
            )
            
            # Verificar que las contribuciones están presentes
            sentiment_contrib = result["breakdown"]["sentiment"]["contribution"]
            technical_contrib = result["breakdown"]["technical"]["contribution"]
            freshness_contrib = result["breakdown"]["freshness"]["contribution"]
            coverage_contrib = result["breakdown"]["coverage"]["contribution"]
            
            # Las contribuciones deben ser score * weight
            assert abs(sentiment_contrib - (result["breakdown"]["sentiment"]["score"] * 0.4)) < 0.01
            assert abs(technical_contrib - (result["breakdown"]["technical"]["score"] * 0.4)) < 0.01
            
            # La suma de contribuciones debe aproximarse al composite_score
            total_contrib = sentiment_contrib + technical_contrib + freshness_contrib + coverage_contrib
            assert abs(total_contrib - result["composite_score"]) < 0.01
    
    def test_generic_asset_type(self, scoring_service, mock_db):
        """Test scoring para tipo de activo genérico/desconocido."""
        generic_item = PortfolioItemResponse(
            id=5,
            asset_type="otros",
            name="Unknown Asset",
            symbol="UNK",
            quantity="100",
            price="50.00",
            total_value="5000.00",
            currency="USD",
            notes="",
            created_at=datetime.now(timezone.utc).isoformat(),
            updated_at=datetime.now(timezone.utc).isoformat()
        )
        
        with patch.object(scoring_service.news_scoring_service, 'calculate_news_score') as mock_score:
            mock_score.return_value = {
                "score": 5.0,
                "components": {"sentiment_type": "neutral"}
            }
            
            result = scoring_service.calculate_asset_score(
                mock_db, generic_item, [], lookback_hours=168
            )
            
            assert result["asset_type"] == "genérico"
            assert "composite_score" in result
            assert "breakdown" in result
    
    def test_sentiment_breakdown_details(self, scoring_service, mock_db, stock_item, positive_news):
        """Test que el desglose de sentimiento incluye todos los detalles."""
        with patch.object(scoring_service.news_scoring_service, 'calculate_news_score') as mock_score, \
             patch.object(scoring_service.market_features_service, 'get_market_features') as mock_features:
            mock_score.return_value = {
                "score": 8.0,
                "components": {"sentiment_type": "positive"}
            }
            mock_features.return_value = {}
            
            result = scoring_service.calculate_asset_score(
                mock_db, stock_item, positive_news, lookback_hours=168
            )
            
            sentiment_details = result["breakdown"]["sentiment"]["details"]
            assert "score" in sentiment_details
            assert "news_count" in sentiment_details
            assert "positive_count" in sentiment_details
            assert "negative_count" in sentiment_details
            assert "neutral_count" in sentiment_details
            assert "avg_sentiment" in sentiment_details
            assert "data_quality" in sentiment_details
            assert "message" in sentiment_details
    
    def test_technical_breakdown_for_stocks(self, scoring_service, mock_db, stock_item, positive_news):
        """Test desglose técnico específico para acciones."""
        with patch.object(scoring_service.news_scoring_service, 'calculate_news_score') as mock_score, \
             patch.object(scoring_service.market_features_service, 'get_market_features') as mock_features:
            mock_score.return_value = {
                "score": 7.0,
                "components": {"sentiment_type": "positive"}
            }
            mock_features.return_value = {
                "intraday_change_pct": 2.5,
                "volume_ratio": 1.5
            }
            
            result = scoring_service.calculate_asset_score(
                mock_db, stock_item, positive_news, lookback_hours=168
            )
            
            technical_details = result["breakdown"]["technical"]["details"]
            assert "score" in technical_details
            assert "signals" in technical_details
            assert "data_quality" in technical_details
            assert "message" in technical_details
            
            # Para acciones, debería haber señales RSI, volumen, tendencia
            signals = technical_details.get("signals", {})
            if signals:
                assert any(key in signals for key in ["rsi", "volume", "trend"])


class TestDataInsufficiencyHandling:
    """Tests para validar manejo explícito de datos insuficientes."""
    
    @pytest.fixture
    def scoring_service(self):
        return MultiAssetScoringService()
    
    @pytest.fixture
    def mock_db(self):
        return Mock()
    
    def test_no_news_no_technical_data(self, scoring_service, mock_db):
        """Test que marca datos insuficientes cuando no hay noticias ni datos técnicos."""
        item = PortfolioItemResponse(
            id=1,
            asset_type="acciones",
            name="Test Stock",
            symbol="TEST",
            quantity="100",
            price="50.00",
            total_value="5000.00",
            currency="USD",
            notes="",
            created_at=datetime.now(timezone.utc).isoformat(),
            updated_at=datetime.now(timezone.utc).isoformat()
        )
        
        with patch.object(scoring_service.market_features_service, 'get_market_features') as mock_features:
            mock_features.return_value = {}  # Sin datos técnicos
            
            result = scoring_service.calculate_asset_score(
                mock_db, item, [], lookback_hours=168
            )
            
            assert result["data_sufficiency"]["sufficient"] == False
            assert "insufficient" in result["data_sufficiency"]["message"].lower() or \
                   "DATOS INSUFICIENTES" in result["data_sufficiency"]["message"]
    
    def test_insufficient_news_but_technical_available(self, scoring_service, mock_db):
        """Test con pocas noticias pero datos técnicos disponibles."""
        item = PortfolioItemResponse(
            id=1,
            asset_type="acciones",
            name="Test Stock",
            symbol="TEST",
            quantity="100",
            price="50.00",
            total_value="5000.00",
            currency="USD",
            notes="",
            created_at=datetime.now(timezone.utc).isoformat(),
            updated_at=datetime.now(timezone.utc).isoformat()
        )
        
        # Solo 1 noticia (insuficiente según criterios)
        news = [
            NewsItemResponse(
                id=1,
                title="Single news",
                body="Only one news item available",
                source="News",
                created_at=datetime.now(timezone.utc).isoformat(),
                score=5.0
            )
        ]
        
        with patch.object(scoring_service.news_scoring_service, 'calculate_news_score') as mock_score, \
             patch.object(scoring_service.market_features_service, 'get_market_features') as mock_features:
            mock_score.return_value = {
                "score": 5.0,
                "components": {"sentiment_type": "neutral"}
            }
            mock_features.return_value = {
                "intraday_change_pct": 2.0,
                "volume_ratio": 1.2
            }
            
            result = scoring_service.calculate_asset_score(
                mock_db, item, news, lookback_hours=168
            )
            
            # Con datos técnicos disponibles, puede ser suficiente
            # pero con calidad baja
            assert result["breakdown"]["sentiment"]["details"]["data_quality"] in ["low", "insufficient"]
            assert result["breakdown"]["coverage"]["details"]["data_quality"] in ["low", "medium"]

