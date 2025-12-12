"""Servicio para generar resumen de situación actual basado en noticias."""
import logging
import json
from typing import List, Dict, Optional
from datetime import datetime, timezone
from openai import OpenAI
from app.config import (
    OPENAI_API_KEY,
    OPENAI_MODEL,
    OPENAI_TEMPERATURE
)
from app.models import NewsItemResponse

logger = logging.getLogger(__name__)

# Configuración de lotes
DEFAULT_BATCH_SIZE = 5  # Noticias por lote
MAX_NEWS_PER_BATCH = 10  # Máximo de noticias por lote
MAX_CHARS_PER_NEWS = 500  # Máximo de caracteres por noticia en el prompt


class SituationSummaryService:
    """Servicio para generar resumen conciso de la situación actual del mercado."""
    
    def __init__(self):
        """Inicializa el cliente de OpenAI."""
        if not OPENAI_API_KEY or OPENAI_API_KEY == "your_openai_api_key_here":
            raise ValueError("OPENAI_API_KEY no está configurada correctamente en app/config.py")
        
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        self.model = OPENAI_MODEL
        self.temperature = OPENAI_TEMPERATURE
    
    def generate_summary(
        self, 
        news_items: List[NewsItemResponse],
        batch_size: int = DEFAULT_BATCH_SIZE,
        use_batching: bool = True
    ) -> Dict:
        """
        Genera un resumen conciso de la situación actual basado en las noticias.
        Procesa las noticias en lotes para evitar exceder límites de tokens.
        
        Args:
            news_items: Lista de noticias para analizar
            batch_size: Número de noticias por lote (default: 5)
            use_batching: Si True, procesa en lotes; si False, procesa todas juntas (legacy)
            
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
                "tokens_used": None
            }
            logger.info("No hay noticias para generar resumen")
            return empty_result
        
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
                    
                    batch_prompt = self._build_summary_prompt(batch, batch_number=batch_idx, total_batches=len(batches))
                    prompt_tokens = len(batch_prompt.split()) * 1.3  # Estimación aproximada
                    total_prompt_tokens += int(prompt_tokens)
                    
                    try:
                        batch_summary = self._generate_batch_summary(batch, batch_prompt)
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
                prompt = self._build_summary_prompt(recent_news)
                # Estimación más precisa con overhead del sistema
                prompt_words = len(prompt.split())
                prompt_tokens = int(prompt_words * 1.3) + 100  # +100 para overhead del sistema
                
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "Eres un analista financiero experto. Tu tarea es generar un resumen conciso "
                                "y claro de la situación actual del mercado basado en las noticias proporcionadas. "
                                "El resumen debe ser breve (2-4 párrafos máximo), directo y enfocado en los puntos clave. "
                                "Evita jerga técnica innecesaria. Sé objetivo y basado en hechos."
                            )
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    temperature=self.temperature,
                    max_tokens=500,
                    timeout=60.0
                )
                
                summary_text = response.choices[0].message.content.strip()
                tokens_used = response.usage.total_tokens if hasattr(response, 'usage') else None
                
                logger.info(
                    f"Resumen directo generado: {len(recent_news)} noticias, "
                    f"~{int(prompt_tokens)} tokens de prompt estimados, "
                    f"{tokens_used or 'N/A'} tokens totales usados"
                )
                
                return {
                    "summary": summary_text,
                    "meta_summary": summary_text,
                    "batch_summaries": [],
                    "news_count": len(news_items),
                    "recent_news_count": len(recent_news),
                    "batches_processed": 1,
                    "total_prompt_tokens": int(prompt_tokens),
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "has_content": True,
                    "tokens_used": tokens_used
                }
            
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
    
    def _generate_batch_summary(self, batch: List[NewsItemResponse], prompt: str) -> Dict:
        """Genera un resumen para un lote específico de noticias."""
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
        tokens_used = response.usage.total_tokens if hasattr(response, 'usage') else None
        
        return {
            "summary": meta_summary_text,
            "tokens_used": tokens_used
        }



