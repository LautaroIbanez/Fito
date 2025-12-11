"""Endpoints para oportunidades correlacionadas fuera de cartera."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import logging
import json
from datetime import datetime, timezone

from app.database import get_db, NewsItem, WatchlistItem, Sector, AssetCatalog
from app.models import (
    NewsOpportunitiesResponse,
    OpportunityAsset,
    WatchlistItemCreate,
    WatchlistItemResponse,
    WatchlistListResponse,
    StandardizedNewsData
)
from app.services.opportunity_inference_engine import OpportunityInferenceEngine
from app.services.sector_extraction_service import SectorExtractionService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/opportunities", tags=["opportunities"])

# Inicializar servicios
inference_engine = OpportunityInferenceEngine()
sector_extractor = SectorExtractionService()


@router.get("/news/{news_id}", response_model=NewsOpportunitiesResponse)
async def get_news_opportunities(
    news_id: int,
    db: Session = Depends(get_db)
):
    """
    Obtiene oportunidades correlacionadas fuera de cartera para una noticia específica.
    
    Identifica sectores/temas afectados y sugiere al menos 3 activos correlacionados
    con puntuación de impacto, señal (positiva/negativa) y justificación breve.
    """
    try:
        # Obtener noticia
        news_item_db = db.query(NewsItem).filter(NewsItem.id == news_id).first()
        if not news_item_db:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Noticia con ID {news_id} no encontrada"
            )
        
        # Convertir a modelo de respuesta
        from app.models import NewsItemResponse
        news_item = NewsItemResponse.model_validate(news_item_db)
        
        # Parsear datos estandarizados si existen
        standardized_data = None
        if news_item_db.standardized_data:
            try:
                standardized_dict = json.loads(news_item_db.standardized_data)
                standardized_data = StandardizedNewsData(**standardized_dict)
            except (json.JSONDecodeError, Exception) as e:
                logger.warning(f"Error parseando standardized_data para noticia {news_id}: {e}")
        
        # Extraer sectores y temas
        extraction_result = sector_extractor.extract_sectors_and_themes(
            news_item,
            standardized_data
        )
        
        # Inferir oportunidades
        opportunities_data = inference_engine.infer_opportunities(
            db,
            news_item,
            standardized_data
        )
        
        # Convertir a modelos Pydantic
        opportunities = [OpportunityAsset(**opp) for opp in opportunities_data]
        
        logger.info(f"Oportunidades generadas para noticia {news_id}: {len(opportunities)} activos")
        
        return NewsOpportunitiesResponse(
            news_id=news_id,
            news_title=news_item.title,
            sectors_detected=extraction_result["sectors"],
            themes_detected=extraction_result["themes"],
            opportunities=opportunities,
            generated_at=datetime.now(timezone.utc).isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generando oportunidades para noticia {news_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno al generar oportunidades: {str(e)}"
        )


@router.post("/watchlist", response_model=WatchlistItemResponse, status_code=status.HTTP_201_CREATED)
async def add_to_watchlist(
    item: WatchlistItemCreate,
    db: Session = Depends(get_db)
):
    """
    Agrega un activo sugerido a la watchlist del usuario.
    """
    try:
        # Buscar sector si se proporciona
        sector_id = None
        if item.sector:
            sector = db.query(Sector).filter(Sector.name == item.sector).first()
            if sector:
                sector_id = sector.id
        
        # Crear item de watchlist
        watchlist_item = WatchlistItem(
            symbol=item.symbol,
            name=item.name,
            asset_type=item.asset_type,
            sector_id=sector_id,
            added_from_news_id=item.added_from_news_id,
            notes=item.notes
        )
        
        db.add(watchlist_item)
        db.commit()
        db.refresh(watchlist_item)
        
        logger.info(f"Item agregado a watchlist: {item.symbol} ({item.name})")
        
        # Construir respuesta
        response = WatchlistItemResponse.model_validate(watchlist_item)
        if watchlist_item.sector:
            response.sector = watchlist_item.sector.name
        
        return response
        
    except Exception as e:
        logger.error(f"Error agregando item a watchlist: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno al agregar a watchlist: {str(e)}"
        )


@router.get("/watchlist", response_model=WatchlistListResponse)
async def get_watchlist(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    Obtiene todos los items en la watchlist.
    """
    try:
        total = db.query(WatchlistItem).count()
        items_db = db.query(WatchlistItem).order_by(WatchlistItem.created_at.desc()).offset(skip).limit(limit).all()
        
        items = []
        for item_db in items_db:
            item_response = WatchlistItemResponse.model_validate(item_db)
            if item_db.sector:
                item_response.sector = item_db.sector.name
            items.append(item_response)
        
        return WatchlistListResponse(
            items=items,
            total=total
        )
        
    except Exception as e:
        logger.error(f"Error obteniendo watchlist: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al obtener watchlist"
        )


@router.delete("/watchlist/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_from_watchlist(
    item_id: int,
    db: Session = Depends(get_db)
):
    """
    Elimina un item de la watchlist.
    """
    try:
        item = db.query(WatchlistItem).filter(WatchlistItem.id == item_id).first()
        
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Item de watchlist con ID {item_id} no encontrado"
            )
        
        db.delete(item)
        db.commit()
        
        logger.info(f"Item eliminado de watchlist: ID {item_id}")
        return None
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error eliminando item de watchlist {item_id}: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al eliminar de watchlist"
        )


