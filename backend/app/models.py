"""Modelos Pydantic para validación de requests/responses."""
from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Optional, Dict, List
from datetime import datetime
import re

# Importar configuraciones
try:
    from app.config import (
        THESIS_MIN_LENGTH, THESIS_MAX_LENGTH,
        DECISION_MIN_REASON_LENGTH, DECISION_DEFAULT_EVALUATION_WINDOW_DAYS,
        STANDARDIZED_NEWS_MAX_BULLET_LENGTH, STANDARDIZED_NEWS_MIN_BULLETS,
        STANDARDIZED_NEWS_MAX_BULLETS, STANDARDIZED_NEWS_SENTIMENT_ENUM,
        PORTFOLIO_ANALYSIS_CONFIDENCE_LEVELS, PORTFOLIO_ANALYSIS_ACTIONS,
        PORTFOLIO_ANALYSIS_MAX_FOLLOWUP_QUESTIONS
    )
except ImportError:
    # Valores por defecto si no se importan correctamente
    THESIS_MIN_LENGTH = 50
    THESIS_MAX_LENGTH = 5000
    DECISION_MIN_REASON_LENGTH = 20
    DECISION_DEFAULT_EVALUATION_WINDOW_DAYS = 30
    STANDARDIZED_NEWS_MAX_BULLET_LENGTH = 50
    STANDARDIZED_NEWS_MIN_BULLETS = 3
    STANDARDIZED_NEWS_MAX_BULLETS = 5
    STANDARDIZED_NEWS_SENTIMENT_ENUM = ["bullish", "bearish", "neutral"]
    PORTFOLIO_ANALYSIS_CONFIDENCE_LEVELS = ["high", "med", "low"]
    PORTFOLIO_ANALYSIS_ACTIONS = ["watch", "add", "trim", "exit"]
    PORTFOLIO_ANALYSIS_MAX_FOLLOWUP_QUESTIONS = 2


class NewsItemCreate(BaseModel):
    """Modelo para crear una noticia."""
    title: Optional[str] = Field(None, max_length=200, description="Título opcional de la noticia")
    body: str = Field(..., min_length=200, max_length=10000, description="Cuerpo de la noticia (200-10000 caracteres)")
    source: Optional[str] = Field(None, max_length=100, description="Fuente opcional de la noticia")

    @field_validator('body')
    @classmethod
    def validate_body(cls, v):
        """Valida y sanitiza el cuerpo."""
        if not v or not v.strip():
            raise ValueError("El cuerpo de la noticia no puede estar vacío")
        
        # Sanitizar solo caracteres de control peligrosos (excepto saltos de línea y tabs)
        # Los emojis y caracteres Unicode están permitidos
        v = re.sub(r'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]', '', v)
        
        # Preservar emojis y caracteres UTF-8 completos
        # El frontend se encargará del renderizado seguro
        
        # Validar longitud después de sanitización
        if len(v.strip()) < 200:
            raise ValueError(f"El cuerpo debe tener al menos 200 caracteres (actual: {len(v.strip())})")
        
        if len(v) > 10000:
            raise ValueError(f"El cuerpo no puede exceder 10000 caracteres (actual: {len(v)})")
        
        return v.strip()

    @field_validator('title')
    @classmethod
    def validate_title(cls, v):
        """Valida y sanitiza el título."""
        if v is None:
            return None
        
        v = v.strip()
        if not v:
            return None
        
        # Sanitizar caracteres de control
        v = re.sub(r'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]', '', v)
        
        # NO escapar HTML para preservar caracteres UTF-8
        
        if len(v) > 200:
            raise ValueError(f"El título no puede exceder 200 caracteres (actual: {len(v)})")
        
        return v

    @field_validator('source')
    @classmethod
    def validate_source(cls, v):
        """Valida y sanitiza la fuente."""
        if v is None:
            return None
        
        v = v.strip()
        if not v:
            return None
        
        # Sanitizar caracteres de control
        v = re.sub(r'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]', '', v)
        
        # NO escapar HTML para preservar caracteres UTF-8
        
        if len(v) > 100:
            raise ValueError(f"La fuente no puede exceder 100 caracteres (actual: {len(v)})")
        
        return v


class StandardizedNewsData(BaseModel):
    """Modelo para datos estandarizados de noticias."""
    title: str = Field(..., description="Título extraído de la noticia")
    publication_date: Optional[str] = Field(None, description="Fecha de publicación (ISO format)")
    source: Optional[str] = Field(None, description="Fuente de la noticia")
    summary_bullets: List[str] = Field(..., min_length=STANDARDIZED_NEWS_MIN_BULLETS, max_length=STANDARDIZED_NEWS_MAX_BULLETS, 
                                       description="3-5 bullets de resumen (máx 50 palabras cada uno)")
    key_people_companies: List[str] = Field(default_factory=list, description="Personas y empresas clave mencionadas")
    quoted_numbers_metrics: List[str] = Field(default_factory=list, description="Números y métricas citadas")
    sentiment: str = Field(..., description="Sentimiento: bullish, bearish, o neutral")
    why_it_matters: str = Field(..., description="Una línea explicando por qué importa desde perspectiva de inversor")

    @field_validator('sentiment')
    @classmethod
    def validate_sentiment(cls, v):
        """Valida que el sentimiento sea uno de los valores permitidos."""
        v_lower = v.lower()
        if v_lower not in [s.lower() for s in STANDARDIZED_NEWS_SENTIMENT_ENUM]:
            raise ValueError(f"Sentimiento debe ser uno de: {', '.join(STANDARDIZED_NEWS_SENTIMENT_ENUM)}")
        return v_lower

    @field_validator('summary_bullets')
    @classmethod
    def validate_bullets(cls, v):
        """Valida que cada bullet tenga máximo 50 palabras."""
        for bullet in v:
            word_count = len(bullet.split())
            if word_count > STANDARDIZED_NEWS_MAX_BULLET_LENGTH:
                raise ValueError(f"Cada bullet debe tener máximo {STANDARDIZED_NEWS_MAX_BULLET_LENGTH} palabras. "
                               f"Bullet con {word_count} palabras encontrado: {bullet[:50]}...")
        return v


class NewsItemStandardizedCreate(BaseModel):
    """Modelo para crear una noticia con estandarización."""
    article_text: str = Field(..., min_length=200, max_length=10000, description="Texto completo del artículo a estandarizar")


class NewsItemResponse(BaseModel):
    """Modelo de respuesta para una noticia."""
    id: int
    title: Optional[str]
    body: str
    source: Optional[str]
    created_at: str
    score: Optional[float] = None
    score_components: Optional[Dict] = None
    is_obsolete: Optional[bool] = None
    standardized_data: Optional[StandardizedNewsData] = None

    @field_validator('created_at', mode='before')
    @classmethod
    def convert_datetime(cls, v):
        """Convierte datetime a string ISO format."""
        if isinstance(v, datetime):
            return v.isoformat()
        return v

    model_config = ConfigDict(from_attributes=True)


class NewsListResponse(BaseModel):
    """Modelo de respuesta para lista de noticias."""
    items: list[NewsItemResponse]
    total: int


class PortfolioItemCreate(BaseModel):
    """Modelo para crear/actualizar un item de cartera."""
    asset_type: str = Field(..., description="Tipo de activo: acciones, bonos, etf, fondos, divisas")
    name: str = Field(..., max_length=200, description="Nombre del activo")
    symbol: Optional[str] = Field(None, max_length=50, description="Símbolo o ticker")
    quantity: Optional[str] = Field(None, max_length=50, description="Cantidad")
    price: Optional[str] = Field(None, max_length=50, description="Precio unitario")
    total_value: Optional[str] = Field(None, max_length=50, description="Valor total")
    currency: Optional[str] = Field("USD", max_length=10, description="Moneda")
    notes: Optional[str] = Field(None, description="Notas adicionales")

    @field_validator('asset_type')
    @classmethod
    def validate_asset_type(cls, v):
        """Valida el tipo de activo."""
        valid_types = ['acciones', 'bonos', 'etf', 'fondos', 'divisas', 'otros']
        if v.lower() not in valid_types:
            raise ValueError(f"Tipo de activo inválido. Debe ser uno de: {', '.join(valid_types)}")
        return v.lower()

    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        """Valida y sanitiza el nombre."""
        if not v or not v.strip():
            raise ValueError("El nombre del activo no puede estar vacío")
        
        v = re.sub(r'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]', '', v.strip())
        
        if len(v) > 200:
            raise ValueError(f"El nombre no puede exceder 200 caracteres")
        
        return v


class PortfolioItemResponse(BaseModel):
    """Modelo de respuesta para un item de cartera."""
    id: int
    asset_type: str
    name: str
    symbol: Optional[str]
    quantity: Optional[str]
    price: Optional[str]
    total_value: Optional[str]
    currency: Optional[str]
    notes: Optional[str]
    created_at: str
    updated_at: str

    @field_validator('created_at', 'updated_at', mode='before')
    @classmethod
    def convert_datetime(cls, v):
        """Convierte datetime a string ISO format."""
        if isinstance(v, datetime):
            return v.isoformat()
        return v

    model_config = ConfigDict(from_attributes=True)


class PortfolioListResponse(BaseModel):
    """Modelo de respuesta para lista de cartera."""
    items: list[PortfolioItemResponse]
    total: int


# ==================== Alert Models ====================

class AlertTriggerCreate(BaseModel):
    """Modelo para crear un trigger de alerta."""
    name: str = Field(..., max_length=200, description="Nombre del trigger")
    symbol: Optional[str] = Field(None, max_length=50, description="Símbolo/ticker específico")
    asset_type: Optional[str] = Field(None, max_length=50, description="Tipo de activo")
    
    price_trigger_type: str = Field(..., description="Tipo: 'intraday_change', 'gap', 'absolute'")
    price_threshold: Optional[float] = Field(None, description="Umbral de precio (±X%)")
    gap_threshold: Optional[float] = Field(None, description="Umbral de gap (%)")
    
    require_recent_news: bool = Field(True, description="Requiere noticias recientes")
    news_relevance_threshold: float = Field(2.0, ge=0.0, description="Score mínimo de noticias")
    news_max_age_hours: int = Field(24, ge=1, le=168, description="Noticias más recientes que X horas (máx 168 = 7 días)")

    @field_validator('price_trigger_type')
    @classmethod
    def validate_trigger_type(cls, v):
        valid_types = ['intraday_change', 'gap', 'absolute']
        if v.lower() not in valid_types:
            raise ValueError(f"Tipo de trigger inválido. Debe ser uno de: {', '.join(valid_types)}")
        return v.lower()
    
    @field_validator('price_threshold', 'gap_threshold')
    @classmethod
    def validate_threshold(cls, v, info):
        if v is None:
            return v
        if v <= 0:
            raise ValueError("El umbral debe ser positivo")
        if v > 1000:
            raise ValueError("El umbral no puede exceder 1000%")
        return v


class AlertTriggerUpdate(BaseModel):
    """Modelo para actualizar un trigger de alerta."""
    name: Optional[str] = Field(None, max_length=200)
    symbol: Optional[str] = Field(None, max_length=50)
    asset_type: Optional[str] = Field(None, max_length=50)
    
    price_trigger_type: Optional[str] = None
    price_threshold: Optional[float] = None
    gap_threshold: Optional[float] = None
    
    require_recent_news: Optional[bool] = None
    news_relevance_threshold: Optional[float] = Field(None, ge=0.0)
    news_max_age_hours: Optional[int] = Field(None, ge=1, le=168)
    
    is_active: Optional[bool] = None

    @field_validator('price_trigger_type')
    @classmethod
    def validate_trigger_type(cls, v):
        if v is None:
            return v
        valid_types = ['intraday_change', 'gap', 'absolute']
        if v.lower() not in valid_types:
            raise ValueError(f"Tipo de trigger inválido. Debe ser uno de: {', '.join(valid_types)}")
        return v.lower()


class AlertTriggerResponse(BaseModel):
    """Modelo de respuesta para un trigger de alerta."""
    id: int
    name: str
    symbol: Optional[str]
    asset_type: Optional[str]
    price_trigger_type: str
    price_threshold: Optional[float]
    gap_threshold: Optional[float]
    require_recent_news: bool
    news_relevance_threshold: float
    news_max_age_hours: int
    is_active: bool
    created_at: str
    updated_at: str

    @field_validator('created_at', 'updated_at', mode='before')
    @classmethod
    def convert_datetime(cls, v):
        if isinstance(v, datetime):
            return v.isoformat()
        return v

    model_config = ConfigDict(from_attributes=True)


class AlertTriggerListResponse(BaseModel):
    """Modelo de respuesta para lista de triggers."""
    items: list[AlertTriggerResponse]
    total: int


class AlertHistoryResponse(BaseModel):
    """Modelo de respuesta para una alerta entregada."""
    id: int
    trigger_id: int
    trigger_name: Optional[str] = None
    symbol: Optional[str]
    asset_name: Optional[str]
    price_condition_met: bool
    news_condition_met: bool
    price_value: Optional[float]
    price_change_percent: Optional[float]
    gap_percent: Optional[float]
    relevant_news_count: int
    highest_news_score: Optional[float]
    alert_summary: str
    expected_impact: Optional[str]
    suggested_action: Optional[str]
    triggered_at: str

    @field_validator('triggered_at', mode='before')
    @classmethod
    def convert_datetime(cls, v):
        if isinstance(v, datetime):
            return v.isoformat()
        return v

    model_config = ConfigDict(from_attributes=True)


class AlertHistoryListResponse(BaseModel):
    """Modelo de respuesta para lista de alertas entregadas."""
    items: list[AlertHistoryResponse]
    total: int


# ==================== Backtest Models ====================

class BacktestRuleCreate(BaseModel):
    """Modelo para crear una regla de backtesting."""
    name: str = Field(..., max_length=200, description="Nombre de la regla")
    description: Optional[str] = Field(None, description="Descripción opcional")
    
    news_sentiment_required: str = Field("positive", description="Sentimiento requerido: 'positive', 'negative', 'any'")
    news_min_score: float = Field(2.0, ge=0.0, description="Score mínimo de noticias")
    news_max_age_hours: int = Field(24, ge=1, le=168, description="Antigüedad máxima de noticias en horas")
    
    price_change_condition: Optional[str] = Field(None, description="Condición de precio: 'drop_before', 'rise_before', 'none'")
    price_change_threshold: Optional[float] = Field(None, ge=0.0, le=100.0, description="Umbral de cambio de precio (%)")
    
    hold_period_days: int = Field(1, ge=1, le=365, description="Días a mantener la posición")
    position_size_pct: float = Field(100.0, ge=1.0, le=100.0, description="% del capital a usar")
    
    start_date: Optional[str] = Field(None, description="Fecha de inicio (ISO format)")
    end_date: Optional[str] = Field(None, description="Fecha de fin (ISO format)")

    @field_validator('news_sentiment_required')
    @classmethod
    def validate_sentiment(cls, v):
        valid_sentiments = ['positive', 'negative', 'any']
        if v.lower() not in valid_sentiments:
            raise ValueError(f"Sentimiento inválido. Debe ser uno de: {', '.join(valid_sentiments)}")
        return v.lower()
    
    @field_validator('price_change_condition')
    @classmethod
    def validate_price_condition(cls, v):
        if v is None:
            return v
        valid_conditions = ['drop_before', 'rise_before', 'none']
        if v.lower() not in valid_conditions:
            raise ValueError(f"Condición de precio inválida. Debe ser uno de: {', '.join(valid_conditions)}")
        return v.lower()


class BacktestRuleResponse(BaseModel):
    """Modelo de respuesta para una regla de backtesting."""
    id: int
    name: str
    description: Optional[str]
    news_sentiment_required: str
    news_min_score: float
    news_max_age_hours: int
    price_change_condition: Optional[str]
    price_change_threshold: Optional[float]
    hold_period_days: int
    position_size_pct: float
    start_date: Optional[str]
    end_date: Optional[str]
    created_at: str
    updated_at: str

    @field_validator('created_at', 'updated_at', 'start_date', 'end_date', mode='before')
    @classmethod
    def convert_datetime(cls, v):
        if isinstance(v, datetime):
            return v.isoformat()
        return v

    model_config = ConfigDict(from_attributes=True)


class BacktestRuleListResponse(BaseModel):
    """Modelo de respuesta para lista de reglas."""
    items: list[BacktestRuleResponse]
    total: int


class EquityCurvePoint(BaseModel):
    """Punto en la curva de equity."""
    date: str
    equity: float
    drawdown: float


class BacktestResultResponse(BaseModel):
    """Modelo de respuesta para resultados de backtesting."""
    id: int
    rule_id: int
    rule_name: Optional[str] = None
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_pnl: float
    total_pnl_pct: float
    average_win: float
    average_loss: float
    max_drawdown: float
    max_drawdown_pct: float
    equity_curve: list[EquityCurvePoint]
    executed_start_date: Optional[str]
    executed_end_date: Optional[str]
    created_at: str

    @field_validator('created_at', 'executed_start_date', 'executed_end_date', mode='before')
    @classmethod
    def convert_datetime(cls, v):
        if isinstance(v, datetime):
            return v.isoformat()
        return v

    model_config = ConfigDict(from_attributes=True)


class BacktestExecuteRequest(BaseModel):
    """Modelo para solicitar ejecución de backtest."""
    rule_id: int
    initial_capital: float = Field(10000.0, ge=1.0, description="Capital inicial para simulación")


class BacktestResultListResponse(BaseModel):
    """Modelo de respuesta para lista de resultados."""
    items: list[BacktestResultResponse]
    total: int


# ==================== Asset Suggestions Models ====================

class AssetSuggestionResponse(BaseModel):
    """Modelo de respuesta para una sugerencia de activo."""
    id: int
    asset_type: str
    name: str
    symbol: Optional[str]
    reason: str  # "diversification", "hedge", "momentum"
    reason_description: Optional[str]
    correlation_with_portfolio: Optional[float]
    news_relevance_score: float
    news_count: int
    suggested_position_size_pct: float
    max_position_value: Optional[float]
    confidence_level: float
    supporting_news_ids: Optional[list[int]] = None
    correlation_data_available: bool
    generated_at: str
    expires_at: Optional[str]

    @field_validator('generated_at', 'expires_at', mode='before')
    @classmethod
    def convert_datetime(cls, v):
        if isinstance(v, datetime):
            return v.isoformat()
        return v

    model_config = ConfigDict(from_attributes=True)


class AssetSuggestionListResponse(BaseModel):
    """Modelo de respuesta para lista de sugerencias."""
    items: list[AssetSuggestionResponse]
    total: int
    portfolio_value: Optional[float] = None


class GenerateSuggestionsRequest(BaseModel):
    """Modelo para solicitar generación de sugerencias."""
    min_news_score: float = Field(3.0, ge=0.0, description="Score mínimo de noticias")
    max_correlation: float = Field(0.5, ge=-1.0, le=1.0, description="Correlación máxima aceptada")
    min_confidence: float = Field(0.6, ge=0.0, le=1.0, description="Confianza mínima requerida")
    max_suggestions: int = Field(10, ge=1, le=50, description="Máximo de sugerencias a generar")


# ==================== Asset Thesis Models ====================

class AssetThesisCreate(BaseModel):
    """Modelo para crear una tesis de activo."""
    portfolio_item_id: int = Field(..., description="ID del item de cartera")
    thesis_text: str = Field(..., min_length=50, max_length=5000, description="Tesis de inversión (50-5000 caracteres)")
    entry_reason: Optional[str] = Field(None, max_length=200, description="Razón de entrada")
    target_price: Optional[str] = Field(None, max_length=50, description="Precio objetivo")
    stop_loss: Optional[str] = Field(None, max_length=50, description="Stop loss")
    time_horizon: Optional[str] = Field(None, max_length=100, description="Horizonte temporal")


class AssetThesisUpdate(BaseModel):
    """Modelo para actualizar una tesis."""
    thesis_text: Optional[str] = Field(None, min_length=50, max_length=5000)
    entry_reason: Optional[str] = Field(None, max_length=200)
    target_price: Optional[str] = Field(None, max_length=50)
    stop_loss: Optional[str] = Field(None, max_length=50)
    time_horizon: Optional[str] = Field(None, max_length=100)


class NewsLinkCreate(BaseModel):
    """Modelo para vincular una noticia a una tesis."""
    news_item_id: int = Field(..., description="ID de la noticia")
    relevance_note: Optional[str] = Field(None, max_length=500, description="Nota sobre relevancia")
    is_key_news: bool = Field(True, description="Es noticia clave")


class ChecklistItemCreate(BaseModel):
    """Modelo para crear un item de checklist."""
    title: str = Field(..., max_length=200, description="Título del paso")
    description: Optional[str] = Field(None, max_length=1000, description="Descripción detallada")
    order_index: int = Field(0, ge=0, description="Orden de visualización")


class ChecklistItemUpdate(BaseModel):
    """Modelo para actualizar un item de checklist."""
    title: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    order_index: Optional[int] = Field(None, ge=0)
    is_completed: Optional[bool] = None
    completed_notes: Optional[str] = Field(None, max_length=1000)


class NewsLinkResponse(BaseModel):
    """Modelo de respuesta para vínculo noticia-tesis."""
    id: int
    thesis_id: int
    news_item_id: int
    news_title: Optional[str] = None
    news_body_preview: Optional[str] = None
    relevance_note: Optional[str]
    is_key_news: bool
    linked_at: str

    @field_validator('linked_at', mode='before')
    @classmethod
    def convert_datetime(cls, v):
        if isinstance(v, datetime):
            return v.isoformat()
        return v

    model_config = ConfigDict(from_attributes=True)


class ChecklistItemResponse(BaseModel):
    """Modelo de respuesta para item de checklist."""
    id: int
    thesis_id: int
    title: str
    description: Optional[str]
    order_index: int
    is_completed: bool
    completed_at: Optional[str]
    completed_notes: Optional[str]
    created_at: str
    updated_at: str

    @field_validator('created_at', 'updated_at', 'completed_at', mode='before')
    @classmethod
    def convert_datetime(cls, v):
        if isinstance(v, datetime):
            return v.isoformat()
        return v

    model_config = ConfigDict(from_attributes=True)


class AssetThesisResponse(BaseModel):
    """Modelo de respuesta para una tesis de activo."""
    id: int
    portfolio_item_id: int
    portfolio_item_name: Optional[str] = None
    portfolio_item_symbol: Optional[str] = None
    thesis_text: str
    entry_reason: Optional[str]
    target_price: Optional[str]
    stop_loss: Optional[str]
    time_horizon: Optional[str]
    linked_news: list[NewsLinkResponse] = []
    checklist_items: list[ChecklistItemResponse] = []
    created_at: str
    updated_at: str

    @field_validator('created_at', 'updated_at', mode='before')
    @classmethod
    def convert_datetime(cls, v):
        if isinstance(v, datetime):
            return v.isoformat()
        return v

    model_config = ConfigDict(from_attributes=True)


class AssetThesisListResponse(BaseModel):
    """Modelo de respuesta para lista de tesis."""
    items: list[AssetThesisResponse]
    total: int


# ==================== Dynamic Limits Models ====================

class DynamicLimitResponse(BaseModel):
    """Modelo de respuesta para límite dinámico."""
    id: int
    portfolio_item_id: int
    portfolio_item_name: Optional[str] = None
    portfolio_item_symbol: Optional[str] = None
    asset_type: Optional[str] = None
    current_position_pct: float
    recent_drawdown_pct: Optional[float]
    realized_volatility: Optional[float]
    implied_volatility: Optional[float]
    max_position_pct: float
    suggested_stop_loss_pct: Optional[float]
    risk_adjusted_size_pct: float
    is_exceeded: bool
    excess_amount_pct: float
    suggested_reduction_pct: float
    current_value: Optional[float] = None
    calculated_at: str
    next_calculation_at: Optional[str]

    @field_validator('calculated_at', 'next_calculation_at', mode='before')
    @classmethod
    def convert_datetime(cls, v):
        if isinstance(v, datetime):
            return v.isoformat()
        return v

    model_config = ConfigDict(from_attributes=True)


class DynamicLimitListResponse(BaseModel):
    """Modelo de respuesta para lista de límites."""
    items: list[DynamicLimitResponse]
    total: int
    exceeded_count: int


# ==================== Decision Log Models ====================

class DecisionLogCreate(BaseModel):
    """Modelo para crear un registro de decisión."""
    portfolio_item_id: int = Field(..., description="ID del activo en la cartera")
    decision_type: str = Field(..., pattern="^(buy|sell|hold)$", description="Tipo de decisión")
    reason: str = Field(..., min_length=DECISION_MIN_REASON_LENGTH, description="Motivo de la decisión")
    signal_type: str = Field(..., pattern="^(news|price|both|analysis|other)$", description="Tipo de señal")
    signal_reference: Optional[str] = Field(None, max_length=200, description="Referencia a noticia, señal de precio, etc.")
    expected_direction: Optional[str] = Field(None, pattern="^(up|down|neutral)$", description="Dirección esperada")
    expected_price: Optional[str] = Field(None, max_length=50, description="Precio objetivo")
    expected_timeframe_days: Optional[int] = Field(None, ge=1, description="Horizonte temporal en días")
    expected_outcome: Optional[str] = Field(None, description="Descripción detallada de la expectativa")
    evaluation_window_days: int = Field(DECISION_DEFAULT_EVALUATION_WINDOW_DAYS, ge=1, description="Ventana de evaluación en días")


class DecisionEvaluationUpdate(BaseModel):
    """Modelo para actualizar evaluación (notas y lecciones)."""
    evaluation_notes: Optional[str] = Field(None, description="Notas sobre el resultado")
    lessons_learned: Optional[str] = Field(None, description="Lecciones aprendidas")


class DecisionEvaluationResponse(BaseModel):
    """Modelo de respuesta para evaluación de decisión."""
    id: int
    decision_id: int
    price_at_decision: Optional[float]
    price_at_evaluation: Optional[float]
    result: str
    price_change_pct: Optional[float]
    outcome_match: Optional[bool]
    evaluation_notes: Optional[str]
    lessons_learned: Optional[str]
    evaluated_at: str

    @field_validator('evaluated_at', mode='before')
    @classmethod
    def convert_datetime(cls, v):
        if isinstance(v, datetime):
            return v.isoformat()
        return v

    model_config = ConfigDict(from_attributes=True)


class DecisionLogResponse(BaseModel):
    """Modelo de respuesta para log de decisión."""
    id: int
    portfolio_item_id: int
    portfolio_item_name: Optional[str] = None
    portfolio_item_symbol: Optional[str] = None
    decision_type: str
    reason: str
    signal_type: str
    signal_reference: Optional[str]
    expected_direction: Optional[str]
    expected_price: Optional[str]
    expected_timeframe_days: Optional[int]
    expected_outcome: Optional[str]
    status: str
    evaluation_window_days: int
    decided_at: str
    evaluated_at: Optional[str]
    evaluation: Optional[DecisionEvaluationResponse] = None

    @field_validator('decided_at', 'evaluated_at', mode='before')
    @classmethod
    def convert_datetime(cls, v):
        if isinstance(v, datetime):
            return v.isoformat()
        return v

    model_config = ConfigDict(from_attributes=True)


class DecisionLogListResponse(BaseModel):
    """Modelo de respuesta para lista de decisiones."""
    items: list[DecisionLogResponse]
    total: int
    pending_count: int
    evaluated_count: int


class DecisionStatisticsResponse(BaseModel):
    """Modelo de respuesta para estadísticas de decisiones."""
    overall: Dict
    by_signal_type: Dict[str, Dict]
    by_decision_type: Dict[str, Dict]


class AnalysisRequest(BaseModel):
    """Modelo para solicitar análisis."""
    pass  # No requiere parámetros, usa todas las noticias guardadas y la cartera


class AnalysisResponse(BaseModel):
    """Modelo de respuesta para análisis."""
    analysis: dict
    news_count: int
    portfolio_count: int
    generated_at: str
    version: str  # Timestamp de cuando se generó


# ==================== Portfolio Analysis Models ====================

class NewsItemAnalysis(BaseModel):
    """Análisis de un item de noticia individual."""
    news_id: int = Field(..., description="ID de la noticia analizada")
    news_title: str = Field(..., description="Título de la noticia")
    thesis_impact: str = Field(..., description="Impacto en la tesis de inversión")
    risk_flags: List[str] = Field(default_factory=list, description="Banderas de riesgo identificadas")
    confidence_level: str = Field(..., description="Nivel de confianza: high, med, o low")
    next_action: str = Field(..., description="Próxima acción recomendada: watch, add, trim, o exit")
    followup_questions: List[str] = Field(..., max_length=PORTFOLIO_ANALYSIS_MAX_FOLLOWUP_QUESTIONS, 
                                          description="1-2 preguntas de seguimiento para diligencia")

    @field_validator('confidence_level')
    @classmethod
    def validate_confidence(cls, v):
        """Valida que el nivel de confianza sea uno de los valores permitidos."""
        v_lower = v.lower()
        valid_levels = [level.lower() for level in PORTFOLIO_ANALYSIS_CONFIDENCE_LEVELS]
        if v_lower not in valid_levels:
            raise ValueError(f"Confidence level debe ser uno de: {', '.join(PORTFOLIO_ANALYSIS_CONFIDENCE_LEVELS)}")
        return v_lower

    @field_validator('next_action')
    @classmethod
    def validate_action(cls, v):
        """Valida que la acción sea una de las permitidas."""
        v_lower = v.lower()
        valid_actions = [action.lower() for action in PORTFOLIO_ANALYSIS_ACTIONS]
        if v_lower not in valid_actions:
            raise ValueError(f"Next action debe ser una de: {', '.join(PORTFOLIO_ANALYSIS_ACTIONS)}")
        return v_lower

    @field_validator('followup_questions')
    @classmethod
    def validate_followup_questions(cls, v):
        """Valida que haya entre 1 y 2 preguntas."""
        if not v or len(v) == 0:
            raise ValueError("Se requiere al menos una pregunta de seguimiento")
        if len(v) > PORTFOLIO_ANALYSIS_MAX_FOLLOWUP_QUESTIONS:
            raise ValueError(f"Máximo {PORTFOLIO_ANALYSIS_MAX_FOLLOWUP_QUESTIONS} preguntas de seguimiento permitidas")
        return [q.strip() for q in v if q.strip()]


class PortfolioAnalysisAggregate(BaseModel):
    """Vista agregada del análisis de cartera."""
    top_3_opportunities: List[str] = Field(..., min_length=1, max_length=3, 
                                           description="Top 3 oportunidades identificadas")
    top_3_risks: List[str] = Field(..., min_length=1, max_length=3, 
                                   description="Top 3 riesgos identificados")
    market_read: str = Field(..., description="Lectura del mercado en un párrafo")


class PortfolioAnalysisRequest(BaseModel):
    """Modelo para solicitar análisis de cartera."""
    news_ids: Optional[List[int]] = Field(None, description="IDs específicos de noticias a analizar. Si es None, analiza todas las estandarizadas")


class PortfolioAnalysisResponse(BaseModel):
    """Modelo de respuesta para análisis de cartera."""
    items: List[NewsItemAnalysis] = Field(..., description="Análisis por item de noticia")
    aggregate: PortfolioAnalysisAggregate = Field(..., description="Vista agregada del análisis")
    analyzed_news_count: int = Field(..., description="Cantidad de noticias analizadas")
    generated_at: str = Field(..., description="Fecha de generación del análisis")
