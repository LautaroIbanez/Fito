"""Modelos Pydantic para validación de requests/responses."""
from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Optional
from datetime import datetime
import re


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


class NewsItemResponse(BaseModel):
    """Modelo de respuesta para una noticia."""
    id: int
    title: Optional[str]
    body: str
    source: Optional[str]
    created_at: str

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
