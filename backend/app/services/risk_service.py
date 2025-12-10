"""Servicio para cálculo de métricas de riesgo y concentración."""
import logging
from typing import Dict, List, Tuple
from app.models import PortfolioItemResponse
from collections import defaultdict

logger = logging.getLogger(__name__)

# Volatilidades estimadas anuales por tipo de activo (en %)
ASSET_VOLATILITY = {
    "acciones": 20.0,  # 20% anual típico para acciones
    "bonos": 5.0,      # 5% anual típico para bonos
    "etf": 15.0,       # 15% anual típico para ETF
    "fondos": 12.0,    # 12% anual típico para fondos
    "divisas": 10.0,   # 10% anual típico para divisas
    "otros": 15.0      # 15% anual por defecto
}

# Z-score para diferentes niveles de confianza (para VaR)
VAR_Z_SCORE_95 = 1.645  # 95% de confianza
VAR_Z_SCORE_99 = 2.326  # 99% de confianza


def parse_value(value_str: str) -> float:
    """Parsea un valor numérico desde string, manejando comas y espacios."""
    if not value_str:
        return 0.0
    try:
        # Remover comas y espacios
        cleaned = str(value_str).replace(',', '').replace(' ', '').strip()
        return float(cleaned)
    except (ValueError, AttributeError):
        return 0.0


class RiskService:
    """Servicio para calcular métricas de riesgo y concentración."""
    
    def calculate_portfolio_value(self, portfolio_items: List[PortfolioItemResponse]) -> float:
        """Calcula el valor total del portafolio."""
        total = 0.0
        for item in portfolio_items:
            if item.total_value:
                total += parse_value(item.total_value)
        return total
    
    def calculate_exposure_by_asset(self, portfolio_items: List[PortfolioItemResponse]) -> List[Dict]:
        """Calcula exposición por activo individual."""
        total_value = self.calculate_portfolio_value(portfolio_items)
        if total_value == 0:
            return []
        
        exposures = []
        for item in portfolio_items:
            asset_value = parse_value(item.total_value) if item.total_value else 0.0
            if asset_value > 0:
                percentage = (asset_value / total_value) * 100
                exposures.append({
                    "id": item.id,
                    "name": item.name,
                    "symbol": item.symbol,
                    "asset_type": item.asset_type,
                    "value": asset_value,
                    "percentage": round(percentage, 2),
                    "currency": item.currency or "USD"
                })
        
        # Ordenar por porcentaje descendente
        exposures.sort(key=lambda x: x["percentage"], reverse=True)
        return exposures
    
    def calculate_exposure_by_sector(self, portfolio_items: List[PortfolioItemResponse]) -> List[Dict]:
        """Calcula exposición por sector (tipo de activo)."""
        total_value = self.calculate_portfolio_value(portfolio_items)
        if total_value == 0:
            return []
        
        sector_values = defaultdict(float)
        sector_counts = defaultdict(int)
        
        for item in portfolio_items:
            asset_value = parse_value(item.total_value) if item.total_value else 0.0
            if asset_value > 0:
                sector_values[item.asset_type] += asset_value
                sector_counts[item.asset_type] += 1
        
        exposures = []
        for sector, value in sorted(sector_values.items(), key=lambda x: x[1], reverse=True):
            percentage = (value / total_value) * 100
            exposures.append({
                "sector": sector,
                "value": value,
                "percentage": round(percentage, 2),
                "asset_count": sector_counts[sector]
            })
        
        return exposures
    
    def get_top_concentrations(self, portfolio_items: List[PortfolioItemResponse], top_n: int = 5) -> List[Dict]:
        """Obtiene las top N concentraciones por activo."""
        exposures = self.calculate_exposure_by_asset(portfolio_items)
        return exposures[:top_n]
    
    def calculate_volatility(self, portfolio_items: List[PortfolioItemResponse], days: int = 30) -> Dict:
        """
        Calcula volatilidad estimada del portafolio para N días.
        Usa volatilidades estimadas por tipo de activo.
        """
        total_value = self.calculate_portfolio_value(portfolio_items)
        if total_value == 0:
            return {
                "volatility_30d": 0.0,
                "volatility_90d": 0.0,
                "annual_volatility": 0.0
            }
        
        # Calcular volatilidad ponderada del portafolio
        weighted_vol = 0.0
        
        for item in portfolio_items:
            asset_value = parse_value(item.total_value) if item.total_value else 0.0
            if asset_value > 0:
                weight = asset_value / total_value
                asset_vol = ASSET_VOLATILITY.get(item.asset_type, 15.0)
                weighted_vol += weight * asset_vol
        
        annual_volatility = weighted_vol
        
        # Convertir a volatilidad para N días usando square root of time rule
        # Vol_Ndías = Vol_anual * sqrt(N_días / 365)
        import math
        volatility_30d = annual_volatility * math.sqrt(30 / 365)
        volatility_90d = annual_volatility * math.sqrt(90 / 365)
        
        return {
            "volatility_30d": round(volatility_30d, 2),
            "volatility_90d": round(volatility_90d, 2),
            "annual_volatility": round(annual_volatility, 2)
        }
    
    def calculate_var(self, portfolio_items: List[PortfolioItemResponse], days: int = 30, confidence: float = 0.95) -> Dict:
        """
        Calcula Value at Risk (VaR) estimado.
        
        VaR = Portfolio_Value * Volatility * sqrt(days/365) * Z_score
        """
        total_value = self.calculate_portfolio_value(portfolio_items)
        if total_value == 0:
            return {
                "var_30d_95": 0.0,
                "var_90d_95": 0.0,
                "var_30d_99": 0.0,
                "var_90d_99": 0.0
            }
        
        vol_metrics = self.calculate_volatility(portfolio_items)
        annual_vol = vol_metrics["annual_volatility"] / 100  # Convertir a decimal
        
        import math
        z_score_95 = VAR_Z_SCORE_95
        z_score_99 = VAR_Z_SCORE_99
        
        # VaR para 30 días
        var_30d_95 = total_value * annual_vol * math.sqrt(30 / 365) * z_score_95
        var_30d_99 = total_value * annual_vol * math.sqrt(30 / 365) * z_score_99
        
        # VaR para 90 días
        var_90d_95 = total_value * annual_vol * math.sqrt(90 / 365) * z_score_95
        var_90d_99 = total_value * annual_vol * math.sqrt(90 / 365) * z_score_99
        
        return {
            "var_30d_95": round(var_30d_95, 2),
            "var_90d_95": round(var_90d_95, 2),
            "var_30d_99": round(var_30d_99, 2),
            "var_90d_99": round(var_90d_99, 2),
            "portfolio_value": round(total_value, 2)
        }
    
    def calculate_risk_dashboard(self, portfolio_items: List[PortfolioItemResponse], top_n: int = 5) -> Dict:
        """
        Calcula todas las métricas del dashboard de riesgo.
        """
        if not portfolio_items:
            return {
                "portfolio_value": 0.0,
                "exposure_by_asset": [],
                "exposure_by_sector": [],
                "top_concentrations": [],
                "volatility": {
                    "volatility_30d": 0.0,
                    "volatility_90d": 0.0,
                    "annual_volatility": 0.0
                },
                "var": {
                    "var_30d_95": 0.0,
                    "var_90d_95": 0.0,
                    "var_30d_99": 0.0,
                    "var_90d_99": 0.0,
                    "portfolio_value": 0.0
                }
            }
        
        total_value = self.calculate_portfolio_value(portfolio_items)
        exposure_by_asset = self.calculate_exposure_by_asset(portfolio_items)
        exposure_by_sector = self.calculate_exposure_by_sector(portfolio_items)
        top_concentrations = self.get_top_concentrations(portfolio_items, top_n)
        volatility = self.calculate_volatility(portfolio_items)
        var = self.calculate_var(portfolio_items)
        
        return {
            "portfolio_value": round(total_value, 2),
            "exposure_by_asset": exposure_by_asset,
            "exposure_by_sector": exposure_by_sector,
            "top_concentrations": top_concentrations,
            "volatility": volatility,
            "var": var
        }



