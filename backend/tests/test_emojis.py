"""Tests para verificar que los emojis se preservan correctamente."""
import pytest
from app.models import NewsItemCreate


def test_emojis_in_body():
    """Test que los emojis se preservan en el cuerpo de la noticia."""
    body = "a" * 150 + "😀 🎉 📰 ✅ 🚀 💡 📊 ⚠️ 🔍 📝" + "a" * 40
    item = NewsItemCreate(body=body, title="Noticia con emojis 😀")
    
    assert "😀" in item.body
    assert "🎉" in item.body
    assert "📰" in item.body
    assert "✅" in item.body
    assert len(item.body) >= 200


def test_emojis_in_title():
    """Test que los emojis se preservan en el título."""
    body = "a" * 200
    title = "Título con emojis 😀 🎉 📰"
    item = NewsItemCreate(body=body, title=title)
    
    assert "😀" in item.title
    assert "🎉" in item.title
    assert "📰" in item.title


def test_emojis_in_source():
    """Test que los emojis se preservan en la fuente."""
    body = "a" * 200
    source = "Fuente 📰 News"
    item = NewsItemCreate(body=body, source=source)
    
    assert "📰" in item.source


def test_unicode_characters():
    """Test que caracteres Unicode especiales se preservan."""
    body = "a" * 150 + "áéíóú ñ ç ü ö ä" + "a" * 40
    item = NewsItemCreate(body=body)
    
    assert "á" in item.body
    assert "ñ" in item.body
    assert "ü" in item.body


def test_emojis_preserved_after_sanitization():
    """Test que los emojis sobreviven a la sanitización."""
    # Incluir emojis y caracteres de control
    body = "a" * 150 + "Texto con emojis 😀🎉\x00y caracteres de control" + "a" * 40
    item = NewsItemCreate(body=body)
    
    # Los emojis deben estar presentes
    assert "😀" in item.body
    assert "🎉" in item.body
    # Los caracteres de control deben ser eliminados
    assert "\x00" not in item.body




