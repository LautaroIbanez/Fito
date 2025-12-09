"""Endpoints para gestión de cartera."""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from sqlalchemy import desc
import logging

from app.database import get_db, PortfolioItem
from app.models import (
    PortfolioItemCreate,
    PortfolioItemResponse,
    PortfolioListResponse
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/portfolio", tags=["portfolio"])


@router.post("", response_model=PortfolioItemResponse, status_code=status.HTTP_201_CREATED)
async def create_portfolio_item(
    request: Request,
    item: PortfolioItemCreate,
    db: Session = Depends(get_db)
):
    """
    Crea un nuevo item en la cartera.
    """
    try:
        db_item = PortfolioItem(
            asset_type=item.asset_type,
            name=item.name,
            symbol=item.symbol,
            quantity=item.quantity,
            price=item.price,
            total_value=item.total_value,
            currency=item.currency,
            notes=item.notes
        )
        db.add(db_item)
        db.commit()
        db.refresh(db_item)
        
        logger.info(f"Item de cartera creado: ID {db_item.id} - {item.name}")
        return PortfolioItemResponse.model_validate(db_item)
        
    except ValueError as e:
        logger.warning(f"Error de validación al crear item de cartera: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error inesperado al crear item de cartera: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al crear el item de cartera"
        )


@router.get("", response_model=PortfolioListResponse)
async def list_portfolio(
    db: Session = Depends(get_db)
):
    """
    Lista todos los items de la cartera ordenados por fecha de actualización.
    """
    try:
        total = db.query(PortfolioItem).count()
        items = db.query(PortfolioItem).order_by(desc(PortfolioItem.updated_at)).all()
        
        return PortfolioListResponse(
            items=[PortfolioItemResponse.model_validate(item) for item in items],
            total=total
        )
    except Exception as e:
        logger.error(f"Error al listar cartera: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al listar la cartera"
        )


@router.put("/{item_id}", response_model=PortfolioItemResponse)
async def update_portfolio_item(
    request: Request,
    item_id: int,
    item: PortfolioItemCreate,
    db: Session = Depends(get_db)
):
    """
    Actualiza un item de la cartera.
    """
    try:
        db_item = db.query(PortfolioItem).filter(PortfolioItem.id == item_id).first()
        
        if not db_item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Item de cartera con ID {item_id} no encontrado"
            )
        
        # Actualizar campos
        db_item.asset_type = item.asset_type
        db_item.name = item.name
        db_item.symbol = item.symbol
        db_item.quantity = item.quantity
        db_item.price = item.price
        db_item.total_value = item.total_value
        db_item.currency = item.currency
        db_item.notes = item.notes
        # updated_at se actualiza automáticamente por el modelo
        
        db.commit()
        db.refresh(db_item)
        
        logger.info(f"Item de cartera actualizado: ID {item_id}")
        return PortfolioItemResponse.model_validate(db_item)
        
    except HTTPException:
        raise
    except ValueError as e:
        logger.warning(f"Error de validación al actualizar item de cartera: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error al actualizar item de cartera {item_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al actualizar el item de cartera"
        )


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_portfolio_item(
    item_id: int,
    db: Session = Depends(get_db)
):
    """
    Elimina un item de la cartera por ID.
    """
    try:
        item = db.query(PortfolioItem).filter(PortfolioItem.id == item_id).first()
        
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Item de cartera con ID {item_id} no encontrado"
            )
        
        db.delete(item)
        db.commit()
        
        logger.info(f"Item de cartera eliminado: ID {item_id}")
        return None
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al eliminar item de cartera {item_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al eliminar el item de cartera"
        )

