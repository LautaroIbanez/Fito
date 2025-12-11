"""Endpoints para gestión de tesis de activos."""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from sqlalchemy import desc
import logging

from app.database import get_db, AssetThesis, ThesisNewsLink, ChecklistItem, PortfolioItem, NewsItem
from app.models import (
    AssetThesisCreate,
    AssetThesisUpdate,
    AssetThesisResponse,
    AssetThesisListResponse,
    NewsLinkCreate,
    NewsLinkResponse,
    ChecklistItemCreate,
    ChecklistItemUpdate,
    ChecklistItemResponse
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/thesis", tags=["thesis"])


# ==================== Thesis CRUD ====================

@router.post("", response_model=AssetThesisResponse, status_code=status.HTTP_201_CREATED)
async def create_thesis(
    request: Request,
    thesis: AssetThesisCreate,
    db: Session = Depends(get_db)
):
    """Crea una nueva tesis para un activo."""
    try:
        # Verificar que el portfolio item existe
        portfolio_item = db.query(PortfolioItem).filter(PortfolioItem.id == thesis.portfolio_item_id).first()
        if not portfolio_item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Item de cartera con ID {thesis.portfolio_item_id} no encontrado"
            )
        
        # Verificar que no existe ya una tesis para este item
        existing = db.query(AssetThesis).filter(
            AssetThesis.portfolio_item_id == thesis.portfolio_item_id
        ).first()
        
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Ya existe una tesis para este activo. Use PUT para actualizarla."
            )
        
        db_thesis = AssetThesis(
            portfolio_item_id=thesis.portfolio_item_id,
            thesis_text=thesis.thesis_text,
            entry_reason=thesis.entry_reason,
            target_price=thesis.target_price,
            stop_loss=thesis.stop_loss,
            time_horizon=thesis.time_horizon
        )
        db.add(db_thesis)
        db.commit()
        db.refresh(db_thesis)
        
        logger.info(f"Tesis creada: ID {db_thesis.id} para portfolio item {thesis.portfolio_item_id}")
        
        # Construir respuesta
        return _build_thesis_response(db, db_thesis)
        
    except HTTPException:
        raise
    except ValueError as e:
        logger.warning(f"Error de validación al crear tesis: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error inesperado al crear tesis: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al crear la tesis"
        )


@router.get("", response_model=AssetThesisListResponse)
async def list_theses(
    portfolio_item_id: int = None,
    db: Session = Depends(get_db)
):
    """Lista todas las tesis o filtra por portfolio item."""
    try:
        query = db.query(AssetThesis)
        
        if portfolio_item_id:
            query = query.filter(AssetThesis.portfolio_item_id == portfolio_item_id)
        
        theses = query.order_by(desc(AssetThesis.updated_at)).all()
        
        return AssetThesisListResponse(
            items=[_build_thesis_response(db, thesis) for thesis in theses],
            total=len(theses)
        )
    except Exception as e:
        logger.error(f"Error al listar tesis: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al listar tesis"
        )


@router.get("/{thesis_id}", response_model=AssetThesisResponse)
async def get_thesis(
    thesis_id: int,
    db: Session = Depends(get_db)
):
    """Obtiene una tesis por ID."""
    try:
        thesis = db.query(AssetThesis).filter(AssetThesis.id == thesis_id).first()
        
        if not thesis:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tesis con ID {thesis_id} no encontrada"
            )
        
        return _build_thesis_response(db, thesis)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al obtener tesis {thesis_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al obtener la tesis"
        )


@router.put("/{thesis_id}", response_model=AssetThesisResponse)
async def update_thesis(
    thesis_id: int,
    thesis_update: AssetThesisUpdate,
    db: Session = Depends(get_db)
):
    """Actualiza una tesis existente."""
    try:
        thesis = db.query(AssetThesis).filter(AssetThesis.id == thesis_id).first()
        
        if not thesis:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tesis con ID {thesis_id} no encontrada"
            )
        
        # Actualizar campos proporcionados
        update_data = thesis_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(thesis, field, value)
        
        db.commit()
        db.refresh(thesis)
        
        logger.info(f"Tesis actualizada: ID {thesis_id}")
        return _build_thesis_response(db, thesis)
    except HTTPException:
        raise
    except ValueError as e:
        logger.warning(f"Error de validación al actualizar tesis: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error inesperado al actualizar tesis {thesis_id}: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al actualizar la tesis"
        )


@router.delete("/{thesis_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_thesis(
    thesis_id: int,
    db: Session = Depends(get_db)
):
    """Elimina una tesis por ID."""
    try:
        thesis = db.query(AssetThesis).filter(AssetThesis.id == thesis_id).first()
        
        if not thesis:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tesis con ID {thesis_id} no encontrada"
            )
        
        db.delete(thesis)
        db.commit()
        
        logger.info(f"Tesis eliminada: ID {thesis_id}")
        return None
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al eliminar tesis {thesis_id}: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al eliminar la tesis"
        )


# ==================== News Links ====================

@router.post("/{thesis_id}/news", response_model=NewsLinkResponse, status_code=status.HTTP_201_CREATED)
async def link_news_to_thesis(
    thesis_id: int,
    news_link: NewsLinkCreate,
    db: Session = Depends(get_db)
):
    """Vincula una noticia a una tesis."""
    try:
        # Verificar que la tesis existe
        thesis = db.query(AssetThesis).filter(AssetThesis.id == thesis_id).first()
        if not thesis:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tesis con ID {thesis_id} no encontrada"
            )
        
        # Verificar que la noticia existe
        news_item = db.query(NewsItem).filter(NewsItem.id == news_link.news_item_id).first()
        if not news_item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Noticia con ID {news_link.news_item_id} no encontrada"
            )
        
        # Verificar que no existe ya el vínculo
        existing = db.query(ThesisNewsLink).filter(
            ThesisNewsLink.thesis_id == thesis_id,
            ThesisNewsLink.news_item_id == news_link.news_item_id
        ).first()
        
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Esta noticia ya está vinculada a esta tesis"
            )
        
        db_link = ThesisNewsLink(
            thesis_id=thesis_id,
            news_item_id=news_link.news_item_id,
            relevance_note=news_link.relevance_note,
            is_key_news=news_link.is_key_news
        )
        db.add(db_link)
        db.commit()
        db.refresh(db_link)
        
        logger.info(f"Noticia {news_link.news_item_id} vinculada a tesis {thesis_id}")
        
        return _build_news_link_response(db, db_link)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al vincular noticia: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al vincular noticia"
        )


@router.delete("/{thesis_id}/news/{link_id}", status_code=status.HTTP_204_NO_CONTENT)
async def unlink_news_from_thesis(
    thesis_id: int,
    link_id: int,
    db: Session = Depends(get_db)
):
    """Desvincula una noticia de una tesis."""
    try:
        link = db.query(ThesisNewsLink).filter(
            ThesisNewsLink.id == link_id,
            ThesisNewsLink.thesis_id == thesis_id
        ).first()
        
        if not link:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Vínculo no encontrado"
            )
        
        db.delete(link)
        db.commit()
        
        logger.info(f"Vínculo {link_id} eliminado de tesis {thesis_id}")
        return None
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al desvincular noticia: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al desvincular noticia"
        )


# ==================== Checklist ====================

@router.post("/{thesis_id}/checklist", response_model=ChecklistItemResponse, status_code=status.HTTP_201_CREATED)
async def create_checklist_item(
    thesis_id: int,
    item: ChecklistItemCreate,
    db: Session = Depends(get_db)
):
    """Crea un item de checklist para una tesis."""
    try:
        thesis = db.query(AssetThesis).filter(AssetThesis.id == thesis_id).first()
        if not thesis:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tesis con ID {thesis_id} no encontrada"
            )
        
        db_item = ChecklistItem(
            thesis_id=thesis_id,
            title=item.title,
            description=item.description,
            order_index=item.order_index
        )
        db.add(db_item)
        db.commit()
        db.refresh(db_item)
        
        logger.info(f"Item de checklist creado: ID {db_item.id} para tesis {thesis_id}")
        return ChecklistItemResponse.model_validate(db_item)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al crear item de checklist: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al crear item de checklist"
        )


@router.put("/checklist/{item_id}", response_model=ChecklistItemResponse)
async def update_checklist_item(
    item_id: int,
    item_update: ChecklistItemUpdate,
    db: Session = Depends(get_db)
):
    """Actualiza un item de checklist."""
    try:
        item = db.query(ChecklistItem).filter(ChecklistItem.id == item_id).first()
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Item de checklist con ID {item_id} no encontrado"
            )
        
        update_data = item_update.model_dump(exclude_unset=True)
        
        # Si se marca como completado, actualizar fecha
        if 'is_completed' in update_data and update_data['is_completed'] and not item.is_completed:
            from datetime import datetime, timezone
            item.completed_at = datetime.now(timezone.utc)
        elif 'is_completed' in update_data and not update_data['is_completed']:
            item.completed_at = None
        
        for field, value in update_data.items():
            setattr(item, field, value)
        
        db.commit()
        db.refresh(item)
        
        logger.info(f"Item de checklist actualizado: ID {item_id}")
        return ChecklistItemResponse.model_validate(item)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al actualizar item de checklist: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al actualizar item de checklist"
        )


@router.delete("/checklist/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_checklist_item(
    item_id: int,
    db: Session = Depends(get_db)
):
    """Elimina un item de checklist."""
    try:
        item = db.query(ChecklistItem).filter(ChecklistItem.id == item_id).first()
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Item de checklist con ID {item_id} no encontrado"
            )
        
        db.delete(item)
        db.commit()
        
        logger.info(f"Item de checklist eliminado: ID {item_id}")
        return None
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al eliminar item de checklist: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al eliminar item de checklist"
        )


# ==================== Helper Functions ====================

def _build_thesis_response(db: Session, thesis: AssetThesis) -> AssetThesisResponse:
    """Construye respuesta completa de tesis con relaciones."""
    portfolio_item = db.query(PortfolioItem).filter(PortfolioItem.id == thesis.portfolio_item_id).first()
    
    # Obtener noticias vinculadas
    links = db.query(ThesisNewsLink).filter(ThesisNewsLink.thesis_id == thesis.id).all()
    linked_news = []
    for link in links:
        news_item = db.query(NewsItem).filter(NewsItem.id == link.news_item_id).first()
        linked_news.append(NewsLinkResponse(
            id=link.id,
            thesis_id=link.thesis_id,
            news_item_id=link.news_item_id,
            news_title=news_item.title if news_item else None,
            news_body_preview=news_item.body[:200] + "..." if news_item and news_item.body else None,
            relevance_note=link.relevance_note,
            is_key_news=link.is_key_news,
            linked_at=link.linked_at.isoformat()
        ))
    
    # Obtener items de checklist
    checklist_items = db.query(ChecklistItem).filter(
        ChecklistItem.thesis_id == thesis.id
    ).order_by(ChecklistItem.order_index).all()
    
    return AssetThesisResponse(
        id=thesis.id,
        portfolio_item_id=thesis.portfolio_item_id,
        portfolio_item_name=portfolio_item.name if portfolio_item else None,
        portfolio_item_symbol=portfolio_item.symbol if portfolio_item else None,
        thesis_text=thesis.thesis_text,
        entry_reason=thesis.entry_reason,
        target_price=thesis.target_price,
        stop_loss=thesis.stop_loss,
        time_horizon=thesis.time_horizon,
        linked_news=linked_news,
        checklist_items=[ChecklistItemResponse.model_validate(item) for item in checklist_items],
        created_at=thesis.created_at.isoformat(),
        updated_at=thesis.updated_at.isoformat()
    )


def _build_news_link_response(db: Session, link: ThesisNewsLink) -> NewsLinkResponse:
    """Construye respuesta de vínculo noticia-tesis."""
    news_item = db.query(NewsItem).filter(NewsItem.id == link.news_item_id).first()
    return NewsLinkResponse(
        id=link.id,
        thesis_id=link.thesis_id,
        news_item_id=link.news_item_id,
        news_title=news_item.title if news_item else None,
        news_body_preview=news_item.body[:200] + "..." if news_item and news_item.body else None,
        relevance_note=link.relevance_note,
        is_key_news=link.is_key_news,
        linked_at=link.linked_at.isoformat()
    )




