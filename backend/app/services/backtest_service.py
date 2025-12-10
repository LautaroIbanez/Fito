"""Servicio para ejecutar backtests de estrategias basadas en noticias."""
import logging
import json
from typing import List, Dict, Tuple, Optional
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session

from app.database import BacktestRule, NewsItem, PortfolioItem
from app.models import NewsItemResponse, PortfolioItemResponse
from app.services.news_scoring_service import NewsScoringService
from app.config import BACKTEST_DEFAULT_INITIAL_CAPITAL, BACKTEST_COMMISSION_RATE

logger = logging.getLogger(__name__)


class Trade:
    """Representa un trade individual."""
    def __init__(self, entry_date: datetime, entry_price: float, symbol: str, news_id: int):
        self.entry_date = entry_date
        self.entry_price = entry_price
        self.symbol = symbol
        self.news_id = news_id
        self.exit_date: Optional[datetime] = None
        self.exit_price: Optional[float] = None
        self.pnl: Optional[float] = None
        self.pnl_pct: Optional[float] = None
        self.is_open = True
    
    def close(self, exit_date: datetime, exit_price: float, commission_rate: float = 0.001):
        """Cierra el trade y calcula PnL."""
        self.exit_date = exit_date
        self.exit_price = exit_price
        self.is_open = False
        
        # Calcular PnL con comisión
        commission = self.entry_price * commission_rate
        exit_commission = exit_price * commission_rate
        self.pnl = (exit_price - self.entry_price) - commission - exit_commission
        self.pnl_pct = ((exit_price - self.entry_price) / self.entry_price) * 100 - (commission_rate * 200)


class BacktestService:
    """Servicio para ejecutar backtests."""
    
    def __init__(self):
        self.scoring_service = NewsScoringService()
    
    def get_historical_price_data(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[datetime, float]:
        """
        Obtiene datos históricos de precio.
        
        Nota: Esta es una implementación simulada. En producción, integrar con API de precios.
        Para esta versión, genera datos simulados basados en noticias.
        """
        # En producción, aquí obtendrías datos reales de Alpha Vantage, Yahoo Finance, etc.
        # Por ahora, retornamos un diccionario vacío que se completará con datos simulados
        logger.warning(f"Usando datos de precio simulados para {symbol}. "
                      "En producción, integrar con API de precios real.")
        return {}
    
    def simulate_price_data(
        self,
        symbol: str,
        base_price: float,
        dates: List[datetime],
        news_impact_factor: float = 0.02
    ) -> Dict[datetime, float]:
        """
        Simula datos de precio basados en noticias y volatilidad.
        
        Args:
            symbol: Símbolo del activo
            base_price: Precio base inicial
            dates: Lista de fechas para las que generar precios
            news_impact_factor: Factor de impacto de noticias (2% por defecto)
        
        Returns:
            Diccionario de fecha -> precio
        """
        import random
        prices = {}
        current_price = base_price
        
        for date in sorted(dates):
            # Variación aleatoria base (volatilidad diaria ~1%)
            daily_vol = 0.01
            change = random.gauss(0, daily_vol)
            current_price = current_price * (1 + change)
            
            # Mantener precio positivo
            current_price = max(0.01, current_price)
            prices[date] = round(current_price, 2)
        
        return prices
    
    def get_relevant_news_for_backtest(
        self,
        db: Session,
        rule: BacktestRule,
        date: datetime,
        portfolio_items: List[PortfolioItemResponse]
    ) -> List[Tuple[NewsItemResponse, float]]:
        """
        Obtiene noticias relevantes para una fecha específica en el contexto del backtest.
        
        Returns:
            Lista de tuplas (noticia, score)
        """
        # Calcular ventana de tiempo para noticias
        news_cutoff = date - timedelta(hours=rule.news_max_age_hours)
        
        # Obtener noticias en la ventana
        news_items = db.query(NewsItem).filter(
            NewsItem.created_at >= news_cutoff,
            NewsItem.created_at <= date
        ).order_by(NewsItem.created_at.desc()).all()
        
        if not news_items:
            return []
        
        # Calcular scores
        news_responses = [NewsItemResponse.model_validate(item) for item in news_items]
        scored_news = self.scoring_service.score_and_sort_news(news_responses, portfolio_items)
        
        # Filtrar por score mínimo y sentimiento
        relevant_news = []
        for news_item, score_dict in scored_news:
            if score_dict["score"] < rule.news_min_score:
                continue
            
            # Verificar sentimiento si es requerido
            sentiment = score_dict["components"]["sentiment_type"]
            if rule.news_sentiment_required != "any":
                if rule.news_sentiment_required == "positive" and sentiment != "positive":
                    continue
                if rule.news_sentiment_required == "negative" and sentiment != "negative":
                    continue
            
            relevant_news.append((news_item, score_dict["score"]))
        
        return relevant_news
    
    def check_price_condition(
        self,
        current_price: float,
        previous_price: float,
        rule: BacktestRule
    ) -> bool:
        """Verifica si se cumple la condición de precio."""
        if not rule.price_change_condition or rule.price_change_condition == "none":
            return True
        
        if previous_price is None or previous_price == 0:
            return False
        
        price_change_pct = ((current_price - previous_price) / previous_price) * 100
        
        if rule.price_change_condition == "drop_before":
            return price_change_pct <= -abs(rule.price_change_threshold or 0)
        elif rule.price_change_condition == "rise_before":
            return price_change_pct >= abs(rule.price_change_threshold or 0)
        
        return False
    
    def execute_backtest(
        self,
        db: Session,
        rule: BacktestRule,
        initial_capital: float = 10000.0
    ) -> Dict:
        """
        Ejecuta un backtest completo de la regla.
        
        Returns:
            Diccionario con métricas y equity curve
        """
        # Obtener rango de fechas
        if rule.start_date:
            start_date = rule.start_date if isinstance(rule.start_date, datetime) else datetime.fromisoformat(str(rule.start_date))
        else:
            # Usar fecha de la noticia más antigua
            oldest_news = db.query(NewsItem).order_by(NewsItem.created_at.asc()).first()
            if not oldest_news:
                raise ValueError("No hay noticias disponibles para backtesting")
            start_date = oldest_news.created_at
        
        if rule.end_date:
            end_date = rule.end_date if isinstance(rule.end_date, datetime) else datetime.fromisoformat(str(rule.end_date))
        else:
            end_date = datetime.now(timezone.utc)
        
        # Obtener portfolio para scoring
        portfolio_items_db = db.query(PortfolioItem).all()
        portfolio_items = [PortfolioItemResponse.model_validate(item) for item in portfolio_items_db]
        
        # Obtener símbolos de la cartera
        symbols = [item.symbol for item in portfolio_items if item.symbol]
        if not symbols:
            symbols = ["SPY"]  # Default si no hay símbolos
        
        # Generar lista de fechas para simulación
        dates = []
        current_date = start_date
        while current_date <= end_date:
            dates.append(current_date)
            current_date += timedelta(days=1)
        
        # Simular datos de precio (en producción, obtener de API real)
        price_data: Dict[str, Dict[datetime, float]] = {}
        base_prices = {symbol: 100.0 for symbol in symbols}  # Precios base simulados
        
        for symbol in symbols:
            price_data[symbol] = self.simulate_price_data(symbol, base_prices[symbol], dates)
        
        # Ejecutar simulación
        trades: List[Trade] = []
        open_trades: List[Trade] = []
        
        for date in dates:
            # Cerrar trades que han alcanzado su período de hold
            trades_to_close = []
            for trade in open_trades:
                days_held = (date - trade.entry_date).days
                if days_held >= rule.hold_period_days:
                    if date in price_data.get(trade.symbol, {}):
                        exit_price = price_data[trade.symbol][date]
                        trade.close(date, exit_price, BACKTEST_COMMISSION_RATE)
                        trades_to_close.append(trade)
            
            for trade in trades_to_close:
                open_trades.remove(trade)
                trades.append(trade)
            
            # Buscar nuevas señales
            for symbol in symbols:
                if date not in price_data.get(symbol, {}):
                    continue
                
                current_price = price_data[symbol][date]
                
                # Verificar condición de precio (precio anterior)
                price_condition_met = True
                if rule.price_change_condition and rule.price_change_condition != "none":
                    prev_date = date - timedelta(days=1)
                    if prev_date in price_data.get(symbol, {}):
                        previous_price = price_data[symbol][prev_date]
                        price_condition_met = self.check_price_condition(current_price, previous_price, rule)
                    else:
                        price_condition_met = False
                
                if not price_condition_met:
                    continue
                
                # Verificar condición de noticias
                relevant_news = self.get_relevant_news_for_backtest(db, rule, date, portfolio_items)
                
                if not relevant_news:
                    continue
                
                # Crear trade si no hay posiciones abiertas para este símbolo
                has_open_trade = any(t.symbol == symbol and t.is_open for t in open_trades)
                if not has_open_trade:
                    # Usar la noticia con mayor score
                    best_news, best_score = max(relevant_news, key=lambda x: x[1])
                    trade = Trade(date, current_price, symbol, best_news.id)
                    open_trades.append(trade)
        
        # Cerrar todas las posiciones abiertas al final
        for trade in open_trades:
            last_date = max(price_data.get(trade.symbol, {}).keys(), default=date)
            if last_date in price_data.get(trade.symbol, {}):
                exit_price = price_data[trade.symbol][last_date]
                trade.close(last_date, exit_price, BACKTEST_COMMISSION_RATE)
                trades.append(trade)
        
        # Calcular métricas
        winning_trades = [t for t in trades if t.pnl and t.pnl > 0]
        losing_trades = [t for t in trades if t.pnl and t.pnl <= 0]
        
        total_trades = len(trades)
        win_count = len(winning_trades)
        loss_count = len(losing_trades)
        win_rate = (win_count / total_trades * 100) if total_trades > 0 else 0.0
        
        # Calcular PnL total usando porcentajes
        total_pnl_pct = sum(t.pnl_pct for t in trades if t.pnl_pct is not None)
        position_value = initial_capital * (rule.position_size_pct / 100.0)
        total_pnl = position_value * (total_pnl_pct / 100.0) if total_pnl_pct else 0.0
        
        avg_win = sum(t.pnl for t in winning_trades) / len(winning_trades) if winning_trades else 0.0
        avg_loss = sum(t.pnl for t in losing_trades) / len(losing_trades) if losing_trades else 0.0
        
        # Calcular equity curve basado en trades cerrados
        equity_curve = [{"date": start_date.isoformat(), "equity": initial_capital, "drawdown": 0.0}]
        current_equity = initial_capital
        peak_equity = initial_capital
        
        for trade in sorted(trades, key=lambda t: t.exit_date if t.exit_date else date):
            if trade.exit_date and trade.pnl is not None and trade.pnl_pct is not None:
                # Calcular PnL basado en porcentaje del capital
                position_value = initial_capital * (rule.position_size_pct / 100.0)
                pnl_amount = position_value * (trade.pnl_pct / 100.0)
                current_equity += pnl_amount
                peak_equity = max(peak_equity, current_equity)
                
                drawdown = peak_equity - current_equity
                drawdown_pct = (drawdown / peak_equity * 100) if peak_equity > 0 else 0.0
                
                equity_curve.append({
                    "date": trade.exit_date.isoformat(),
                    "equity": round(current_equity, 2),
                    "drawdown": round(drawdown_pct, 2)
                })
        
        # Calcular max drawdown desde la curva de equity
        max_dd = 0.0
        max_dd_pct = 0.0
        peak = initial_capital
        for point in equity_curve:
            if point["equity"] > peak:
                peak = point["equity"]
            dd = peak - point["equity"]
            dd_pct = point.get("drawdown", (dd / peak * 100) if peak > 0 else 0.0)
            if dd_pct > max_dd_pct:
                max_dd_pct = dd_pct
                max_dd = dd
        
        return {
            "total_trades": total_trades,
            "winning_trades": win_count,
            "losing_trades": loss_count,
            "win_rate": round(win_rate, 2),
            "total_pnl": round(total_pnl, 2),
            "total_pnl_pct": round(total_pnl_pct, 2),
            "average_win": round(avg_win, 2),
            "average_loss": round(avg_loss, 2),
            "max_drawdown": round(max_dd, 2),
            "max_drawdown_pct": round(max_dd_pct, 2),
            "equity_curve": equity_curve,
            "executed_start_date": start_date.isoformat(),
            "executed_end_date": end_date.isoformat()
        }

