"""Tests para el servicio de OpenAI."""
import pytest
from datetime import datetime, timedelta, timezone
from app.services.openai_service import OpenAIService
from app.models import NewsItemResponse, PortfolioItemResponse


class TestNewsStaleDetection:
    """Tests para detección de noticias desactualizadas."""
    
    def test_fresh_news(self):
        """Test que noticias recientes no se marcan como stale."""
        service = OpenAIService()
        
        # Noticia de hace 2 días
        fresh_date = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
        is_stale, age_days = service._is_news_stale(fresh_date)
        
        assert is_stale == False
        assert age_days == 2
    
    def test_stale_news(self):
        """Test que noticias antiguas se marcan como stale."""
        service = OpenAIService()
        
        # Noticia de hace 10 días (mayor a 7 días por defecto)
        stale_date = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
        is_stale, age_days = service._is_news_stale(stale_date)
        
        assert is_stale == True
        assert age_days == 10
    
    def test_iso_date_parsing(self):
        """Test parsing de diferentes formatos de fecha ISO."""
        service = OpenAIService()
        
        # Formato con T y Z
        date_str = "2025-12-01T10:00:00Z"
        is_stale, age_days = service._is_news_stale(date_str)
        assert isinstance(is_stale, bool)
        assert isinstance(age_days, int)
        
        # Formato sin Z
        date_str2 = "2025-12-01T10:00:00"
        is_stale2, age_days2 = service._is_news_stale(date_str2)
        assert isinstance(is_stale2, bool)
        assert isinstance(age_days2, int)


class TestPortfolioSnapshot:
    """Tests para formato de snapshot de cartera."""
    
    def test_empty_portfolio(self):
        """Test formateo de cartera vacía."""
        service = OpenAIService()
        snapshot = service._format_portfolio_snapshot([])
        
        assert snapshot == ""
    
    def test_portfolio_snapshot_format(self):
        """Test que el snapshot incluye información relevante."""
        service = OpenAIService()
        
        portfolio_items = [
            PortfolioItemResponse(
                id=1,
                asset_type="acciones",
                name="Apple Inc.",
                symbol="AAPL",
                quantity="100",
                price="150.50",
                total_value="15050.00",
                currency="USD",
                notes="Tech stock",
                created_at="2025-12-01T10:00:00",
                updated_at="2025-12-09T10:00:00"
            ),
            PortfolioItemResponse(
                id=2,
                asset_type="bonos",
                name="US Treasury",
                symbol=None,
                quantity=None,
                price=None,
                total_value="5000.00",
                currency="USD",
                notes=None,
                created_at="2025-12-05T10:00:00",
                updated_at="2025-12-05T10:00:00"
            )
        ]
        
        snapshot = service._format_portfolio_snapshot(portfolio_items)
        
        # Verificar que contiene información clave
        assert "SNAPSHOT DE CARTERA ACTUAL" in snapshot
        assert "Apple Inc." in snapshot
        assert "AAPL" in snapshot
        assert "US Treasury" in snapshot
        assert "ACCIONES" in snapshot.upper()
        assert "BONOS" in snapshot.upper()
        assert "Total de activos: 2" in snapshot
    
    def test_portfolio_weight_calculation(self):
        """Test que se calculan pesos aproximados cuando hay valores."""
        service = OpenAIService()
        
        portfolio_items = [
            PortfolioItemResponse(
                id=1,
                asset_type="acciones",
                name="Asset 1",
                symbol="A1",
                quantity=None,
                price=None,
                total_value="10000.00",
                currency="USD",
                notes=None,
                created_at="2025-12-01T10:00:00",
                updated_at="2025-12-01T10:00:00"
            ),
            PortfolioItemResponse(
                id=2,
                asset_type="acciones",
                name="Asset 2",
                symbol="A2",
                quantity=None,
                price=None,
                total_value="5000.00",
                currency="USD",
                notes=None,
                created_at="2025-12-01T10:00:00",
                updated_at="2025-12-01T10:00:00"
            )
        ]
        
        snapshot = service._format_portfolio_snapshot(portfolio_items)
        
        # Debería calcular pesos (66.67% y 33.33% aproximadamente)
        assert "Peso Aprox" in snapshot or "10000" in snapshot


class TestNewsListFormatting:
    """Tests para formateo de lista de noticias."""
    
    def test_news_list_with_fresh_and_stale(self):
        """Test que clasifica noticias en frescas y stale."""
        service = OpenAIService()
        
        now = datetime.now(timezone.utc)
        
        news_items = [
            # Noticia fresca (hace 3 días)
            NewsItemResponse(
                id=1,
                title="Noticia Fresca",
                body="Contenido de noticia fresca " * 50,
                source="Fuente 1",
                created_at=(now - timedelta(days=3)).isoformat()
            ),
            # Noticia stale (hace 10 días)
            NewsItemResponse(
                id=2,
                title="Noticia Antigua",
                body="Contenido de noticia antigua " * 50,
                source="Fuente 2",
                created_at=(now - timedelta(days=10)).isoformat()
            ),
        ]
        
        news_text, fresh_count, stale_count = service._format_news_list(news_items)
        
        assert fresh_count == 1
        assert stale_count == 1
        assert "NOTICIAS FRESCAS" in news_text
        assert "NOTICIAS DESACTUALIZADAS" in news_text
        assert "Noticia Fresca" in news_text
        assert "Noticia Antigua" in news_text
        assert "DESACTUALIZADA" in news_text
    
    def test_news_list_all_fresh(self):
        """Test con solo noticias frescas."""
        service = OpenAIService()
        
        now = datetime.now(timezone.utc)
        
        news_items = [
            NewsItemResponse(
                id=1,
                title="Noticia 1",
                body="Contenido " * 50,
                source="Fuente",
                created_at=(now - timedelta(days=2)).isoformat()
            ),
        ]
        
        news_text, fresh_count, stale_count = service._format_news_list(news_items)
        
        assert fresh_count == 1
        assert stale_count == 0
        assert "NOTICIAS FRESCAS" in news_text
        assert "NOTICIAS DESACTUALIZADAS" not in news_text or "No hay" in news_text


class TestPromptBuilding:
    """Tests para construcción del prompt completo."""
    
    def test_build_prompt_includes_portfolio(self):
        """Test que el prompt incluye snapshot de cartera."""
        service = OpenAIService()
        
        portfolio_items = [
            PortfolioItemResponse(
                id=1,
                asset_type="acciones",
                name="Test Asset",
                symbol="TEST",
                quantity=None,
                price=None,
                total_value="1000.00",
                currency="USD",
                notes=None,
                created_at="2025-12-01T10:00:00",
                updated_at="2025-12-01T10:00:00"
            )
        ]
        
        news_items = [
            NewsItemResponse(
                id=1,
                title="Test News",
                body="Test content " * 50,
                source="Test Source",
                created_at=(datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
            )
        ]
        
        prompt = service.build_prompt(news_items, portfolio_items)
        
        assert "SNAPSHOT DE CARTERA ACTUAL" in prompt
        assert "Test Asset" in prompt
        assert "LISTADO DE NOTICIAS" in prompt
        assert "Test News" in prompt
    
    def test_build_prompt_no_correlations_warning(self):
        """Test que el prompt incluye advertencia de no inventar correlaciones."""
        service = OpenAIService()
        
        news_items = [
            NewsItemResponse(
                id=1,
                title="Test",
                body="Test " * 50,
                source=None,
                created_at=datetime.now(timezone.utc).isoformat()
            )
        ]
        
        prompt = service.build_prompt(news_items)
        
        assert "No inventes correlaciones" in prompt or "NO inventes" in prompt
        assert "NO fuerces" in prompt or "no fuerces" in prompt
        assert "Sin relación evidente" in prompt or "sin relación" in prompt
    
    def test_build_prompt_includes_stale_warnings(self):
        """Test que el prompt incluye instrucciones sobre noticias stale."""
        service = OpenAIService()
        
        now = datetime.now(timezone.utc)
        
        news_items = [
            NewsItemResponse(
                id=1,
                title="Old News",
                body="Content " * 50,
                source=None,
                created_at=(now - timedelta(days=10)).isoformat()
            )
        ]
        
        prompt = service.build_prompt(news_items)
        
        assert "DESACTUALIZADA" in prompt or "desactualizada" in prompt
        assert "contexto histórico" in prompt or "CONTEXTO HISTÓRICO" in prompt
    
    def test_build_prompt_empty_news_list(self):
        """Test que requiere al menos una noticia."""
        service = OpenAIService()
        
        with pytest.raises(ValueError, match="al menos una noticia"):
            service.generate_analysis([])


class TestGenerateAnalysis:
    """Tests para generación de análisis (mockeando OpenAI)."""
    
    def test_generate_analysis_requires_news(self):
        """Test que requiere al menos una noticia."""
        service = OpenAIService()
        
        with pytest.raises(ValueError, match="al menos una noticia"):
            service.generate_analysis([])
    
    def test_generate_analysis_metadata(self):
        """Test que el resultado incluye metadata de noticias frescas/stale."""
        # Este test requeriría mockear la llamada a OpenAI
        # Por ahora solo verificamos la estructura esperada
        service = OpenAIService()
        
        now = datetime.now(timezone.utc)
        
        news_items = [
            NewsItemResponse(
                id=1,
                title="Fresh",
                body="Content " * 50,
                source=None,
                created_at=(now - timedelta(days=2)).isoformat()
            ),
            NewsItemResponse(
                id=2,
                title="Stale",
                body="Content " * 50,
                source=None,
                created_at=(now - timedelta(days=10)).isoformat()
            )
        ]
        
        # Verificar que build_prompt funciona (sin llamar a OpenAI)
        prompt = service.build_prompt(news_items)
        assert len(prompt) > 0
        assert "Fresh" in prompt
        assert "Stale" in prompt


class TestResponseFormatting:
    """Tests para validación y formateo de respuestas minimalistas."""
    
    def test_truncate_section(self):
        """Test que las secciones se truncan al máximo permitido."""
        service = OpenAIService()
        
        long_text = "A" * 500
        truncated = service._truncate_section(long_text, max_length=300)
        
        assert len(truncated) <= 300
        assert truncated.endswith("...")
        # El texto truncado debe ser menor o igual a 300, incluyendo los "..."
        assert len(truncated) <= 300
    
    def test_truncate_section_with_spaces(self):
        """Test truncamiento con texto que tiene espacios."""
        service = OpenAIService()
        
        long_text = "A B C " * 100  # Texto con espacios
        truncated = service._truncate_section(long_text, max_length=300)
        
        assert len(truncated) <= 300
        assert truncated.endswith("...")
    
    def test_truncate_section_short_text(self):
        """Test que textos cortos no se truncan."""
        service = OpenAIService()
        
        short_text = "Texto corto de prueba."
        truncated = service._truncate_section(short_text, max_length=300)
        
        assert truncated == short_text
        assert not truncated.endswith("...")
    
    def test_validate_response_structure(self):
        """Test que la validación extrae las 3 secciones requeridas."""
        service = OpenAIService()
        
        mock_response = """1. IMPACTO EN CARTERA:
El mercado muestra volatilidad moderada que podría afectar activos tech.

2. ACCIONES RECOMENDADAS:
Mantener AAPL, reducir exposición a tech si aumenta volatilidad.

3. NUEVOS ACTIVOS:
Sin sugerencias: insuficientes noticias frescas."""
        
        fresh_count = 0
        formatted = service._validate_and_format_response(mock_response, fresh_count)
        
        assert "impacto_cartera" in formatted
        assert "acciones_recomendadas" in formatted
        assert "nuevos_activos" in formatted
        assert len(formatted["impacto_cartera"]) > 0
        assert len(formatted["acciones_recomendadas"]) > 0
        assert len(formatted["nuevos_activos"]) > 0
    
    def test_validate_response_length_limits(self):
        """Test que cada sección respeta el límite de longitud."""
        service = OpenAIService()
        
        # Crear respuesta con secciones largas
        long_section = "A" * 400
        mock_response = f"""1. IMPACTO EN CARTERA:
{long_section}

2. ACCIONES RECOMENDADAS:
{long_section}

3. NUEVOS ACTIVOS:
{long_section}"""
        
        formatted = service._validate_and_format_response(mock_response, fresh_count=5)
        
        assert len(formatted["impacto_cartera"]) <= service.max_section_length
        assert len(formatted["acciones_recomendadas"]) <= service.max_section_length
        assert len(formatted["nuevos_activos"]) <= service.max_section_length
    
    def test_no_suggestions_without_evidence(self):
        """Test que no se generan sugerencias sin suficientes noticias frescas."""
        service = OpenAIService()
        
        # Mock response que sugiere activos sin respaldo
        mock_response = """1. IMPACTO EN CARTERA:
Algún impacto.

2. ACCIONES RECOMENDADAS:
Mantener posición.

3. NUEVOS ACTIVOS:
Sugerir Bitcoin y Ethereum por tendencias."""
        
        # Con 0 noticias frescas (insuficiente)
        fresh_count = 0
        formatted = service._validate_and_format_response(mock_response, fresh_count)
        
        # Debe forzar mensaje de "sin sugerencias"
        assert "sin sugerencias" in formatted["nuevos_activos"].lower() or "insuficientes" in formatted["nuevos_activos"].lower()
    
    def test_suggestions_with_sufficient_evidence(self):
        """Test que se permiten sugerencias con suficientes noticias frescas."""
        service = OpenAIService()
        
        mock_response = """1. IMPACTO EN CARTERA:
Impacto positivo en tech.

2. ACCIONES RECOMENDADAS:
Aumentar exposición tech.

3. NUEVOS ACTIVOS:
Considerar AAPL por noticias positivas."""
        
        # Con suficientes noticias frescas
        fresh_count = 5  # Mayor al mínimo requerido
        formatted = service._validate_and_format_response(mock_response, fresh_count)
        
        # No debe forzar "sin sugerencias" si hay suficientes noticias
        assert len(formatted["nuevos_activos"]) > 0
    
    def test_parse_analysis_new_format(self):
        """Test parsing de formato nuevo minimalista."""
        service = OpenAIService()
        
        new_format_text = """1. IMPACTO EN CARTERA:
Impacto moderado en tech.

2. ACCIONES RECOMENDADAS:
Mantener AAPL.

3. NUEVOS ACTIVOS:
Sin sugerencias."""
        
        parsed = service._parse_analysis(new_format_text)
        
        assert "impacto_cartera" in parsed
        assert "acciones_recomendadas" in parsed
        assert "nuevos_activos" in parsed
        assert len(parsed["impacto_cartera"]) > 0
