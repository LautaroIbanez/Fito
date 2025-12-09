"""Endpoints para gestión de noticias."""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List
import logging

from app.database import get_db, NewsItem
from app.models import NewsItemCreate, NewsItemResponse, NewsListResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/news", tags=["news"])


@router.post("", response_model=NewsItemResponse, status_code=status.HTTP_201_CREATED)
async def create_news(
    request: Request,
    news_item: NewsItemCreate,
    db: Session = Depends(get_db)
):
    # Rate limiting aplicado a nivel de aplicación
    """
    Crea una nueva noticia.
    
    Valida que el cuerpo tenga entre 200 y 10000 caracteres.
    """
    try:
        db_item = NewsItem(
            title=news_item.title,
            body=news_item.body,
            source=news_item.source
        )
        db.add(db_item)
        db.commit()
        db.refresh(db_item)
        
        logger.info(f"Noticia creada: ID {db_item.id}")
        return NewsItemResponse.model_validate(db_item)
        
    except ValueError as e:
        logger.warning(f"Error de validación al crear noticia: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error inesperado al crear noticia: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al crear la noticia"
        )


@router.get("", response_model=NewsListResponse)
async def list_news(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    Lista todas las noticias ordenadas por fecha descendente.
    
    Soporta paginación con skip y limit.
    """
    try:
        total = db.query(NewsItem).count()
        items = db.query(NewsItem).order_by(desc(NewsItem.created_at)).offset(skip).limit(limit).all()
        
        return NewsListResponse(
            items=[NewsItemResponse.model_validate(item) for item in items],
            total=total
        )
    except Exception as e:
        logger.error(f"Error al listar noticias: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al listar noticias"
        )


@router.delete("/{news_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_news(
    news_id: int,
    db: Session = Depends(get_db)
):
    """
    Elimina una noticia por ID.
    """
    try:
        item = db.query(NewsItem).filter(NewsItem.id == news_id).first()
        
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Noticia con ID {news_id} no encontrada"
            )
        
        db.delete(item)
        db.commit()
        
        logger.info(f"Noticia eliminada: ID {news_id}")
        return None
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al eliminar noticia {news_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al eliminar la noticia"
        )

