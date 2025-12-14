"""Servicio para obtener datos de precio y volumen de activos."""
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import httpx

logger = logging.getLogger(__name__)


class PriceDataService:
    """Servicio para obtener datos de precio y volumen desde APIs externas."""
    
    def __init__(self):
        self.base_url = "https://query1.finance.yahoo.com/v8/finance/chart"
        self.timeout = 30
    
    async def get_price_data(
        self, 
        symbol: str, 
        period: str = "1mo",
        interval: str = "1d"
    ) -> Dict[str, Any]:
        """
        Obtiene datos de precio y volumen para un símbolo.
        
        Args:
            symbol: Símbolo del activo (ej: 'AAPL', 'TGSU2.BA')
            period: Período de datos ('1d', '5d', '1mo', '3mo', '6mo', '1y', '2y', '5y', '10y', 'ytd', 'max')
            interval: Intervalo de datos ('1m', '2m', '5m', '15m', '30m', '60m', '90m', '1h', '1d', '5d', '1wk', '1mo', '3mo')
        
        Returns:
            Dict con datos de precio y volumen
        """
        try:
            # Construir URL
            url = f"{self.base_url}/{symbol}"
            
            params = {
                "period1": None,  # Se calculará según el período
                "period2": int(datetime.now().timestamp()),
                "interval": interval,
                "includePrePost": "false",
                "events": "div,splits"
            }
            
            # Calcular period1 según el período solicitado
            period_days = {
                "1d": 1,
                "5d": 5,
                "1mo": 30,
                "3mo": 90,
                "6mo": 180,
                "1y": 365,
                "2y": 730,
                "5y": 1825,
                "10y": 3650,
                "ytd": None,  # Year to date
                "max": None
            }
            
            if period in period_days:
                days = period_days[period]
                if days:
                    params["period1"] = int((datetime.now() - timedelta(days=days)).timestamp())
                else:
                    # Para ytd o max, usar un valor por defecto
                    params["period1"] = int((datetime.now() - timedelta(days=365)).timestamp())
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
            
            # Procesar respuesta de Yahoo Finance
            if "chart" not in data or "result" not in data["chart"]:
                raise ValueError("Formato de respuesta inválido de Yahoo Finance")
            
            result = data["chart"]["result"][0]
            
            # Extraer datos
            timestamps = result.get("timestamp", [])
            indicators = result.get("indicators", {})
            quote = indicators.get("quote", [{}])[0]
            
            open_prices = quote.get("open", [])
            high_prices = quote.get("high", [])
            low_prices = quote.get("low", [])
            close_prices = quote.get("close", [])
            volumes = quote.get("volume", [])
            
            # Construir lista de datos OHLCV
            price_data = []
            for i in range(len(timestamps)):
                if close_prices[i] is not None:
                    price_data.append({
                        "date": datetime.fromtimestamp(timestamps[i]).isoformat(),
                        "timestamp": timestamps[i],
                        "open": open_prices[i] if i < len(open_prices) and open_prices[i] is not None else close_prices[i],
                        "high": high_prices[i] if i < len(high_prices) and high_prices[i] is not None else close_prices[i],
                        "low": low_prices[i] if i < len(low_prices) and low_prices[i] is not None else close_prices[i],
                        "close": close_prices[i],
                        "volume": volumes[i] if i < len(volumes) and volumes[i] is not None else 0
                    })
            
            # Obtener metadatos
            meta = result.get("meta", {})
            current_price = close_prices[-1] if close_prices else None
            
            return {
                "symbol": symbol,
                "current_price": current_price,
                "currency": meta.get("currency", "USD"),
                "exchange": meta.get("exchangeName", ""),
                "data": price_data,
                "period": period,
                "interval": interval,
                "data_points": len(price_data)
            }
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Error HTTP al obtener datos de precio para {symbol}: {e}")
            raise ValueError(f"No se pudieron obtener datos para el símbolo {symbol}. Verifica que el símbolo sea correcto.")
        except httpx.TimeoutException:
            logger.error(f"Timeout al obtener datos de precio para {symbol}")
            raise ValueError("Timeout al obtener datos de precio. Intenta nuevamente más tarde.")
        except Exception as e:
            logger.error(f"Error inesperado al obtener datos de precio para {symbol}: {e}", exc_info=True)
            raise ValueError(f"Error al obtener datos de precio: {str(e)}")
    
    def format_symbol_for_yahoo(self, symbol: str, asset_type: str) -> str:
        """
        Formatea el símbolo según el tipo de activo para Yahoo Finance.
        
        Args:
            symbol: Símbolo del activo
            asset_type: Tipo de activo (ACCIONES, BONOS, etc.)
        
        Returns:
            Símbolo formateado para Yahoo Finance
        """
        # Para acciones argentinas, agregar .BA
        if asset_type == "ACCIONES" and not symbol.endswith(".BA") and not "." in symbol:
            # Verificar si es una acción argentina (heurística simple)
            # Si el símbolo tiene 4-5 caracteres y no tiene punto, probablemente es argentina
            if len(symbol) >= 4 and len(symbol) <= 5:
                return f"{symbol}.BA"
        
        return symbol
