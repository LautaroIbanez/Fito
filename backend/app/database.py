"""Configuración de base de datos SQLite."""
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, Float, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import json
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
    # Standardized data stored as JSON string (SQLite doesn't have native JSON)
    standardized_data = Column(Text, nullable=True)

    def to_dict(self):
        """Convierte el modelo a diccionario."""
        standardized = None
        if self.standardized_data:
            try:
                standardized = json.loads(self.standardized_data)
            except (json.JSONDecodeError, TypeError):
                standardized = None
        
        return {
            "id": self.id,
            "title": self.title,
            "body": self.body,
            "source": self.source,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "standardized_data": standardized,
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


class AlertTrigger(Base):
    """Modelo de datos para triggers de alertas."""
    __tablename__ = "alert_triggers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)  # Nombre del trigger
    symbol = Column(String(50), nullable=True)  # Símbolo/ticker específico (opcional)
    asset_type = Column(String(50), nullable=True)  # Tipo de activo (opcional)
    
    # Condiciones de precio
    price_trigger_type = Column(String(50), nullable=False)  # "intraday_change", "gap", "absolute"
    price_threshold = Column(Float, nullable=True)  # Umbral de precio (±X%)
    gap_threshold = Column(Float, nullable=True)  # Umbral de gap (%)
    
    # Condiciones de noticias
    require_recent_news = Column(Boolean, default=True, nullable=False)
    news_relevance_threshold = Column(Float, default=2.0, nullable=False)  # Score mínimo de noticias
    news_max_age_hours = Column(Integer, default=24, nullable=False)  # Noticias más recientes que X horas
    
    # Configuración
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relación con alertas entregadas
    alerts = relationship("AlertHistory", back_populates="trigger", cascade="all, delete-orphan")

    def to_dict(self):
        """Convierte el modelo a diccionario."""
        return {
            "id": self.id,
            "name": self.name,
            "symbol": self.symbol,
            "asset_type": self.asset_type,
            "price_trigger_type": self.price_trigger_type,
            "price_threshold": self.price_threshold,
            "gap_threshold": self.gap_threshold,
            "require_recent_news": self.require_recent_news,
            "news_relevance_threshold": self.news_relevance_threshold,
            "news_max_age_hours": self.news_max_age_hours,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class AlertHistory(Base):
    """Modelo de datos para historial de alertas entregadas."""
    __tablename__ = "alert_history"

    id = Column(Integer, primary_key=True, index=True)
    trigger_id = Column(Integer, ForeignKey("alert_triggers.id"), nullable=False)
    
    # Información del activo
    symbol = Column(String(50), nullable=True)
    asset_name = Column(String(200), nullable=True)
    
    # Detalles del trigger que se cumplió
    price_condition_met = Column(Boolean, nullable=False)
    news_condition_met = Column(Boolean, nullable=False)
    price_value = Column(Float, nullable=True)  # Precio actual cuando se disparó
    price_change_percent = Column(Float, nullable=True)  # Cambio porcentual
    gap_percent = Column(Float, nullable=True)  # Gap porcentual
    
    # Información de noticias relevantes
    relevant_news_count = Column(Integer, default=0, nullable=False)
    highest_news_score = Column(Float, nullable=True)
    
    # Alerta generada
    alert_summary = Column(Text, nullable=False)  # Resumen de la alerta
    expected_impact = Column(Text, nullable=True)  # Impacto esperado
    suggested_action = Column(Text, nullable=True)  # Acción sugerida
    
    # Metadatos
    triggered_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relación con trigger
    trigger = relationship("AlertTrigger", back_populates="alerts")

    def to_dict(self):
        """Convierte el modelo a diccionario."""
        return {
            "id": self.id,
            "trigger_id": self.trigger_id,
            "symbol": self.symbol,
            "asset_name": self.asset_name,
            "price_condition_met": self.price_condition_met,
            "news_condition_met": self.news_condition_met,
            "price_value": self.price_value,
            "price_change_percent": self.price_change_percent,
            "gap_percent": self.gap_percent,
            "relevant_news_count": self.relevant_news_count,
            "highest_news_score": self.highest_news_score,
            "alert_summary": self.alert_summary,
            "expected_impact": self.expected_impact,
            "suggested_action": self.suggested_action,
            "triggered_at": self.triggered_at.isoformat() if self.triggered_at else None,
        }


class BacktestRule(Base):
    """Modelo de datos para reglas de backtesting."""
    __tablename__ = "backtest_rules"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    
    # Condiciones de noticia
    news_sentiment_required = Column(String(20), nullable=False)  # "positive", "negative", "any"
    news_min_score = Column(Float, default=2.0, nullable=False)
    news_max_age_hours = Column(Integer, default=24, nullable=False)
    
    # Condiciones de precio
    price_change_condition = Column(String(50), nullable=True)  # "drop_before", "rise_before", "none"
    price_change_threshold = Column(Float, nullable=True)  # Porcentaje de cambio requerido
    
    # Configuración de trade
    hold_period_days = Column(Integer, default=1, nullable=False)  # Días a mantener la posición
    position_size_pct = Column(Float, default=100.0, nullable=False)  # % del capital a usar
    
    # Período de backtest
    start_date = Column(DateTime, nullable=True)
    end_date = Column(DateTime, nullable=True)
    
    # Metadatos
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relación con resultados
    results = relationship("BacktestResult", back_populates="rule", cascade="all, delete-orphan")

    def to_dict(self):
        """Convierte el modelo a diccionario."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "news_sentiment_required": self.news_sentiment_required,
            "news_min_score": self.news_min_score,
            "news_max_age_hours": self.news_max_age_hours,
            "price_change_condition": self.price_change_condition,
            "price_change_threshold": self.price_change_threshold,
            "hold_period_days": self.hold_period_days,
            "position_size_pct": self.position_size_pct,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class BacktestResult(Base):
    """Modelo de datos para resultados de backtesting."""
    __tablename__ = "backtest_results"

    id = Column(Integer, primary_key=True, index=True)
    rule_id = Column(Integer, ForeignKey("backtest_rules.id"), nullable=False)
    
    # Métricas generales
    total_trades = Column(Integer, default=0, nullable=False)
    winning_trades = Column(Integer, default=0, nullable=False)
    losing_trades = Column(Integer, default=0, nullable=False)
    win_rate = Column(Float, default=0.0, nullable=False)  # Porcentaje
    
    # PnL
    total_pnl = Column(Float, default=0.0, nullable=False)
    total_pnl_pct = Column(Float, default=0.0, nullable=False)  # Porcentaje del capital inicial
    average_win = Column(Float, default=0.0, nullable=False)
    average_loss = Column(Float, default=0.0, nullable=False)
    
    # Drawdown
    max_drawdown = Column(Float, default=0.0, nullable=False)
    max_drawdown_pct = Column(Float, default=0.0, nullable=False)
    
    # Equity curve (JSON serializado)
    equity_curve_data = Column(Text, nullable=True)  # JSON array de {date, equity}
    
    # Período ejecutado
    executed_start_date = Column(DateTime, nullable=True)
    executed_end_date = Column(DateTime, nullable=True)
    
    # Metadatos
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relación con regla
    rule = relationship("BacktestRule", back_populates="results")

    def to_dict(self):
        """Convierte el modelo a diccionario."""
        return {
            "id": self.id,
            "rule_id": self.rule_id,
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
            "win_rate": self.win_rate,
            "total_pnl": self.total_pnl,
            "total_pnl_pct": self.total_pnl_pct,
            "average_win": self.average_win,
            "average_loss": self.average_loss,
            "max_drawdown": self.max_drawdown,
            "max_drawdown_pct": self.max_drawdown_pct,
            "equity_curve_data": self.equity_curve_data,
            "executed_start_date": self.executed_start_date.isoformat() if self.executed_start_date else None,
            "executed_end_date": self.executed_end_date.isoformat() if self.executed_end_date else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class AssetSuggestion(Base):
    """Modelo de datos para sugerencias de activos."""
    __tablename__ = "asset_suggestions"

    id = Column(Integer, primary_key=True, index=True)
    
    # Información del activo sugerido
    asset_type = Column(String(50), nullable=False)
    name = Column(String(200), nullable=False)
    symbol = Column(String(50), nullable=True)
    
    # Motivo de la sugerencia
    reason = Column(String(50), nullable=False)  # "diversification", "hedge", "momentum"
    reason_description = Column(Text, nullable=True)
    
    # Análisis
    correlation_with_portfolio = Column(Float, nullable=True)  # Correlación con cartera actual (-1 a 1)
    news_relevance_score = Column(Float, nullable=False)  # Score de relevancia en noticias
    news_count = Column(Integer, default=0, nullable=False)  # Cantidad de noticias relevantes
    
    # Recomendación
    suggested_position_size_pct = Column(Float, nullable=False)  # % máximo recomendado
    max_position_value = Column(Float, nullable=True)  # Valor máximo en USD
    confidence_level = Column(Float, nullable=False)  # Nivel de confianza (0-1)
    
    # Datos de soporte
    supporting_news_ids = Column(Text, nullable=True)  # JSON array de IDs de noticias
    correlation_data_available = Column(Boolean, default=False, nullable=False)
    
    # Metadatos
    generated_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=True)  # Cuándo expira la sugerencia

    def to_dict(self):
        """Convierte el modelo a diccionario."""
        return {
            "id": self.id,
            "asset_type": self.asset_type,
            "name": self.name,
            "symbol": self.symbol,
            "reason": self.reason,
            "reason_description": self.reason_description,
            "correlation_with_portfolio": self.correlation_with_portfolio,
            "news_relevance_score": self.news_relevance_score,
            "news_count": self.news_count,
            "suggested_position_size_pct": self.suggested_position_size_pct,
            "max_position_value": self.max_position_value,
            "confidence_level": self.confidence_level,
            "supporting_news_ids": self.supporting_news_ids,
            "correlation_data_available": self.correlation_data_available,
            "generated_at": self.generated_at.isoformat() if self.generated_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        }


class AssetThesis(Base):
    """Modelo de datos para tesis de inversión por activo."""
    __tablename__ = "asset_theses"

    id = Column(Integer, primary_key=True, index=True)
    portfolio_item_id = Column(Integer, ForeignKey("portfolio_items.id"), nullable=False)
    
    # Contenido de la tesis
    thesis_text = Column(Text, nullable=False)  # Por qué se posee este activo
    entry_reason = Column(String(200), nullable=True)  # Razón de entrada
    target_price = Column(String(50), nullable=True)  # Precio objetivo
    stop_loss = Column(String(50), nullable=True)  # Stop loss
    time_horizon = Column(String(100), nullable=True)  # Horizonte temporal
    
    # Metadatos
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relaciones
    portfolio_item = relationship("PortfolioItem", backref="theses")
    linked_news = relationship("ThesisNewsLink", back_populates="thesis", cascade="all, delete-orphan")
    checklist_items = relationship("ChecklistItem", back_populates="thesis", cascade="all, delete-orphan", order_by="ChecklistItem.order_index")

    def to_dict(self):
        """Convierte el modelo a diccionario."""
        return {
            "id": self.id,
            "portfolio_item_id": self.portfolio_item_id,
            "thesis_text": self.thesis_text,
            "entry_reason": self.entry_reason,
            "target_price": self.target_price,
            "stop_loss": self.stop_loss,
            "time_horizon": self.time_horizon,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class ThesisNewsLink(Base):
    """Modelo de datos para vincular noticias a tesis."""
    __tablename__ = "thesis_news_links"

    id = Column(Integer, primary_key=True, index=True)
    thesis_id = Column(Integer, ForeignKey("asset_theses.id"), nullable=False)
    news_item_id = Column(Integer, ForeignKey("news_items.id"), nullable=False)
    
    # Metadatos del vínculo
    relevance_note = Column(Text, nullable=True)  # Nota sobre por qué esta noticia es relevante
    is_key_news = Column(Boolean, default=True, nullable=False)  # Noticia clave para la tesis
    linked_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relaciones
    thesis = relationship("AssetThesis", back_populates="linked_news")
    news_item = relationship("NewsItem", backref="thesis_links")

    def to_dict(self):
        """Convierte el modelo a diccionario."""
        return {
            "id": self.id,
            "thesis_id": self.thesis_id,
            "news_item_id": self.news_item_id,
            "relevance_note": self.relevance_note,
            "is_key_news": self.is_key_news,
            "linked_at": self.linked_at.isoformat() if self.linked_at else None,
        }


class ChecklistItem(Base):
    """Modelo de datos para items del checklist post-noticia."""
    __tablename__ = "checklist_items"

    id = Column(Integer, primary_key=True, index=True)
    thesis_id = Column(Integer, ForeignKey("asset_theses.id"), nullable=False)
    
    # Contenido del item
    title = Column(String(200), nullable=False)  # Título del paso
    description = Column(Text, nullable=True)  # Descripción detallada
    order_index = Column(Integer, nullable=False, default=0)  # Orden de visualización
    
    # Estado
    is_completed = Column(Boolean, default=False, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    completed_notes = Column(Text, nullable=True)  # Notas al completar
    
    # Metadatos
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relación
    thesis = relationship("AssetThesis", back_populates="checklist_items")

    def to_dict(self):
        """Convierte el modelo a diccionario."""
        return {
            "id": self.id,
            "thesis_id": self.thesis_id,
            "title": self.title,
            "description": self.description,
            "order_index": self.order_index,
            "is_completed": self.is_completed,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "completed_notes": self.completed_notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class DynamicLimit(Base):
    """Modelo de datos para límites dinámicos por activo."""
    __tablename__ = "dynamic_limits"

    id = Column(Integer, primary_key=True, index=True)
    portfolio_item_id = Column(Integer, ForeignKey("portfolio_items.id"), nullable=False)
    
    # Datos para cálculo
    current_position_pct = Column(Float, nullable=False)  # % actual en cartera
    recent_drawdown_pct = Column(Float, nullable=True)  # Drawdown reciente (%)
    realized_volatility = Column(Float, nullable=True)  # Volatilidad realizada anual
    implied_volatility = Column(Float, nullable=True)  # Volatilidad implícita (si disponible)
    
    # Límites calculados
    max_position_pct = Column(Float, nullable=False)  # % máximo permitido
    suggested_stop_loss_pct = Column(Float, nullable=True)  # Stop loss sugerido (% desde precio actual)
    risk_adjusted_size_pct = Column(Float, nullable=False)  # Tamaño ajustado por riesgo
    
    # Estado
    is_exceeded = Column(Boolean, default=False, nullable=False)  # Si excede límite
    excess_amount_pct = Column(Float, default=0.0, nullable=False)  # Exceso sobre límite
    suggested_reduction_pct = Column(Float, default=0.0, nullable=False)  # % sugerido de reducción
    
    # Metadatos
    calculated_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    next_calculation_at = Column(DateTime, nullable=True)  # Próximo cálculo
    
    # Relación
    portfolio_item = relationship("PortfolioItem", backref="dynamic_limits")

    def to_dict(self):
        """Convierte el modelo a diccionario."""
        return {
            "id": self.id,
            "portfolio_item_id": self.portfolio_item_id,
            "current_position_pct": self.current_position_pct,
            "recent_drawdown_pct": self.recent_drawdown_pct,
            "realized_volatility": self.realized_volatility,
            "implied_volatility": self.implied_volatility,
            "max_position_pct": self.max_position_pct,
            "suggested_stop_loss_pct": self.suggested_stop_loss_pct,
            "risk_adjusted_size_pct": self.risk_adjusted_size_pct,
            "is_exceeded": self.is_exceeded,
            "excess_amount_pct": self.excess_amount_pct,
            "suggested_reduction_pct": self.suggested_reduction_pct,
            "calculated_at": self.calculated_at.isoformat() if self.calculated_at else None,
            "next_calculation_at": self.next_calculation_at.isoformat() if self.next_calculation_at else None,
        }


class DecisionLog(Base):
    """Modelo de datos para registro de decisiones de trading."""
    __tablename__ = "decision_logs"

    id = Column(Integer, primary_key=True, index=True)
    portfolio_item_id = Column(Integer, ForeignKey("portfolio_items.id"), nullable=False)
    
    # Tipo de decisión
    decision_type = Column(String(10), nullable=False)  # 'buy', 'sell', 'hold'
    
    # Motivo y contexto
    reason = Column(Text, nullable=False)  # Motivo de la decisión
    signal_type = Column(String(20), nullable=False)  # 'news', 'price', 'both', 'analysis', 'other'
    signal_reference = Column(String(200), nullable=True)  # ID de noticia, descripción de señal de precio, etc.
    
    # Expectativa
    expected_direction = Column(String(10), nullable=True)  # 'up', 'down', 'neutral'
    expected_price = Column(String(50), nullable=True)  # Precio objetivo esperado
    expected_timeframe_days = Column(Integer, nullable=True)  # Horizonte temporal en días
    expected_outcome = Column(Text, nullable=True)  # Descripción más detallada de la expectativa
    
    # Estado y evaluación
    status = Column(String(20), default='pending', nullable=False)  # 'pending', 'evaluated', 'cancelled'
    evaluation_window_days = Column(Integer, nullable=False)  # Ventana para evaluar resultado
    
    # Metadatos
    decided_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    evaluated_at = Column(DateTime, nullable=True)
    
    # Relaciones
    portfolio_item = relationship("PortfolioItem", backref="decision_logs")
    evaluation = relationship("DecisionEvaluation", back_populates="decision", uselist=False, cascade="all, delete-orphan")
    
    def to_dict(self):
        """Convierte el modelo a diccionario."""
        eval_dict = None
        if self.evaluation:
            eval_dict = self.evaluation.to_dict()
        
        return {
            "id": self.id,
            "portfolio_item_id": self.portfolio_item_id,
            "decision_type": self.decision_type,
            "reason": self.reason,
            "signal_type": self.signal_type,
            "signal_reference": self.signal_reference,
            "expected_direction": self.expected_direction,
            "expected_price": self.expected_price,
            "expected_timeframe_days": self.expected_timeframe_days,
            "expected_outcome": self.expected_outcome,
            "status": self.status,
            "evaluation_window_days": self.evaluation_window_days,
            "decided_at": self.decided_at.isoformat() if self.decided_at else None,
            "evaluated_at": self.evaluated_at.isoformat() if self.evaluated_at else None,
            "evaluation": eval_dict,
        }


class DecisionEvaluation(Base):
    """Modelo de datos para evaluación de resultados de decisiones."""
    __tablename__ = "decision_evaluations"

    id = Column(Integer, primary_key=True, index=True)
    decision_id = Column(Integer, ForeignKey("decision_logs.id"), nullable=False, unique=True)
    
    # Precios
    price_at_decision = Column(Float, nullable=True)  # Precio al momento de la decisión
    price_at_evaluation = Column(Float, nullable=True)  # Precio después del periodo
    
    # Resultado
    result = Column(String(10), nullable=False)  # 'hit', 'miss', 'partial'
    price_change_pct = Column(Float, nullable=True)  # Cambio de precio en %
    outcome_match = Column(Boolean, nullable=True)  # Si la expectativa se cumplió
    
    # Análisis
    evaluation_notes = Column(Text, nullable=True)  # Notas sobre el resultado
    lessons_learned = Column(Text, nullable=True)  # Lecciones aprendidas
    
    # Metadatos
    evaluated_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relación
    decision = relationship("DecisionLog", back_populates="evaluation")
    
    def to_dict(self):
        """Convierte el modelo a diccionario."""
        return {
            "id": self.id,
            "decision_id": self.decision_id,
            "price_at_decision": self.price_at_decision,
            "price_at_evaluation": self.price_at_evaluation,
            "result": self.result,
            "price_change_pct": self.price_change_pct,
            "outcome_match": self.outcome_match,
            "evaluation_notes": self.evaluation_notes,
            "lessons_learned": self.lessons_learned,
            "evaluated_at": self.evaluated_at.isoformat() if self.evaluated_at else None,
        }


class Sector(Base):
    """Modelo de datos para sectores/temas."""
    __tablename__ = "sectors"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)  # Ej: "Tecnología", "Energía", "Salud"
    category = Column(String(50), nullable=False)  # "sector", "theme", "industry"
    keywords = Column(Text, nullable=True)  # JSON array de palabras clave
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def to_dict(self):
        """Convierte el modelo a diccionario."""
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "keywords": self.keywords,
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class AssetCatalog(Base):
    """Catálogo de activos (tickers/ETF) mapeados a sectores."""
    __tablename__ = "asset_catalog"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(50), nullable=False, unique=True)  # Ticker/ETF symbol
    name = Column(String(200), nullable=False)
    asset_type = Column(String(50), nullable=False)  # "stock", "etf", "index"
    sector_id = Column(Integer, ForeignKey("sectors.id"), nullable=False)
    is_etf = Column(Boolean, default=False, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relación
    sector = relationship("Sector", backref="assets")

    def to_dict(self):
        """Convierte el modelo a diccionario."""
        return {
            "id": self.id,
            "symbol": self.symbol,
            "name": self.name,
            "asset_type": self.asset_type,
            "sector_id": self.sector_id,
            "is_etf": self.is_etf,
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class WatchlistItem(Base):
    """Items en la watchlist del usuario."""
    __tablename__ = "watchlist_items"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(50), nullable=False)
    name = Column(String(200), nullable=False)
    asset_type = Column(String(50), nullable=False)
    sector_id = Column(Integer, ForeignKey("sectors.id"), nullable=True)
    added_from_news_id = Column(Integer, ForeignKey("news_items.id"), nullable=True)  # Noticia que generó la sugerencia
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relaciones
    sector = relationship("Sector", backref="watchlist_items")
    news_item = relationship("NewsItem", backref="watchlist_suggestions")

    def to_dict(self):
        """Convierte el modelo a diccionario."""
        return {
            "id": self.id,
            "symbol": self.symbol,
            "name": self.name,
            "asset_type": self.asset_type,
            "sector_id": self.sector_id,
            "added_from_news_id": self.added_from_news_id,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class TradingRecommendation(Base):
    """Modelo de datos para recomendaciones de trading con trazabilidad completa."""
    __tablename__ = "trading_recommendations"

    id = Column(Integer, primary_key=True, index=True)
    portfolio_item_id = Column(Integer, ForeignKey("portfolio_items.id"), nullable=False)
    
    # Origen y trazabilidad
    source_news_id = Column(Integer, ForeignKey("news_items.id"), nullable=True)  # Noticia que originó la recomendación
    source_news_title = Column(String(200), nullable=True)  # Título de la noticia (snapshot)
    generated_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Recomendación
    action = Column(String(20), nullable=False)  # add, reduce, trim, exit, stop, watch
    condition = Column(String(200), nullable=False)  # Condición que activa la recomendación
    reason = Column(Text, nullable=False)  # Razón de la recomendación
    explanation = Column(Text, nullable=True)  # Explicación detallada de por qué el umbral es relevante
    
    # Variables consideradas (JSON)
    inputs = Column(Text, nullable=True)  # JSON con sentimiento, precio, volumen, sector, etc.
    
    # Umbrales y métricas
    threshold_data = Column(Text, nullable=True)  # JSON con umbrales cuantitativos
    confidence = Column(Float, nullable=False)  # Confianza (0.0-1.0)
    priority = Column(Integer, default=1, nullable=False)  # Prioridad de la recomendación
    
    # Estado
    is_active = Column(Boolean, default=True, nullable=False)  # Si la recomendación sigue activa
    acknowledged_at = Column(DateTime, nullable=True)  # Cuándo el usuario la revisó
    executed_at = Column(DateTime, nullable=True)  # Cuándo se ejecutó (si aplica)
    
    # Metadatos
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relaciones
    portfolio_item = relationship("PortfolioItem", backref="trading_recommendations")
    source_news = relationship("NewsItem", backref="generated_recommendations")

    def to_dict(self):
        """Convierte el modelo a diccionario."""
        inputs_dict = None
        threshold_dict = None
        
        if self.inputs:
            try:
                inputs_dict = json.loads(self.inputs)
            except (json.JSONDecodeError, TypeError):
                inputs_dict = None
        
        if self.threshold_data:
            try:
                threshold_dict = json.loads(self.threshold_data)
            except (json.JSONDecodeError, TypeError):
                threshold_dict = None
        
        return {
            "id": self.id,
            "portfolio_item_id": self.portfolio_item_id,
            "source_news_id": self.source_news_id,
            "source_news_title": self.source_news_title,
            "generated_at": self.generated_at.isoformat() if self.generated_at else None,
            "action": self.action,
            "condition": self.condition,
            "reason": self.reason,
            "explanation": self.explanation,
            "inputs": inputs_dict,
            "threshold_data": threshold_dict,
            "confidence": self.confidence,
            "priority": self.priority,
            "is_active": self.is_active,
            "acknowledged_at": self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            "executed_at": self.executed_at.isoformat() if self.executed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
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

