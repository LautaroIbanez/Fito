"""Endpoints para gestión de noticias."""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List
import logging
import json

from app.database import get_db, NewsItem, PortfolioItem
from app.models import (
    NewsItemCreate, NewsItemResponse, NewsListResponse, NewsItemStandardizedCreate,
    StandardizedNewsData, PortfolioItemResponse, SituationSummaryResponse
)
from app.services.news_scoring_service import NewsScoringService
from app.services.news_preprocessing_service import NewsPreprocessingService
from app.services.situation_summary_service import SituationSummaryService
from datetime import datetime, timezone

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/news", tags=["news"])


@router.post("/standardize", response_model=NewsItemResponse, status_code=status.HTTP_201_CREATED)
async def save_standardized_news(
    request: Request,
    news_item: NewsItemStandardizedCreate,
    db: Session = Depends(get_db)
):
    """
    Guarda una noticia estandarizada.
    
    Aplica un prompt de primera pasada al artículo para extraer:
    - Título, fecha de publicación, fuente
    - Resumen de 3-5 bullets (máx 50 palabras cada uno)
    - Personas/empresas clave
    - Números/métricas citadas
    - Sentimiento (bullish/bearish/neutral)
    - Una línea "por qué importa" desde perspectiva de inversor
    
    Los datos estandarizados se guardan en formato JSON para consumo uniforme por prompts posteriores.
    """
    try:
        # Estandarizar la noticia usando OpenAI
        preprocessing_service = NewsPreprocessingService()
        standardized_data = preprocessing_service.standardize_news(news_item.article_text)
        
        # Crear el item de noticia con datos estandarizados
        db_item = NewsItem(
            title=standardized_data.title,
            body=news_item.article_text,  # Guardar el texto original completo
            source=standardized_data.source,
            standardized_data=json.dumps(standardized_data.model_dump(), ensure_ascii=False)
        )
        
        db.add(db_item)
        db.commit()
        db.refresh(db_item)
        
        logger.info(f"Noticia estandarizada creada: ID {db_item.id}, título: {standardized_data.title}")
        
        # Construir respuesta con datos estandarizados
        response = NewsItemResponse.model_validate(db_item)
        response.standardized_data = standardized_data
        
        return response
        
    except ValueError as e:
        logger.warning(f"Error de validación al estandarizar noticia: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error inesperado al estandarizar noticia: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno al estandarizar la noticia: {str(e)}"
        )


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
        
        # Parsear standardized_data si existe
        response = NewsItemResponse.model_validate(db_item)
        if db_item.standardized_data:
            try:
                standardized_dict = json.loads(db_item.standardized_data)
                response.standardized_data = StandardizedNewsData(**standardized_dict)
            except (json.JSONDecodeError, Exception) as e:
                logger.warning(f"Error parseando standardized_data para noticia {db_item.id}: {e}")
                response.standardized_data = None
        
        return response
        
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
    sort_by: str = "score",  # "score" o "date"
    db: Session = Depends(get_db)
):
    """
    Lista todas las noticias ordenadas por score (default) o fecha descendente.
    
    Soporta paginación con skip y limit.
    Ordena por score de relevancia cuando sort_by="score" (default).
    """
    try:
        total = db.query(NewsItem).count()
        
        # Obtener todas las noticias
        all_items = db.query(NewsItem).all()
        
        # Obtener cartera para scoring
        portfolio_items_db = db.query(PortfolioItem).all()
        portfolio_items = [PortfolioItemResponse.model_validate(item) for item in portfolio_items_db]
        
        # Calcular scores y ordenar
        scoring_service = NewsScoringService()
        news_items = []
        for item in all_items:
            response_item = NewsItemResponse.model_validate(item)
            # Parsear standardized_data si existe
            if item.standardized_data:
                try:
                    standardized_dict = json.loads(item.standardized_data)
                    response_item.standardized_data = StandardizedNewsData(**standardized_dict)
                except (json.JSONDecodeError, Exception) as e:
                    logger.warning(f"Error parseando standardized_data para noticia {item.id}: {e}")
                    response_item.standardized_data = None
            news_items.append(response_item)
        
        if sort_by == "score" and portfolio_items:
            # Ordenar por score
            scored_news = scoring_service.score_and_sort_news(news_items, portfolio_items)
            sorted_items = [item for item, score_dict in scored_news]
            
            # Agregar score a cada item
            for item, score_dict in scored_news:
                item.score = score_dict["score"]
                item.score_components = score_dict["components"]
                item.is_obsolete = score_dict["components"]["is_obsolete"]
        else:
            # Ordenar por fecha (comportamiento original)
            sorted_items = sorted(news_items, key=lambda x: x.created_at, reverse=True)
        
        # Aplicar paginación
        paginated_items = sorted_items[skip:skip + limit]
        
        return NewsListResponse(
            items=paginated_items,
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


@router.delete("", response_model=NewsListResponse, status_code=status.HTTP_200_OK)
async def clear_all_news(
    db: Session = Depends(get_db)
):
    """
    Elimina todas las noticias almacenadas y devuelve una lista vacía.
    """
    try:
        # Contar noticias antes de eliminar
        total_before = db.query(NewsItem).count()
        
        # Eliminar todas las noticias
        db.query(NewsItem).delete()
        db.commit()
        
        logger.info(f"Todas las noticias eliminadas: {total_before} noticias borradas")
        
        # Devolver lista vacía
        return NewsListResponse(
            items=[],
            total=0
        )
        
    except Exception as e:
        logger.error(f"Error al limpiar todas las noticias: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al limpiar las noticias"
        )


@router.get("/summary", response_model=SituationSummaryResponse, status_code=status.HTTP_200_OK)
async def get_situation_summary(
    db: Session = Depends(get_db)
):
    """
    Genera un resumen conciso de la situación actual del mercado basado en las noticias almacenadas.
    
    El resumen se genera automáticamente desde las noticias más recientes y proporciona
    una visión general de la situación actual del mercado.
    """
    try:
        # Obtener todas las noticias
        news_items = db.query(NewsItem).order_by(desc(NewsItem.created_at)).all()
        
        if not news_items:
            # Retornar respuesta vacía sin error
            return SituationSummaryResponse(
                summary="",
                news_count=0,
                recent_news_count=0,
                generated_at=datetime.now(timezone.utc).isoformat(),
                has_content=False,
                tokens_used=None
            )
        
        # Convertir a modelos de respuesta
        news_responses = [NewsItemResponse.model_validate(item) for item in news_items]
        
        # Generar resumen
        summary_service = SituationSummaryService()
        summary_result = summary_service.generate_summary(news_responses)
        
        logger.info(f"Resumen de situación generado para {summary_result['news_count']} noticias")
        
        return SituationSummaryResponse(**summary_result)
        
    except ValueError as e:
        logger.warning(f"Error de validación al generar resumen: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error inesperado al generar resumen: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno al generar resumen: {str(e)}"
        )

