"""Tests para el servicio de cálculo de riesgo."""
import pytest
from app.services.risk_service import RiskService, parse_value
from app.models import PortfolioItemResponse


class TestParseValue:
    """Tests para parsing de valores."""
    
    def test_parse_normal_value(self):
        assert parse_value("1000.50") == 1000.50
    
    def test_parse_value_with_comma(self):
        assert parse_value("1,000.50") == 1000.50
    
    def test_parse_value_with_spaces(self):
        assert parse_value("1 000.50") == 1000.50
    
    def test_parse_empty_string(self):
        assert parse_value("") == 0.0
    
    def test_parse_none(self):
        assert parse_value(None) == 0.0


class TestPortfolioValue:
    """Tests para cálculo de valor del portafolio."""
    
    def test_empty_portfolio(self):
        service = RiskService()
        value = service.calculate_portfolio_value([])
        assert value == 0.0
    
    def test_single_asset(self):
        service = RiskService()
        items = [
            PortfolioItemResponse(
                id=1,
                asset_type="acciones",
                name="Test Asset",
                symbol="TEST",
                quantity="100",
                price="10",
                total_value="1000.00",
                currency="USD",
                notes=None,
                created_at="2025-12-01T10:00:00",
                updated_at="2025-12-01T10:00:00"
            )
        ]
        value = service.calculate_portfolio_value(items)
        assert value == 1000.0
    
    def test_multiple_assets(self):
        service = RiskService()
        items = [
            PortfolioItemResponse(
                id=1,
                asset_type="acciones",
                name="Asset 1",
                symbol=None,
                quantity=None,
                price=None,
                total_value="1000.00",
                currency="USD",
                notes=None,
                created_at="2025-12-01T10:00:00",
                updated_at="2025-12-01T10:00:00"
            ),
            PortfolioItemResponse(
                id=2,
                asset_type="bonos",
                name="Asset 2",
                symbol=None,
                quantity=None,
                price=None,
                total_value="2000.00",
                currency="USD",
                notes=None,
                created_at="2025-12-01T10:00:00",
                updated_at="2025-12-01T10:00:00"
            )
        ]
        value = service.calculate_portfolio_value(items)
        assert value == 3000.0


class TestExposureByAsset:
    """Tests para exposición por activo."""
    
    def test_empty_portfolio(self):
        service = RiskService()
        exposures = service.calculate_exposure_by_asset([])
        assert exposures == []
    
    def test_exposure_percentages(self):
        service = RiskService()
        items = [
            PortfolioItemResponse(
                id=1,
                asset_type="acciones",
                name="Asset 1",
                symbol="A1",
                quantity=None,
                price=None,
                total_value="1000.00",
                currency="USD",
                notes=None,
                created_at="2025-12-01T10:00:00",
                updated_at="2025-12-01T10:00:00"
            ),
            PortfolioItemResponse(
                id=2,
                asset_type="bonos",
                name="Asset 2",
                symbol="A2",
                quantity=None,
                price=None,
                total_value="2000.00",
                currency="USD",
                notes=None,
                created_at="2025-12-01T10:00:00",
                updated_at="2025-12-01T10:00:00"
            )
        ]
        exposures = service.calculate_exposure_by_asset(items)
        
        assert len(exposures) == 2
        assert exposures[0]["percentage"] == pytest.approx(66.67, abs=0.01)
        assert exposures[1]["percentage"] == pytest.approx(33.33, abs=0.01)
        assert exposures[0]["value"] == 2000.0
        assert exposures[1]["value"] == 1000.0


class TestExposureBySector:
    """Tests para exposición por sector."""
    
    def test_empty_portfolio(self):
        service = RiskService()
        exposures = service.calculate_exposure_by_sector([])
        assert exposures == []
    
    def test_sector_grouping(self):
        service = RiskService()
        items = [
            PortfolioItemResponse(
                id=1,
                asset_type="acciones",
                name="Stock 1",
                symbol=None,
                quantity=None,
                price=None,
                total_value="1000.00",
                currency="USD",
                notes=None,
                created_at="2025-12-01T10:00:00",
                updated_at="2025-12-01T10:00:00"
            ),
            PortfolioItemResponse(
                id=2,
                asset_type="acciones",
                name="Stock 2",
                symbol=None,
                quantity=None,
                price=None,
                total_value="2000.00",
                currency="USD",
                notes=None,
                created_at="2025-12-01T10:00:00",
                updated_at="2025-12-01T10:00:00"
            ),
            PortfolioItemResponse(
                id=3,
                asset_type="bonos",
                name="Bond 1",
                symbol=None,
                quantity=None,
                price=None,
                total_value="1000.00",
                currency="USD",
                notes=None,
                created_at="2025-12-01T10:00:00",
                updated_at="2025-12-01T10:00:00"
            )
        ]
        exposures = service.calculate_exposure_by_sector(items)
        
        assert len(exposures) == 2
        assert exposures[0]["sector"] == "acciones"
        assert exposures[0]["percentage"] == pytest.approx(75.0, abs=0.01)
        assert exposures[0]["asset_count"] == 2
        assert exposures[1]["sector"] == "bonos"
        assert exposures[1]["percentage"] == pytest.approx(25.0, abs=0.01)
        assert exposures[1]["asset_count"] == 1


class TestTopConcentrations:
    """Tests para top concentraciones."""
    
    def test_top_n_concentrations(self):
        service = RiskService()
        items = [
            PortfolioItemResponse(
                id=i,
                asset_type="acciones",
                name=f"Asset {i}",
                symbol=f"A{i}",
                quantity=None,
                price=None,
                total_value=f"{i * 1000}.00",
                currency="USD",
                notes=None,
                created_at="2025-12-01T10:00:00",
                updated_at="2025-12-01T10:00:00"
            )
            for i in range(1, 6)
        ]
        
        top = service.get_top_concentrations(items, top_n=3)
        
        assert len(top) == 3
        assert top[0]["name"] == "Asset 5"
        assert top[0]["value"] == 5000.0
        assert top[1]["name"] == "Asset 4"
        assert top[2]["name"] == "Asset 3"


class TestVolatility:
    """Tests para cálculo de volatilidad."""
    
    def test_empty_portfolio_volatility(self):
        service = RiskService()
        vol = service.calculate_volatility([])
        assert vol["volatility_30d"] == 0.0
        assert vol["volatility_90d"] == 0.0
        assert vol["annual_volatility"] == 0.0
    
    def test_single_asset_volatility(self):
        service = RiskService()
        items = [
            PortfolioItemResponse(
                id=1,
                asset_type="acciones",
                name="Stock",
                symbol=None,
                quantity=None,
                price=None,
                total_value="1000.00",
                currency="USD",
                notes=None,
                created_at="2025-12-01T10:00:00",
                updated_at="2025-12-01T10:00:00"
            )
        ]
        vol = service.calculate_volatility(items)
        
        assert vol["annual_volatility"] == pytest.approx(20.0, abs=0.1)
        assert vol["volatility_30d"] > 0
        assert vol["volatility_90d"] > vol["volatility_30d"]
    
    def test_mixed_portfolio_volatility(self):
        service = RiskService()
        items = [
            PortfolioItemResponse(
                id=1,
                asset_type="acciones",
                name="Stock",
                symbol=None,
                quantity=None,
                price=None,
                total_value="1000.00",
                currency="USD",
                notes=None,
                created_at="2025-12-01T10:00:00",
                updated_at="2025-12-01T10:00:00"
            ),
            PortfolioItemResponse(
                id=2,
                asset_type="bonos",
                name="Bond",
                symbol=None,
                quantity=None,
                price=None,
                total_value="1000.00",
                currency="USD",
                notes=None,
                created_at="2025-12-01T10:00:00",
                updated_at="2025-12-01T10:00:00"
            )
        ]
        vol = service.calculate_volatility(items)
        
        # Volatilidad ponderada: 50% * 20% + 50% * 5% = 12.5%
        assert vol["annual_volatility"] == pytest.approx(12.5, abs=0.1)


class TestVaR:
    """Tests para cálculo de VaR."""
    
    def test_empty_portfolio_var(self):
        service = RiskService()
        var = service.calculate_var([])
        assert var["var_30d_95"] == 0.0
        assert var["var_90d_95"] == 0.0
    
    def test_var_calculation(self):
        service = RiskService()
        items = [
            PortfolioItemResponse(
                id=1,
                asset_type="acciones",
                name="Stock",
                symbol=None,
                quantity=None,
                price=None,
                total_value="10000.00",
                currency="USD",
                notes=None,
                created_at="2025-12-01T10:00:00",
                updated_at="2025-12-01T10:00:00"
            )
        ]
        var = service.calculate_var(items)
        
        assert var["portfolio_value"] == 10000.0
        assert var["var_30d_95"] > 0
        assert var["var_90d_95"] > var["var_30d_95"]
        assert var["var_30d_99"] > var["var_30d_95"]
        assert var["var_90d_99"] > var["var_90d_95"]


class TestRiskDashboard:
    """Tests para cálculo completo del dashboard."""
    
    def test_empty_dashboard(self):
        service = RiskService()
        dashboard = service.calculate_risk_dashboard([])
        
        assert dashboard["portfolio_value"] == 0.0
        assert dashboard["exposure_by_asset"] == []
        assert dashboard["exposure_by_sector"] == []
        assert dashboard["top_concentrations"] == []
        assert dashboard["volatility"]["annual_volatility"] == 0.0
        assert dashboard["var"]["var_30d_95"] == 0.0
    
    def test_complete_dashboard(self):
        service = RiskService()
        items = [
            PortfolioItemResponse(
                id=1,
                asset_type="acciones",
                name="Stock 1",
                symbol="S1",
                quantity=None,
                price=None,
                total_value="5000.00",
                currency="USD",
                notes=None,
                created_at="2025-12-01T10:00:00",
                updated_at="2025-12-01T10:00:00"
            ),
            PortfolioItemResponse(
                id=2,
                asset_type="bonos",
                name="Bond 1",
                symbol="B1",
                quantity=None,
                price=None,
                total_value="3000.00",
                currency="USD",
                notes=None,
                created_at="2025-12-01T10:00:00",
                updated_at="2025-12-01T10:00:00"
            ),
            PortfolioItemResponse(
                id=3,
                asset_type="etf",
                name="ETF 1",
                symbol="E1",
                quantity=None,
                price=None,
                total_value="2000.00",
                currency="USD",
                notes=None,
                created_at="2025-12-01T10:00:00",
                updated_at="2025-12-01T10:00:00"
            )
        ]
        
        dashboard = service.calculate_risk_dashboard(items, top_n=2)
        
        assert dashboard["portfolio_value"] == 10000.0
        assert len(dashboard["exposure_by_asset"]) == 3
        assert len(dashboard["exposure_by_sector"]) == 3
        assert len(dashboard["top_concentrations"]) == 2
        assert dashboard["top_concentrations"][0]["name"] == "Stock 1"
        assert dashboard["volatility"]["annual_volatility"] > 0
        assert dashboard["var"]["var_30d_95"] > 0

