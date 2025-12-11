"""Endpoints para ingesta y gestión de noticias normalizadas."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
import logging
import json
from typing import List, Optional
from datetime import datetime, timezone

from app.database import get_db, NewsItem, NormalizedNews
from app.models import (
    NormalizedNewsCreate,
    NormalizedNewsResponse,
    NormalizedNewsListResponse,
    NewsItemResponse,
    StandardizedNewsData
)
from app.services.news_normalization_service import NewsNormalizationService
from app.config import NORMALIZED_NEWS_REJECT_ON_CRITICAL_ERROR

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/normalized-news", tags=["normalized-news"])

# Inicializar servicio
normalization_service = NewsNormalizationService()


@router.post("", response_model=NormalizedNewsResponse, status_code=status.HTTP_201_CREATED)
async def ingest_normalized_news(
    news_data: NormalizedNewsCreate,
    db: Session = Depends(get_db)
):
    """
    Ingresa una noticia normalizada al sistema.
    
    Valida todos los campos obligatorios y rangos. Si hay errores críticos
    y NORMALIZED_NEWS_REJECT_ON_CRITICAL_ERROR está activo, rechaza la noticia.
    """
    try:
        # Parsear timestamp
        try:
            timestamp = datetime.fromisoformat(news_data.timestamp.replace('Z', '+00:00'))
        except (ValueError, AttributeError) as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Timestamp inválido: {str(e)}"
            )
        
        # Construir diccionario normalizado
        normalized_dict = {
            "source": news_data.source,
            "timestamp": timestamp,
            "summary": news_data.summary,
            "sentiment": news_data.sentiment,
            "impact_score": news_data.impact_score,
            "tickers": news_data.tickers or [],
            "entities": news_data.entities or [],
            "title": news_data.title,
            "original_text": news_data.original_text,
            "categories": news_data.categories or [],
            "metadata": news_data.metadata or {}
        }
        
        # Validar
        is_valid, validation_errors = normalization_service.validate_normalized_news(normalized_dict)
        
        # Si hay errores críticos y está configurado para rechazar, rechazar
        if not is_valid and NORMALIZED_NEWS_REJECT_ON_CRITICAL_ERROR:
            error_msg = "; ".join(validation_errors)
            logger.warning(f"Noticia rechazada por errores críticos: {error_msg}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Noticia rechazada por errores de validación: {error_msg}"
            )
        
        # Guardar
        db_item = normalization_service.save_normalized_news(
            db,
            normalized_dict,
            validation_errors,
            original_news_id=news_data.original_news_id
        )
        
        logger.info(f"Noticia normalizada ingresada: ID {db_item.id}, status: {db_item.status}")
        
        return NormalizedNewsResponse.model_validate(db_item)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error inesperado al ingresar noticia normalizada: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno al ingresar noticia: {str(e)}"
        )


@router.post("/from-news/{news_id}", response_model=NormalizedNewsResponse, status_code=status.HTTP_201_CREATED)
async def normalize_existing_news(
    news_id: int,
    db: Session = Depends(get_db)
):
    """
    Normaliza una noticia existente y la guarda en el esquema unificado.
    
    Transforma una noticia de la tabla news_items al esquema normalizado.
    """
    try:
        # Obtener noticia original
        news_item_db = db.query(NewsItem).filter(NewsItem.id == news_id).first()
        if not news_item_db:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Noticia con ID {news_id} no encontrada"
            )
        
        # Convertir a modelo de respuesta
        news_item = NewsItemResponse.model_validate(news_item_db)
        
        # Parsear datos estandarizados si existen
        standardized_data = None
        if news_item_db.standardized_data:
            try:
                standardized_dict = json.loads(news_item_db.standardized_data)
                standardized_data = StandardizedNewsData(**standardized_dict)
            except (json.JSONDecodeError, TypeError, Exception) as e:
                logger.warning(f"Error parseando standardized_data para noticia {news_id}: {e}")
        
        # Normalizar
        normalized_dict, validation_errors = normalization_service.normalize_news(
            news_item,
            standardized_data
        )
        
        # Validar
        is_valid, additional_errors = normalization_service.validate_normalized_news(normalized_dict)
        all_errors = validation_errors + additional_errors
        
        # Si hay errores críticos y está configurado para rechazar, rechazar
        if not is_valid and NORMALIZED_NEWS_REJECT_ON_CRITICAL_ERROR:
            error_msg = "; ".join(all_errors)
            logger.warning(f"Noticia {news_id} rechazada por errores críticos: {error_msg}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Noticia rechazada por errores de validación: {error_msg}"
            )
        
        # Guardar
        db_item = normalization_service.save_normalized_news(
            db,
            normalized_dict,
            all_errors,
            original_news_id=news_id
        )
        
        logger.info(f"Noticia {news_id} normalizada: ID normalizado {db_item.id}, status: {db_item.status}")
        
        return NormalizedNewsResponse.model_validate(db_item)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error normalizando noticia {news_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno al normalizar noticia: {str(e)}"
        )


@router.get("", response_model=NormalizedNewsListResponse)
async def list_normalized_news(
    skip: int = 0,
    limit: int = 100,
    status_filter: Optional[str] = None,  # valid, error, warning
    sentiment_filter: Optional[str] = None,  # bullish, bearish, neutral
    source_filter: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Lista noticias normalizadas con filtros opcionales.
    """
    try:
        query = db.query(NormalizedNews)
        
        # Aplicar filtros
        if status_filter:
            query = query.filter(NormalizedNews.status == status_filter)
        
        if sentiment_filter:
            query = query.filter(NormalizedNews.sentiment == sentiment_filter.lower())
        
        if source_filter:
            query = query.filter(NormalizedNews.source.ilike(f"%{source_filter}%"))
        
        # Contar totales por status
        total = query.count()
        valid_count = db.query(NormalizedNews).filter(NormalizedNews.status == "valid").count()
        error_count = db.query(NormalizedNews).filter(NormalizedNews.status == "error").count()
        warning_count = db.query(NormalizedNews).filter(NormalizedNews.status == "warning").count()
        
        # Ordenar y paginar
        items_db = query.order_by(desc(NormalizedNews.timestamp)).offset(skip).limit(limit).all()
        
        items = [NormalizedNewsResponse.model_validate(item) for item in items_db]
        
        return NormalizedNewsListResponse(
            items=items,
            total=total,
            valid_count=valid_count,
            error_count=error_count,
            warning_count=warning_count
        )
        
    except Exception as e:
        logger.error(f"Error listando noticias normalizadas: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al listar noticias normalizadas"
        )


@router.get("/{normalized_id}", response_model=NormalizedNewsResponse)
async def get_normalized_news(
    normalized_id: int,
    db: Session = Depends(get_db)
):
    """
    Obtiene una noticia normalizada por ID.
    """
    try:
        item = db.query(NormalizedNews).filter(NormalizedNews.id == normalized_id).first()
        
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Noticia normalizada con ID {normalized_id} no encontrada"
            )
        
        return NormalizedNewsResponse.model_validate(item)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo noticia normalizada {normalized_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al obtener noticia normalizada"
        )


