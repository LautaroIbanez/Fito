"""Tests para el servicio de OpenAI."""
import pytest
from app.services.openai_service import OpenAIService
from app.models import NewsItemResponse


def test_build_prompt():
    """Test construcción del prompt."""
    service = OpenAIService()
    
    news_items = [
        NewsItemResponse(
            id=1,
            title="Título 1",
            body="Contenido de la noticia 1" * 20,
            source="Fuente 1",
            created_at="2025-12-09T10:00:00"
        ),
        NewsItemResponse(
            id=2,
            title="Título 2",
            body="Contenido de la noticia 2" * 20,
            source=None,
            created_at="2025-12-09T11:00:00"
        ),
    ]
    
    prompt = service.build_prompt(news_items)
    
    assert "Título 1" in prompt
    assert "Fuente 1" in prompt
    assert "Título 2" in prompt
    assert "RESUMEN EJECUTIVO" in prompt
    assert "RIESGOS IDENTIFICADOS" in prompt
    assert "ACTORES CLAVE" in prompt
    assert "SEÑALES TEMPRANAS" in prompt
    assert "CONCLUSIONES ACCIONABLES" in prompt


def test_build_prompt_empty_list():
    """Test que requiere al menos una noticia."""
    service = OpenAIService()
    
    with pytest.raises(ValueError, match="al menos una noticia"):
        service.generate_analysis([])

