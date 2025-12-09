"""Tests para validación de noticias."""
import pytest
from pydantic import ValidationError
from app.models import NewsItemCreate


def test_valid_news_item():
    """Test que una noticia válida se crea correctamente."""
    body = "a" * 200  # Mínimo de caracteres
    item = NewsItemCreate(body=body)
    assert item.body == body
    assert item.title is None
    assert item.source is None


def test_news_item_with_title_and_source():
    """Test noticia con título y fuente."""
    body = "a" * 300
    title = "Título de prueba"
    source = "Fuente de prueba"
    item = NewsItemCreate(body=body, title=title, source=source)
    assert item.body == body
    assert item.title == title
    assert item.source == source


def test_news_item_too_short():
    """Test que rechaza noticias muy cortas."""
    with pytest.raises(ValidationError) as exc_info:
        NewsItemCreate(body="a" * 199)  # Menos del mínimo
    
    errors = exc_info.value.errors()
    assert any("200" in str(error) for error in errors)


def test_news_item_too_long():
    """Test que rechaza noticias muy largas."""
    with pytest.raises(ValidationError) as exc_info:
        NewsItemCreate(body="a" * 10001)  # Más del máximo
    
    errors = exc_info.value.errors()
    assert any("10000" in str(error) for error in errors)


def test_news_item_empty_body():
    """Test que rechaza cuerpo vacío."""
    with pytest.raises(ValidationError):
        NewsItemCreate(body="")


def test_news_item_title_too_long():
    """Test que rechaza títulos muy largos."""
    body = "a" * 300
    with pytest.raises(ValidationError) as exc_info:
        NewsItemCreate(body=body, title="a" * 201)
    
    errors = exc_info.value.errors()
    assert any("200" in str(error) for error in errors)


def test_news_item_sanitization():
    """Test que sanitiza caracteres de control."""
    body = "Texto normal\ncon salto de línea\x00caracter control"
    item = NewsItemCreate(body=body)
    assert "\x00" not in item.body
    assert "\n" in item.body  # Los saltos de línea se mantienen


def test_news_item_html_escaping():
    """Test que escapa HTML."""
    body = "a" * 200 + "<script>alert('xss')</script>"
    item = NewsItemCreate(body=body)
    assert "<script>" not in item.body
    assert "&lt;script&gt;" in item.body

