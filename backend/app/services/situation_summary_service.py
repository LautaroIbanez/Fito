"""Servicio para generar resumen de situación actual basado en noticias."""
import logging
import json
from typing import List, Dict
from datetime import datetime, timezone
from openai import OpenAI
from app.config import (
    OPENAI_API_KEY,
    OPENAI_MODEL,
    OPENAI_TEMPERATURE
)
from app.models import NewsItemResponse

logger = logging.getLogger(__name__)


class SituationSummaryService:
    """Servicio para generar resumen conciso de la situación actual del mercado."""
    
    def __init__(self):
        """Inicializa el cliente de OpenAI."""
        if not OPENAI_API_KEY or OPENAI_API_KEY == "your_openai_api_key_here":
            raise ValueError("OPENAI_API_KEY no está configurada correctamente en app/config.py")
        
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        self.model = OPENAI_MODEL
        self.temperature = OPENAI_TEMPERATURE
    
    def generate_summary(self, news_items: List[NewsItemResponse]) -> Dict:
        """
        Genera un resumen conciso de la situación actual basado en las noticias.
        
        Args:
            news_items: Lista de noticias para analizar
            
        Returns:
            Dict con summary (texto del resumen) y metadata
        """
        if not news_items:
            return {
                "summary": "",
                "news_count": 0,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "has_content": False
            }
        
        try:
            # Ordenar noticias por fecha (más recientes primero)
            sorted_news = sorted(
                news_items,
                key=lambda x: x.created_at,
                reverse=True
            )
            
            # Tomar las noticias más recientes (últimas 10)
            recent_news = sorted_news[:10]
            
            # Construir prompt
            prompt = self._build_summary_prompt(recent_news)
            
            logger.info(f"Generando resumen de situación actual para {len(recent_news)} noticias recientes")
            
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
                max_tokens=500,  # Resumen corto
                timeout=60.0
            )
            
            summary_text = response.choices[0].message.content.strip()
            
            return {
                "summary": summary_text,
                "news_count": len(news_items),
                "recent_news_count": len(recent_news),
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "has_content": True,
                "tokens_used": response.usage.total_tokens if hasattr(response, 'usage') else None
            }
            
        except Exception as e:
            logger.error(f"Error generando resumen de situación: {e}", exc_info=True)
            raise ValueError(f"Error al generar resumen: {str(e)}")
    
    def _build_summary_prompt(self, news_items: List[NewsItemResponse]) -> str:
        """Construye el prompt para generar el resumen."""
        prompt_parts = [
            "Resumen de Noticias del Mercado",
            "=" * 60,
            f"Fecha de análisis: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}",
            f"Total de noticias analizadas: {len(news_items)}",
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
        ]
        
        for idx, item in enumerate(news_items, 1):
            prompt_parts.append(f"{idx}. {item.title or 'Sin título'}")
            if item.source:
                prompt_parts.append(f"   Fuente: {item.source}")
            prompt_parts.append(f"   Fecha: {item.created_at}")
            prompt_parts.append(f"   Contenido: {item.body[:500]}...")  # Primeros 500 caracteres
            prompt_parts.append("")
        
        prompt_parts.append("=" * 60)
        prompt_parts.append("")
        prompt_parts.append("Genera el resumen de situación actual:")
        
        return "\n".join(prompt_parts)

