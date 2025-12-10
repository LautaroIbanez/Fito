"""Servicio para empaquetar prompts de forma concisa respetando límites de tokens/palabras."""
import logging
from typing import List, Dict, Tuple
from app.config import (
    PROMPT_PACKAGING_MAX_TOKENS,
    PROMPT_PACKAGING_MAX_WORDS_PER_ITEM,
    PROMPT_PACKAGING_FALLBACK_ENABLED,
    PROMPT_PACKAGING_ESTIMATE_TOKENS_PER_WORD
)

logger = logging.getLogger(__name__)


class PromptPackagingService:
    """Servicio para empaquetar prompts respetando límites de tokens/palabras."""
    
    def __init__(self):
        """Inicializa el servicio de empaquetado."""
        self.max_tokens = PROMPT_PACKAGING_MAX_TOKENS
        self.max_words_per_item = PROMPT_PACKAGING_MAX_WORDS_PER_ITEM
        self.fallback_enabled = PROMPT_PACKAGING_FALLBACK_ENABLED
        self.tokens_per_word = PROMPT_PACKAGING_ESTIMATE_TOKENS_PER_WORD
    
    def package_standardized_news(
        self,
        standardized_news_items: List[Dict],
        base_prompt_template: str = "",
        portfolio_context: str = ""
    ) -> Tuple[str, Dict]:
        """
        Empaqueta noticias estandarizadas respetando el presupuesto de tokens.
        
        Args:
            standardized_news_items: Lista de diccionarios con datos estandarizados
            base_prompt_template: Template base del prompt (instrucciones, etc.)
            portfolio_context: Contexto de cartera (opcional)
            
        Returns:
            Tuple[str, Dict]: (prompt_empaquetado, metadata)
            metadata incluye: total_tokens_estimate, items_included, items_truncated, 
                             items_fallback, word_count_per_item
        """
        metadata = {
            "total_tokens_estimate": 0,
            "items_included": 0,
            "items_truncated": 0,
            "items_fallback": 0,
            "word_count_per_item": []
        }
        
        # Calcular presupuesto disponible para noticias
        base_tokens = self._estimate_tokens(base_prompt_template)
        portfolio_tokens = self._estimate_tokens(portfolio_context)
        reserved_tokens = base_tokens + portfolio_tokens + 500  # 500 tokens de margen para estructura
        
        available_tokens = max(0, self.max_tokens - reserved_tokens)
        available_words = int(available_tokens / self.tokens_per_word)
        
        logger.info(f"Presupuesto disponible: ~{available_tokens} tokens (~{available_words} palabras) para {len(standardized_news_items)} noticias")
        
        # Empaquetar noticias
        packaged_items = []
        total_words_used = 0
        
        for idx, news_item in enumerate(standardized_news_items):
            news_id = news_item.get('id', idx + 1)
            standardized = news_item.get('standardized_data', {})
            
            if isinstance(standardized, str):
                import json
                try:
                    standardized = json.loads(standardized)
                except json.JSONDecodeError:
                    standardized = {}
            
            # Intentar empaquetar con formato completo primero
            formatted_item, item_words, used_fallback = self._format_news_item(
                news_id,
                standardized,
                news_item.get('title'),
                available_words - total_words_used,
                len(standardized_news_items) - idx  # Items restantes
            )
            item_tokens = int(item_words * self.tokens_per_word)
            
            # Verificar si cabe en el presupuesto
            if total_words_used + item_words <= available_words:
                packaged_items.append(formatted_item)
                total_words_used += item_words
                metadata["items_included"] += 1
                if used_fallback:
                    metadata["items_fallback"] += 1
                else:
                    metadata["items_truncated"] += 1 if item_words >= self.max_words_per_item * 0.9 else 0
                metadata["word_count_per_item"].append({
                    "news_id": news_id,
                    "words": item_words,
                    "tokens_estimate": item_tokens,
                    "fallback": used_fallback
                })
            else:
                # No cabe, usar fallback mínimo si está habilitado
                if self.fallback_enabled:
                    fallback_item = self._create_fallback_item(news_id, standardized, news_item.get('title'))
                    fallback_words = self._count_words(fallback_item)
                    
                    if total_words_used + fallback_words <= available_words:
                        packaged_items.append(fallback_item)
                        total_words_used += fallback_words
                        metadata["items_included"] += 1
                        metadata["items_fallback"] += 1
                        metadata["word_count_per_item"].append({
                            "news_id": news_id,
                            "words": fallback_words,
                            "tokens_estimate": int(fallback_words * self.tokens_per_word),
                            "fallback": True
                        })
                    else:
                        logger.warning(f"Noticia {news_id} no cabe ni en modo fallback, omitiendo")
                        break
                else:
                    logger.warning(f"Noticia {news_id} excede presupuesto y fallback deshabilitado, omitiendo")
                    break
        
        # Construir prompt final
        prompt_parts = []
        
        if base_prompt_template:
            prompt_parts.append(base_prompt_template)
            prompt_parts.append("\n")
        
        if portfolio_context:
            prompt_parts.append(portfolio_context)
            prompt_parts.append("\n")
        
        if packaged_items:
            prompt_parts.append("NOTICIAS ESTANDARIZADAS PARA ANÁLISIS:\n")
            prompt_parts.append("=" * 60 + "\n")
            for item in packaged_items:
                prompt_parts.append(item)
                prompt_parts.append("")
        
        final_prompt = "\n".join(prompt_parts)
        
        # Calcular tokens totales estimados
        metadata["total_tokens_estimate"] = self._estimate_tokens(final_prompt)
        
        logger.info(
            f"Prompt empaquetado: {metadata['items_included']} items incluidos, "
            f"{metadata['items_fallback']} en fallback, "
            f"~{metadata['total_tokens_estimate']} tokens estimados"
        )
        
        return final_prompt, metadata
    
    def _format_news_item(
        self,
        news_id: int,
        standardized: Dict,
        fallback_title: str = None,
        available_words: int = None,
        remaining_items: int = 1
    ) -> Tuple[str, int, bool]:
        """
        Formatea un item de noticia respetando límites de palabras.
        
        Returns:
            Tuple[str, int, bool]: (formatted_text, word_count, used_fallback)
        """
        if available_words is None:
            available_words = self.max_words_per_item
        
        # Calcular presupuesto por item
        words_per_item = min(
            self.max_words_per_item,
            available_words // max(remaining_items, 1) if remaining_items > 0 else self.max_words_per_item
        )
        
        # Si el presupuesto es muy bajo, usar fallback
        if words_per_item < 30 and self.fallback_enabled:
            fallback_item = self._create_fallback_item(news_id, standardized, fallback_title)
            fallback_word_count = self._count_words(fallback_item)
            return fallback_item, fallback_word_count, True
        
        parts = []
        word_count = 0
        used_fallback = False
        
        # Título (siempre incluido)
        title = standardized.get('title', fallback_title or 'N/A')
        parts.append(f"\nNOTICIA (ID: {news_id}):")
        parts.append(f"Título: {title}")
        word_count += self._count_words(f"Título: {title}")
        
        # Campos esenciales primero
        essential_fields = []
        
        if standardized.get('sentiment'):
            essential_fields.append(f"Sentimiento: {standardized.get('sentiment')}")
        
        if standardized.get('why_it_matters'):
            why_matters = standardized.get('why_it_matters')
            # Truncar si es necesario
            if self._count_words(why_matters) > 30:
                words = why_matters.split()[:30]
                why_matters = " ".join(words) + "..."
            essential_fields.append(f"Por qué importa: {why_matters}")
        
        # Agregar campos esenciales
        for field in essential_fields:
            field_words = self._count_words(field)
            if word_count + field_words <= words_per_item:
                parts.append(field)
                word_count += field_words
            else:
                break
        
        # Campos opcionales (si hay espacio)
        optional_budget = words_per_item - word_count
        
        if optional_budget > 20:
            # Fecha y fuente (breves)
            if standardized.get('publication_date'):
                date_field = f"Fecha: {standardized.get('publication_date')}"
                if self._count_words(date_field) <= optional_budget:
                    parts.append(date_field)
                    word_count += self._count_words(date_field)
                    optional_budget -= self._count_words(date_field)
            
            if standardized.get('source'):
                source_field = f"Fuente: {standardized.get('source')}"
                if self._count_words(source_field) <= optional_budget:
                    parts.append(source_field)
                    word_count += self._count_words(source_field)
                    optional_budget -= self._count_words(source_field)
        
        # Bullets de resumen (si hay espacio)
        if optional_budget > 30 and standardized.get('summary_bullets'):
            bullets = standardized.get('summary_bullets', [])
            parts.append("Resumen:")
            word_count += 1  # "Resumen:"
            
            bullets_added = 0
            for bullet in bullets:
                bullet_text = f"  • {bullet}"
                bullet_words = self._count_words(bullet_text)
                
                # Truncar bullet si es muy largo
                if bullet_words > 25:
                    words = bullet.split()[:20]
                    bullet_text = f"  • {' '.join(words)}..."
                    bullet_words = self._count_words(bullet_text)
                
                if word_count + bullet_words <= words_per_item:
                    parts.append(bullet_text)
                    word_count += bullet_words
                    bullets_added += 1
                else:
                    break
            
            if bullets_added == 0:
                # Si no cabió ningún bullet, remover "Resumen:"
                parts.pop()
                word_count -= 1
        
        # Personas/empresas clave (muy breve)
        if optional_budget > 15 and standardized.get('key_people_companies'):
            people = standardized.get('key_people_companies', [])[:3]  # Máximo 3
            people_text = f"Personas/Empresas clave: {', '.join(people)}"
            if self._count_words(people_text) <= optional_budget:
                parts.append(people_text)
                word_count += self._count_words(people_text)
        
        # Métricas (muy breve)
        if optional_budget > 15 and standardized.get('quoted_numbers_metrics'):
            metrics = standardized.get('quoted_numbers_metrics', [])[:3]  # Máximo 3
            metrics_text = f"Métricas citadas: {', '.join(metrics)}"
            if self._count_words(metrics_text) <= optional_budget:
                parts.append(metrics_text)
                word_count += self._count_words(metrics_text)
        
        formatted_text = "\n".join(parts)
        return formatted_text, word_count, used_fallback
    
    def _create_fallback_item(
        self,
        news_id: int,
        standardized: Dict,
        fallback_title: str = None
    ) -> str:
        """
        Crea un item de noticia en modo fallback (mínimo: título + why_it_matters + sentiment).
        """
        title = standardized.get('title', fallback_title or 'N/A')
        sentiment = standardized.get('sentiment', 'N/A')
        why_matters = standardized.get('why_it_matters', 'N/A')
        
        # Truncar why_it_matters a una línea
        if why_matters and len(why_matters) > 100:
            why_matters = why_matters[:97] + "..."
        
        parts = [
            f"\nNOTICIA (ID: {news_id}):",
            f"Título: {title}",
            f"Sentimiento: {sentiment}",
            f"Por qué importa: {why_matters}"
        ]
        
        return "\n".join(parts)
    
    def _count_words(self, text: str) -> int:
        """Cuenta palabras en un texto."""
        if not text:
            return 0
        return len(text.split())
    
    def _estimate_tokens(self, text: str) -> int:
        """Estima tokens en un texto."""
        if not text:
            return 0
        words = self._count_words(text)
        return int(words * self.tokens_per_word)

