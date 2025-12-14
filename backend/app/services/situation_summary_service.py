"""Servicio para generar resumen de situación actual basado en noticias."""
import logging
import json
from typing import List, Dict, Optional
from datetime import datetime, timezone
from app.config import (
    EXTRACTIVE_SUMMARY_MAX_SENTENCES,
    EXTRACTIVE_SUMMARY_MAX_CHARS_PER_NEWS,
    EXTRACTIVE_SUMMARY_MAX_CHARS_PER_BATCH,
    META_SUMMARY_MAX_SENTENCES,
    META_SUMMARY_MAX_CHARS
)
from app.models import NewsItemResponse
from app.services.extractive_summarizer import ExtractiveSummarizer
from app.services.meta_summary_service import MetaSummaryService

logger = logging.getLogger(__name__)

# Configuración de lotes
DEFAULT_BATCH_SIZE = 5  # Noticias por lote
MAX_NEWS_PER_BATCH = 10  # Máximo de noticias por lote


class SituationSummaryService:
    """Servicio para generar resumen conciso de la situación actual del mercado usando NLP local."""
    
    def __init__(self, use_extractive: bool = True):
        """
        Inicializa el servicio.
        
        Args:
            use_extractive: Si True, usa resumen extractivo (sin LLM). Si False, usa OpenAI (legacy).
        """
        self.use_extractive = use_extractive
        if use_extractive:
            self.extractive_summarizer = ExtractiveSummarizer()
            self.meta_summary_service = MetaSummaryService()
            logger.info("SituationSummaryService inicializado con resumen extractivo (sin LLM)")
        else:
            # Legacy: mantener compatibilidad con OpenAI si se necesita
            from openai import OpenAI
            from app.config import OPENAI_API_KEY, OPENAI_MODEL, OPENAI_TEMPERATURE
            from app.services.prompt_template_service import PromptTemplateService
            from app.services.prompt_cache_service import PromptCacheService
            
            if not OPENAI_API_KEY or OPENAI_API_KEY == "your_openai_api_key_here":
                raise ValueError("OPENAI_API_KEY no está configurada correctamente en app/config.py")
            
            self.client = OpenAI(api_key=OPENAI_API_KEY)
            self.model = OPENAI_MODEL
            self.temperature = OPENAI_TEMPERATURE
            self.template_service = PromptTemplateService()
            self.cache_service = PromptCacheService()
            logger.info("SituationSummaryService inicializado con OpenAI (legacy)")
    
    def generate_summary(
        self, 
        news_items: List[NewsItemResponse],
        batch_size: int = DEFAULT_BATCH_SIZE,
        use_batching: bool = True
    ) -> Dict:
        """
        Genera un resumen conciso de la situación actual basado en las noticias.
        Usa resumen extractivo por defecto (sin LLM).
        
        Args:
            news_items: Lista de noticias para analizar
            batch_size: Número de noticias por lote (default: 5)
            use_batching: Si True, procesa en lotes; si False, procesa todas juntas
            
        Returns:
            Dict con summary (meta-resumen), batch_summaries (resúmenes parciales) y metadata
        """
        if not news_items:
            empty_result = {
                "summary": "",
                "meta_summary": "",
                "batch_summaries": [],
                "news_count": 0,
                "recent_news_count": 0,
                "batches_processed": 0,
                "total_prompt_tokens": 0,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "has_content": False,
                "tokens_used": None,
                "estimated_tokens": 0,
                "method": "extractive" if self.use_extractive else "openai"
            }
            logger.info("No hay noticias para generar resumen")
            return empty_result
        
        # Usar resumen extractivo si está habilitado
        if self.use_extractive:
            return self._generate_extractive_summary(news_items, batch_size, use_batching)
        else:
            # Legacy: usar OpenAI
            return self._generate_openai_summary(news_items, batch_size, use_batching)
    
    def _generate_extractive_summary(
        self,
        news_items: List[NewsItemResponse],
        batch_size: int,
        use_batching: bool
    ) -> Dict:
        """Genera resumen usando método extractivo (sin LLM)."""
        # Ordenar noticias por fecha (más recientes primero)
        sorted_news = sorted(
            news_items,
            key=lambda x: x.created_at,
            reverse=True
        )
        
        # Limitar a las noticias más recientes
        max_news = 20
        recent_news = sorted_news[:max_news]
        
        batch_summaries = []
        total_chars = 0
        
        if use_batching and len(recent_news) > batch_size:
            # Procesar en lotes
            batches = [
                recent_news[i:i + batch_size] 
                for i in range(0, len(recent_news), batch_size)
            ]
            
            logger.info(
                f"[MOTOR LOCAL] Procesando {len(recent_news)} noticias en {len(batches)} lotes "
                f"(método extractivo, sin LLM, sin llamadas HTTP externas)"
            )
            
            for batch_idx, batch in enumerate(batches, 1):
                # Convertir a formato dict para el summarizer
                batch_dicts = []
                for item in batch:
                    batch_dicts.append({
                        "id": item.id,
                        "title": item.title,
                        "body": item.body or "",
                        "text": item.body or ""
                    })
                
                # Generar resúmenes extractivos para el lote
                summaries = self.extractive_summarizer.summarize_batch(
                    news_items=batch_dicts,
                    max_sentences_per_news=EXTRACTIVE_SUMMARY_MAX_SENTENCES,
                    max_chars_per_news=EXTRACTIVE_SUMMARY_MAX_CHARS_PER_NEWS,
                    max_total_chars=EXTRACTIVE_SUMMARY_MAX_CHARS_PER_BATCH
                )
                
                # Combinar resúmenes del lote
                batch_summary_text = " ".join([s["summary"] for s in summaries])
                batch_char_count = sum([s["char_count"] for s in summaries])
                
                batch_summaries.append({
                    "batch_number": batch_idx,
                    "news_count": len(batch),
                    "summary": batch_summary_text,
                    "tokens_used": None,  # Sin tokens (método local)
                    "char_count": batch_char_count,
                    "estimated_tokens": int(batch_char_count / 4)  # Estimación: ~4 chars por token
                })
                
                total_chars += batch_char_count
                logger.debug(f"Lote {batch_idx} procesado: {batch_char_count} chars")
            
            # Generar metarresumen
            if batch_summaries:
                meta_summary = self.meta_summary_service.generate_meta_summary(
                    batch_summaries=batch_summaries,
                    max_sentences=META_SUMMARY_MAX_SENTENCES,
                    max_chars=META_SUMMARY_MAX_CHARS,
                    deduplicate=True
                )
                
                # Si el metarresumen está vacío, usar el primer resumen de lote como fallback
                if not meta_summary or not meta_summary.strip():
                    logger.warning("[MOTOR LOCAL] Metarresumen vacío, usando primer resumen de lote como fallback")
                    for batch in batch_summaries:
                        batch_summary = batch.get("summary", "")
                        if batch_summary and not batch_summary.startswith("[Error"):
                            meta_summary = batch_summary[:META_SUMMARY_MAX_CHARS] if len(batch_summary) > META_SUMMARY_MAX_CHARS else batch_summary
                            break
                
                # Calcular tokens estimados (sin costos de API)
                estimated_tokens = int(total_chars / 4)  # Estimación conservadora
                
                logger.info(
                    f"[MOTOR LOCAL] Resumen extractivo completado: {len(batches)} lotes, "
                    f"{total_chars} chars totales, ~{estimated_tokens} tokens estimados "
                    f"(procesamiento local, sin llamadas HTTP externas)"
                )
                
                return {
                    "summary": meta_summary,
                    "meta_summary": meta_summary,
                    "batch_summaries": batch_summaries,
                    "news_count": len(news_items),
                    "recent_news_count": len(recent_news),
                    "batches_processed": len(batches),
                    "total_prompt_tokens": estimated_tokens,
                    "estimated_tokens": estimated_tokens,
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "has_content": bool(meta_summary),
                    "tokens_used": None,  # Sin tokens reales (método local)
                    "method": "extractive"
                }
            else:
                raise ValueError("No se pudieron procesar los lotes")
        else:
            # Procesar todas juntas (pocas noticias)
            logger.info(f"Procesando {len(recent_news)} noticias directamente (método extractivo)")
            
            news_dicts = []
            for item in recent_news:
                news_dicts.append({
                    "id": item.id,
                    "title": item.title,
                    "body": item.body or "",
                    "text": item.body or ""
                })
            
            summaries = self.extractive_summarizer.summarize_batch(
                news_items=news_dicts,
                max_sentences_per_news=EXTRACTIVE_SUMMARY_MAX_SENTENCES,
                max_chars_per_news=EXTRACTIVE_SUMMARY_MAX_CHARS_PER_NEWS
            )
            
            # Combinar resúmenes
            combined_summary = " ".join([s["summary"] for s in summaries])
            total_chars = sum([s["char_count"] for s in summaries])
            estimated_tokens = int(total_chars / 4)
            
            return {
                "summary": combined_summary,
                "meta_summary": combined_summary,
                "batch_summaries": [{
                    "batch_number": 1,
                    "news_count": len(recent_news),
                    "summary": combined_summary,
                    "tokens_used": None,
                    "char_count": total_chars,
                    "estimated_tokens": estimated_tokens
                }],
                "news_count": len(news_items),
                "recent_news_count": len(recent_news),
                "batches_processed": 1,
                "total_prompt_tokens": estimated_tokens,
                "estimated_tokens": estimated_tokens,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "has_content": bool(combined_summary),
                "tokens_used": None,
                "method": "extractive"
            }
    
    def _generate_openai_summary(
        self,
        news_items: List[NewsItemResponse],
        batch_size: int,
        use_batching: bool
    ) -> Dict:
        """Genera resumen usando OpenAI (método legacy)."""
        # Mantener implementación original para compatibilidad
        # Este método contiene el código original que usa OpenAI
        # Se mantiene para compatibilidad hacia atrás si se necesita
        try:
            sorted_news = sorted(news_items, key=lambda x: x.created_at, reverse=True)
            max_news = 20
            recent_news = sorted_news[:max_news]
            
            total_prompt_tokens = 0
            batch_summaries = []
            should_use_batching = use_batching and (len(recent_news) > batch_size or len(recent_news) > 10)
            
            if should_use_batching:
                batches = [recent_news[i:i + batch_size] for i in range(0, len(recent_news), batch_size)]
                
                for batch_idx, batch in enumerate(batches, 1):
                    batch_news_dicts = [self._news_item_to_dict(n) for n in batch]
                    prompt_data = self.template_service.build_optimized_prompt(
                        template_type="situation_summary",
                        variable_data={"news_items": batch_news_dicts, "batch_number": batch_idx, "total_batches": len(batches)}
                    )
                    
                    if not prompt_data.get("is_valid", True):
                        batch_summaries.append({
                            "batch_number": batch_idx,
                            "news_count": len(batch),
                            "summary": "[Error: Prompt excede límites]",
                            "tokens_used": 0
                        })
                        continue
                    
                    total_prompt_tokens += prompt_data["estimated_tokens"]
                    batch_summary = self._generate_batch_summary_optimized(batch, prompt_data, f"summary_batch_{batch_idx}")
                    batch_summaries.append({
                        "batch_number": batch_idx,
                        "news_count": len(batch),
                        "summary": batch_summary["summary"],
                        "tokens_used": batch_summary.get("tokens_used")
                    })
                
                if batch_summaries:
                    valid_batch_summaries = [b for b in batch_summaries if not b['summary'].startswith('[Error')]
                    if valid_batch_summaries:
                        meta_summary = self._generate_meta_summary(valid_batch_summaries)
                        total_tokens = sum(b.get("tokens_used", 0) for b in batch_summaries if b.get("tokens_used")) + meta_summary.get("tokens_used", 0)
                        return {
                            "summary": meta_summary["summary"],
                            "meta_summary": meta_summary["summary"],
                            "batch_summaries": batch_summaries,
                            "news_count": len(news_items),
                            "recent_news_count": len(recent_news),
                            "batches_processed": len(batches),
                            "total_prompt_tokens": int(total_prompt_tokens),
                            "estimated_tokens": int(total_prompt_tokens),
                            "generated_at": datetime.now(timezone.utc).isoformat(),
                            "has_content": bool(meta_summary["summary"]),
                            "tokens_used": total_tokens if total_tokens > 0 else None,
                            "method": "openai"
                        }
            
            # Procesamiento directo (legacy)
            news_dicts = [self._news_item_to_dict(n) for n in recent_news]
            prompt_data = self.template_service.build_optimized_prompt(
                template_type="situation_summary",
                variable_data={"news_items": news_dicts}
            )
            
            if not prompt_data.get("is_valid", True):
                return {
                    "summary": "[Error: Prompt excede límites]",
                    "meta_summary": "[Error: Prompt excede límites]",
                    "batch_summaries": [],
                    "news_count": len(news_items),
                    "recent_news_count": len(recent_news),
                    "batches_processed": 1,
                    "total_prompt_tokens": prompt_data["estimated_tokens"],
                    "estimated_tokens": prompt_data["estimated_tokens"],
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "has_content": False,
                    "tokens_used": 0,
                    "method": "openai"
                }
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": prompt_data["system_content"]},
                    {"role": "user", "content": prompt_data["user_content"]}
                ],
                temperature=self.temperature,
                max_tokens=500,
                timeout=60.0
            )
            
            summary_text = response.choices[0].message.content.strip()
            tokens_used = response.usage.total_tokens if response.usage else None
            
            return {
                "summary": summary_text,
                "meta_summary": summary_text,
                "batch_summaries": [],
                "news_count": len(news_items),
                "recent_news_count": len(recent_news),
                "batches_processed": 1,
                "total_prompt_tokens": prompt_data["estimated_tokens"],
                "estimated_tokens": prompt_data["estimated_tokens"],
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "has_content": True,
                "tokens_used": tokens_used,
                "method": "openai"
            }
        except Exception as e:
            logger.error(f"Error en generación OpenAI (legacy): {e}", exc_info=True)
            raise
        
        try:
            # Ordenar noticias por fecha (más recientes primero)
            sorted_news = sorted(
                news_items,
                key=lambda x: x.created_at,
                reverse=True
            )
            
            # Limitar a las noticias más recientes para evitar procesar demasiadas
            max_news = 20  # Máximo de noticias a considerar
            recent_news = sorted_news[:max_news]
            
            total_prompt_tokens = 0
            batch_summaries = []
            
            # Usar batching si está habilitado Y hay más noticias que el tamaño del lote
            # O si hay muchas noticias (más de 10) para evitar exceder límites de tokens
            should_use_batching = use_batching and (len(recent_news) > batch_size or len(recent_news) > 10)
            
            if should_use_batching:
                # Procesar en lotes
                logger.info(
                    f"Procesando {len(recent_news)} noticias en lotes de {batch_size}. "
                    f"Total de lotes estimados: {(len(recent_news) + batch_size - 1) // batch_size}"
                )
                
                # Dividir en lotes
                batches = [
                    recent_news[i:i + batch_size] 
                    for i in range(0, len(recent_news), batch_size)
                ]
                
                # Procesar cada lote
                for batch_idx, batch in enumerate(batches, 1):
                    logger.info(f"Procesando lote {batch_idx}/{len(batches)} con {len(batch)} noticias")
                    
                    # Construir prompt optimizado usando plantillas
                    batch_news_dicts = [self._news_item_to_dict(n) for n in batch]
                    prompt_data = self.template_service.build_optimized_prompt(
                        template_type="situation_summary",
                        variable_data={
                            "news_items": batch_news_dicts,
                            "batch_number": batch_idx,
                            "total_batches": len(batches)
                        }
                    )
                    
                    # Condición de salida explícita: verificar si el prompt es válido
                    if not prompt_data.get("is_valid", True):
                        logger.warning(
                            f"Lote {batch_idx}: Prompt inválido ({prompt_data.get('char_count', 0)} chars, "
                            f"{prompt_data.get('estimated_tokens', 0)} tokens). Saltando llamada a OpenAI."
                        )
                        batch_summaries.append({
                            "batch_number": batch_idx,
                            "news_count": len(batch),
                            "summary": f"[Error: Prompt excede límites de tokens]",
                            "tokens_used": 0
                        })
                        continue
                    
                    total_prompt_tokens += prompt_data["estimated_tokens"]
                    
                    try:
                        batch_summary = self._generate_batch_summary_optimized(
                            batch, 
                            prompt_data,
                            step_name=f"summary_batch_{batch_idx}"
                        )
                        batch_summaries.append({
                            "batch_number": batch_idx,
                            "news_count": len(batch),
                            "summary": batch_summary["summary"],
                            "tokens_used": batch_summary.get("tokens_used")
                        })
                        logger.info(f"Lote {batch_idx} procesado exitosamente. Tokens: {batch_summary.get('tokens_used', 'N/A')}")
                    except Exception as e:
                        logger.error(f"Error procesando lote {batch_idx}: {e}")
                        # Continuar con el siguiente lote
                        batch_summaries.append({
                            "batch_number": batch_idx,
                            "news_count": len(batch),
                            "summary": f"[Error al procesar lote {batch_idx}]",
                            "tokens_used": None
                        })
                
                # Generar meta-resumen a partir de los resúmenes parciales
                if batch_summaries:
                    # Filtrar lotes con errores antes de generar meta-resumen
                    valid_batch_summaries = [b for b in batch_summaries if not b['summary'].startswith('[Error')]
                    
                    if valid_batch_summaries:
                        meta_summary = self._generate_meta_summary(valid_batch_summaries)
                        meta_tokens = meta_summary.get("tokens_used", 0)
                        total_tokens = sum(b.get("tokens_used", 0) for b in batch_summaries if b.get("tokens_used")) + meta_tokens
                        
                        # Agregar tokens del meta-resumen a la estimación total
                        meta_prompt_estimate = len(valid_batch_summaries) * 200  # Estimación para prompt de meta-resumen
                        total_prompt_tokens += meta_prompt_estimate
                        
                        logger.info(
                            f"Resumen completado: {len(batches)} lotes procesados ({len(valid_batch_summaries)} válidos), "
                            f"~{int(total_prompt_tokens)} tokens de prompt estimados, "
                            f"{total_tokens} tokens totales usados"
                        )
                    else:
                        # Si todos los lotes fallaron, usar el primer resumen disponible o error
                        logger.warning("Todos los lotes fallaron, usando resumen de fallback")
                        fallback_summary = batch_summaries[0]['summary'] if batch_summaries and batch_summaries[0].get('summary') else "Error al procesar noticias"
                        meta_summary = {
                            "summary": fallback_summary,
                            "tokens_used": 0
                        }
                        total_tokens = sum(b.get("tokens_used", 0) for b in batch_summaries if b.get("tokens_used"))
                    
                    return {
                        "summary": meta_summary["summary"],  # Mantener compatibilidad
                        "meta_summary": meta_summary["summary"],
                        "batch_summaries": batch_summaries,
                        "news_count": len(news_items),
                        "recent_news_count": len(recent_news),
                        "batches_processed": len(batches),
                        "total_prompt_tokens": int(total_prompt_tokens),
                        "generated_at": datetime.now(timezone.utc).isoformat(),
                        "has_content": bool(meta_summary["summary"] and meta_summary["summary"] != "Error al procesar noticias"),
                        "tokens_used": total_tokens if total_tokens > 0 else None
                    }
                else:
                    raise ValueError("No se pudieron procesar los lotes")
            else:
                # Procesamiento directo (legacy o pocas noticias)
                logger.info(f"Procesando {len(recent_news)} noticias directamente (sin lotes)")
                
                # Construir prompt optimizado
                news_dicts = [self._news_item_to_dict(n) for n in recent_news]
                prompt_data = self.template_service.build_optimized_prompt(
                    template_type="situation_summary",
                    variable_data={"news_items": news_dicts}
                )
                
                # Verificar caché (solo para contexto estático, no para datos dinámicos)
                static_data = {"context": "situation_summary_direct"}
                cached_response = self.cache_service.get(
                    prompt_type="situation_summary",
                    static_data=static_data,
                    variable_data={"news_count": len(recent_news)},
                    cache_ttl=CACHE_TTL["summary"]
                )
                
                if cached_response:
                    logger.info(f"Usando respuesta cacheada para resumen directo")
                    return cached_response
                
                # Verificar condición de salida: si el prompt es inválido, no llamar a OpenAI
                if not prompt_data.get("is_valid", True):
                    logger.warning("Prompt inválido para resumen directo, saltando llamada a OpenAI")
                    return {
                        "summary": "[Error: Prompt excede límites de tokens]",
                        "meta_summary": "[Error: Prompt excede límites de tokens]",
                        "batch_summaries": [],
                        "news_count": len(news_items),
                        "recent_news_count": len(recent_news),
                        "batches_processed": 1,
                        "total_prompt_tokens": prompt_data["estimated_tokens"],
                        "generated_at": datetime.now(timezone.utc).isoformat(),
                        "has_content": False,
                        "tokens_used": 0
                    }
                
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": prompt_data["system_content"]
                        },
                        {
                            "role": "user",
                            "content": prompt_data["user_content"]
                        }
                    ],
                    temperature=self.temperature,
                    max_tokens=500,
                    timeout=60.0
                )
                
                summary_text = response.choices[0].message.content.strip()
                tokens_used = response.usage.total_tokens if response.usage else None
                
                # Log de tokens
                if response.usage:
                    token_logger.log_usage(
                        prompt_tokens=response.usage.prompt_tokens,
                        completion_tokens=response.usage.completion_tokens,
                        step_name="situation_summary_direct",
                        prompt_type="situation_summary",
                        response=response
                    )
                
                result = {
                    "summary": summary_text,
                    "meta_summary": summary_text,
                    "batch_summaries": [],
                    "news_count": len(news_items),
                    "recent_news_count": len(recent_news),
                    "batches_processed": 1,
                    "total_prompt_tokens": prompt_data["estimated_tokens"],
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "has_content": True,
                    "tokens_used": tokens_used
                }
                
                # Cachear respuesta (solo si tiene contenido válido)
                if result["has_content"]:
                    self.cache_service.set(
                        prompt_type="situation_summary",
                        static_data=static_data,
                        response=result,
                        variable_data={"news_count": len(recent_news)},
                        token_count=tokens_used,
                        cache_ttl=CACHE_TTL["summary"]
                    )
                
                logger.info(
                    f"Resumen directo generado: {len(recent_news)} noticias, "
                    f"{prompt_data['estimated_tokens']} tokens de prompt estimados, "
                    f"{tokens_used or 'N/A'} tokens totales usados"
                )
                
                return result
            
        except Exception as e:
            logger.error(f"Error generando resumen de situación: {e}", exc_info=True)
            raise ValueError(f"Error al generar resumen: {str(e)}")
    
    def _build_summary_prompt(
        self, 
        news_items: List[NewsItemResponse],
        batch_number: Optional[int] = None,
        total_batches: Optional[int] = None
    ) -> str:
        """Construye el prompt para generar el resumen."""
        prompt_parts = [
            "Resumen de Noticias del Mercado",
            "=" * 60,
            f"Fecha de análisis: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}",
            f"Total de noticias en este lote: {len(news_items)}",
        ]
        
        if batch_number and total_batches:
            prompt_parts.append(f"Lote {batch_number} de {total_batches}")
        
        prompt_parts.extend([
            "",
            "INSTRUCCIONES:",
            "Genera un resumen conciso (2-4 párrafos) de la situación actual del mercado basado en las siguientes noticias.",
            "Enfócate en:",
            "- Tendencias principales identificadas",
            "- Eventos o desarrollos clave",
            "- Contexto general del mercado",
            "",
            "Sé objetivo, claro y directo. Evita especulación sin respaldo.",
            "",
            "=" * 60,
            "",
            "NOTICIAS:",
            ""
        ])
        
        for idx, item in enumerate(news_items, 1):
            prompt_parts.append(f"{idx}. {item.title or 'Sin título'}")
            if item.source:
                prompt_parts.append(f"   Fuente: {item.source}")
            prompt_parts.append(f"   Fecha: {item.created_at}")
            # Limitar caracteres para evitar exceder tokens
            content_preview = item.body[:MAX_CHARS_PER_NEWS]
            if len(item.body) > MAX_CHARS_PER_NEWS:
                content_preview += "..."
            prompt_parts.append(f"   Contenido: {content_preview}")
            prompt_parts.append("")
        
        prompt_parts.append("=" * 60)
        prompt_parts.append("")
        prompt_parts.append("Genera el resumen de situación actual:")
        
        return "\n".join(prompt_parts)
    
    def _news_item_to_dict(self, news_item: NewsItemResponse) -> Dict:
        """Convierte NewsItemResponse a diccionario para plantillas."""
        # Manejar standardized_data que puede ser None o un modelo Pydantic
        standardized_data = None
        if news_item.standardized_data is not None:
            if hasattr(news_item.standardized_data, 'model_dump'):
                standardized_data = news_item.standardized_data.model_dump()
            elif isinstance(news_item.standardized_data, dict):
                standardized_data = news_item.standardized_data
            else:
                # Si es un string JSON, intentar parsearlo
                try:
                    import json
                    if isinstance(news_item.standardized_data, str):
                        standardized_data = json.loads(news_item.standardized_data)
                    else:
                        standardized_data = {}
                except:
                    standardized_data = {}
        
        return {
            "id": news_item.id,
            "title": news_item.title,
            "body": news_item.body,
            "source": news_item.source,
            "created_at": news_item.created_at,
            "standardized_data": standardized_data  # Puede ser None o dict
        }
    
    def _generate_batch_summary_optimized(
        self, 
        batch: List[NewsItemResponse], 
        prompt_data: Dict,
        step_name: str
    ) -> Dict:
        """Genera un resumen para un lote usando prompts optimizados."""
        # Verificar condición de salida: si el prompt es inválido, no llamar a OpenAI
        if not prompt_data.get("is_valid", True):
            logger.warning(f"Prompt inválido para {step_name}, saltando llamada a OpenAI")
            return {
                "summary": "[Error: Prompt excede límites de tokens]",
                "tokens_used": 0
            }
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": prompt_data["system_content"]
                },
                {
                    "role": "user",
                    "content": prompt_data["user_content"]
                }
            ],
            temperature=self.temperature,
            max_tokens=400,  # Resumen más corto para lotes
            timeout=60.0
        )
        
        summary_text = response.choices[0].message.content.strip()
        tokens_used = response.usage.total_tokens if response.usage else None
        
        # Log de tokens
        if response.usage:
            token_logger.log_usage(
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
                step_name=step_name,
                prompt_type="situation_summary",
                response=response
            )
        
        return {
            "summary": summary_text,
            "tokens_used": tokens_used
        }
    
    def _generate_batch_summary(self, batch: List[NewsItemResponse], prompt: str) -> Dict:
        """Genera un resumen para un lote específico de noticias (método legacy)."""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Eres un analista financiero experto. Tu tarea es generar un resumen conciso "
                        "y claro de la situación actual del mercado basado en las noticias proporcionadas. "
                        "El resumen debe ser breve (2-3 párrafos máximo), directo y enfocado en los puntos clave. "
                        "Evita jerga técnica innecesaria. Sé objetivo y basado en hechos."
                    )
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=self.temperature,
            max_tokens=400,  # Resumen más corto para lotes
            timeout=60.0
        )
        
        summary_text = response.choices[0].message.content.strip()
        tokens_used = response.usage.total_tokens if hasattr(response, 'usage') else None
        
        return {
            "summary": summary_text,
            "tokens_used": tokens_used
        }
    
    def _generate_meta_summary(self, batch_summaries: List[Dict]) -> Dict:
        """Genera un meta-resumen a partir de los resúmenes parciales de los lotes."""
        if not batch_summaries:
            return {
                "summary": "",
                "tokens_used": 0
            }
        
        # Construir prompt con los resúmenes parciales
        prompt_parts = [
            "Meta-Resumen de Situación del Mercado",
            "=" * 60,
            f"Fecha de análisis: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}",
            f"Total de lotes procesados: {len(batch_summaries)}",
            "",
            "INSTRUCCIONES:",
            "Genera un resumen ejecutivo consolidado (2-4 párrafos) que sintetice la situación actual del mercado "
            "basado en los siguientes resúmenes parciales de diferentes lotes de noticias.",
            "",
            "El meta-resumen debe:",
            "- Integrar los puntos clave de todos los lotes",
            "- Identificar tendencias y patrones comunes",
            "- Proporcionar una visión general coherente y concisa",
            "- Evitar redundancias entre lotes",
            "",
            "Sé objetivo, claro y directo.",
            "",
            "=" * 60,
            "",
            "RESÚMENES PARCIALES:",
            ""
        ]
        
        for batch_summary in batch_summaries:
            prompt_parts.append(f"Lote {batch_summary['batch_number']} ({batch_summary['news_count']} noticias):")
            prompt_parts.append(batch_summary['summary'])
            prompt_parts.append("")
        
        prompt_parts.append("=" * 60)
        prompt_parts.append("")
        prompt_parts.append("Genera el meta-resumen ejecutivo consolidado:")
        
        prompt = "\n".join(prompt_parts)
        
        logger.info(f"Generando meta-resumen desde {len(batch_summaries)} resúmenes parciales")
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Eres un analista financiero senior. Tu tarea es generar un meta-resumen ejecutivo "
                        "que consolide múltiples resúmenes parciales de noticias en una visión general coherente. "
                        "El meta-resumen debe ser conciso (2-4 párrafos), identificar tendencias principales, "
                        "y proporcionar una síntesis clara de la situación actual del mercado."
                    )
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=self.temperature,
            max_tokens=600,  # Un poco más largo para el meta-resumen
            timeout=60.0
        )
        
        meta_summary_text = response.choices[0].message.content.strip()
        tokens_used = response.usage.total_tokens if response.usage else None
        
        # Log de tokens
        if response.usage:
            token_logger.log_usage(
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
                step_name="meta_summary",
                prompt_type="situation_summary",
                response=response
            )
        
        return {
            "summary": meta_summary_text,
            "tokens_used": tokens_used
        }



