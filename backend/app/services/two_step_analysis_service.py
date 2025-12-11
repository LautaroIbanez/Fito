"""Servicio de análisis de noticias en dos pasos: normalización y análisis de inversor."""
import logging
import json
from typing import Dict, List, Optional
from datetime import datetime, timezone
from openai import OpenAI

from app.config import OPENAI_API_KEY, OPENAI_MODEL, OPENAI_TEMPERATURE
from app.models import NewsItemResponse, PortfolioItemResponse

logger = logging.getLogger(__name__)


class TwoStepAnalysisService:
    """
    Servicio que implementa análisis de noticias en dos pasos:
    1. Normalización: Extrae datos estructurados de noticias crudas
    2. Análisis: Genera análisis de inversor basado en datos normalizados
    """
    
    def __init__(self):
        """Inicializa el cliente de OpenAI."""
        if not OPENAI_API_KEY or OPENAI_API_KEY == "your_openai_api_key_here":
            raise ValueError("OPENAI_API_KEY no está configurada correctamente")
        
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        self.model = OPENAI_MODEL
        self.temperature = OPENAI_TEMPERATURE
    
    def normalize_news_batch(
        self, 
        news_items: List[NewsItemResponse]
    ) -> List[Dict]:
        """
        Paso 1: Normaliza un lote de noticias crudas.
        
        Extrae: title, date, source, plain_bullets, tickers, geo_tags, 
        sector_tags, uncertainty, source_urls, duplication_notes.
        
        Returns:
            List[Dict]: Lista de noticias normalizadas en formato JSON
        """
        if not news_items:
            return []
        
        # Construir lista de noticias crudas para el prompt
        raw_news_list = []
        for item in news_items:
            raw_news_list.append({
                "id": item.id,
                "title": item.title or "Sin título",
                "body": item.body,
                "source": item.source or "Desconocida",
                "created_at": item.created_at
            })
        
        normalization_prompt = f"""You extract facts from raw news snippets. For each item, return JSON with: title, date, source, plain_bullets (array of 1-2 sentence factual bullets), tickers (with exchange suffix if known, e.g., AAPL.US, TSLA.US), geo_tags, sector_tags, uncertainty (true/false), source_urls ([] if none), and duplication_notes. No extra text.

Validate URLs and drop clearly duplicated stories. Keep an uncertainty flag if details are missing.

Input:
{json.dumps(raw_news_list, ensure_ascii=False, indent=2)}

IMPORTANT: Return a JSON object with a "items" key containing an array. Each element must correspond to an input item and include:
- "id": original id from input
- "title": extracted or cleaned title
- "date": ISO date string or null
- "source": source name or null
- "plain_bullets": array of 1-2 sentence factual bullets (no prose)
- "tickers": array of tickers with exchange suffix (e.g., ["AAPL.US", "TSLA.US"]) or empty array
- "geo_tags": array of geographic tags (e.g., ["US", "Argentina"]) or empty array
- "sector_tags": array of sector tags (e.g., ["TECH", "FINANCE"]) or empty array
- "uncertainty": boolean (true if details are missing or unclear)
- "source_urls": array of URLs or empty array
- "duplication_notes": string describing if story is duplicate or empty string

Return format:
{{
  "items": [
    {{
      "id": <original_id>,
      "title": "extracted title",
      "date": "2024-01-15T10:00:00Z" or null,
      "source": "source name" or null,
      "plain_bullets": ["bullet 1", "bullet 2"],
      "tickers": ["AAPL.US", "TSLA.US"],
      "geo_tags": ["US", "Argentina"],
      "sector_tags": ["TECH", "FINANCE"],
      "uncertainty": false,
      "source_urls": [],
      "duplication_notes": ""
    }}
  ]
}}"""
        
        try:
            logger.info(f"Normalizando {len(news_items)} noticias (Paso 1)")
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a fact extraction assistant. Extract structured data from news articles. "
                            "Return only valid JSON. Validate URLs and drop clearly duplicated stories. "
                            "Keep an uncertainty flag if details are missing."
                        )
                    },
                    {
                        "role": "user",
                        "content": normalization_prompt
                    }
                ],
                temperature=0.3,  # Lower temperature for factual extraction
                response_format={"type": "json_object"},
                timeout=60.0
            )
            
            content = response.choices[0].message.content
            # Parse JSON response
            try:
                normalized_data = json.loads(content)
            except json.JSONDecodeError:
                # Try to extract JSON from text if wrapped
                json_start = content.find('[')
                json_end = content.rfind(']') + 1
                if json_start >= 0 and json_end > json_start:
                    normalized_data = json.loads(content[json_start:json_end])
                else:
                    json_start = content.find('{')
                    json_end = content.rfind('}') + 1
                    if json_start >= 0 and json_end > json_start:
                        normalized_data = json.loads(content[json_start:json_end])
                    else:
                        raise ValueError("No se pudo parsear JSON de la respuesta")
            
            # Handle both array and object with array key
            if isinstance(normalized_data, dict):
                # Try common keys
                normalized_list = normalized_data.get("items", normalized_data.get("news", normalized_data.get("data", [])))
                if not normalized_list:
                    # If dict but no array key, check if it's a single item
                    if "id" in normalized_data:
                        normalized_list = [normalized_data]
                    else:
                        normalized_list = []
            elif isinstance(normalized_data, list):
                normalized_list = normalized_data
            else:
                normalized_list = []
            
            logger.info(f"Normalizadas {len(normalized_list)} noticias exitosamente")
            return normalized_list
            
        except Exception as e:
            logger.error(f"Error en normalización (Paso 1): {e}", exc_info=True)
            # Fallback: crear normalización básica
            return self._create_fallback_normalization(news_items)
    
    def analyze_normalized_news(
        self,
        normalized_news: List[Dict],
        portfolio_items: Optional[List[PortfolioItemResponse]] = None
    ) -> Dict:
        """
        Paso 2: Genera análisis de inversor basado en noticias normalizadas.
        
        Returns:
            Dict con summaries, portfolio_impacts, suggestions
        """
        if not normalized_news:
            return {
                "summaries": [],
                "portfolio_impacts": [],
                "suggestions": [],
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "news_count": 0
            }
        
        # Construir snapshot de cartera
        portfolio_snapshot = ""
        if portfolio_items:
            portfolio_lines = []
            for item in portfolio_items[:20]:  # Limitar a 20 items más recientes
                portfolio_lines.append(f"- {item.name} ({item.symbol or 'N/A'}) - {item.asset_type}")
            portfolio_snapshot = "\n".join(portfolio_lines)
        else:
            portfolio_snapshot = "No hay activos registrados en la cartera."
        
        analysis_prompt = f"""Eres un analista de acciones profesional y gestor de cartera. Sé conciso, factual y explícito sobre la incertidumbre.

Usa el JSON normalizado a continuación. Para cada noticia, produce los campos en el orden mostrado. Evita jerga y no inventes datos. Cierra con 'Impactos en cartera'.

Feed normalizado:
{json.dumps(normalized_news, ensure_ascii=False, indent=2)}

Contexto de cartera del usuario (opcional):
{portfolio_snapshot}

Para cada noticia, proporciona:
- "headline": Un resumen de una oración en español simple
- "plain_explanation": Explicación simple "para principiantes" (1-2 oraciones)
- "impacto_esperado": Dirección + magnitud (ej: "Leve positivo", "Material negativo") con 1-2 factores
- "riesgos_y_dudas": Menciona datos faltantes, fuentes contradictorias o dependencias (aprobaciones, macro, etc.)
- "tickers_afectados": Lista con sufijos de mercado; di "N/A" si es desconocido
- "confidence": "high" | "medium" | "low"

Al final, proporciona:
- "impactos_en_cartera": Resumen del sentimiento neto para tenencias vs. watchlist; menciona consideraciones de efectivo/cobertura

GUARDARRAILES: Nunca inventes números o tickers; marca hechos como "No verificado" si no están respaldados por la entrada estructurada.

Formato JSON de respuesta:
{{
  "items": [
    {{
      "id": <news_id>,
      "headline": "resumen de una oración",
      "plain_explanation": "explicación para principiantes",
      "impacto_esperado": "Leve positivo - factor 1, factor 2",
      "riesgos_y_dudas": "datos faltantes o dependencias",
      "tickers_afectados": ["AAPL.US", "N/A"],
      "confidence": "high"
    }}
  ],
  "impactos_en_cartera": "resumen del sentimiento neto para la cartera"
}}"""
        
        try:
            logger.info(f"Generando análisis para {len(normalized_news)} noticias normalizadas (Paso 2)")
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a professional equity analyst and portfolio manager. "
                            "Be concise, factual, and explicit about uncertainty. "
                            "Never invent numbers or tickers; mark facts as 'No verificado' if unsupported."
                        )
                    },
                    {
                        "role": "user",
                        "content": analysis_prompt
                    }
                ],
                temperature=0.7,
                response_format={"type": "json_object"},
                timeout=90.0
            )
            
            content = response.choices[0].message.content
            analysis_data = json.loads(content)
            
            # Convertir al formato esperado
            summaries = []
            for item in analysis_data.get("items", []):
                summaries.append({
                    "news_id": item.get("id"),
                    "news_title": next((n.get("title", "Sin título") for n in normalized_news if n.get("id") == item.get("id")), "Sin título"),
                    "summary": item.get("headline", ""),
                    "explanation": item.get("plain_explanation", ""),
                    "impacto_esperado": item.get("impacto_esperado", ""),
                    "riesgos_y_dudas": item.get("riesgos_y_dudas", ""),
                    "tickers_afectados": item.get("tickers_afectados", []),
                    "confidence": item.get("confidence", "medium"),
                    "score": 0.0,  # Will be filled by scoring service
                    "sentiment": "neutral"  # Will be filled by scoring service
                })
            
            portfolio_impacts = []
            if analysis_data.get("impactos_en_cartera"):
                portfolio_impacts.append({
                    "type": "summary",
                    "description": analysis_data.get("impactos_en_cartera", "")
                })
            
            logger.info(f"Análisis generado exitosamente para {len(summaries)} noticias")
            
            return {
                "summaries": summaries,
                "portfolio_impacts": portfolio_impacts,
                "suggestions": [],
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "news_count": len(summaries)
            }
            
        except Exception as e:
            logger.error(f"Error en análisis (Paso 2): {e}", exc_info=True)
            # Fallback: crear análisis básico
            return self._create_fallback_analysis(normalized_news)
    
    def _create_fallback_normalization(self, news_items: List[NewsItemResponse]) -> List[Dict]:
        """Crea normalización básica como fallback."""
        normalized = []
        for item in news_items:
            normalized.append({
                "id": item.id,
                "title": item.title or "Sin título",
                "date": item.created_at,
                "source": item.source or None,
                "plain_bullets": [item.body[:200] + "..." if len(item.body) > 200 else item.body],
                "tickers": [],
                "geo_tags": [],
                "sector_tags": [],
                "uncertainty": True,
                "source_urls": [],
                "duplication_notes": "Normalización fallback - datos limitados"
            })
        return normalized
    
    def _create_fallback_analysis(self, normalized_news: List[Dict]) -> Dict:
        """Crea análisis básico como fallback."""
        summaries = []
        for item in normalized_news:
            summaries.append({
                "news_id": item.get("id"),
                "news_title": item.get("title", "Sin título"),
                "summary": " ".join(item.get("plain_bullets", [])[:2]),
                "explanation": "Análisis no disponible temporalmente",
                "impacto_esperado": "No determinado",
                "riesgos_y_dudas": "Datos limitados",
                "tickers_afectados": item.get("tickers", []),
                "confidence": "low",
                "score": 0.0,
                "sentiment": "neutral"
            })
        
        return {
            "summaries": summaries,
            "portfolio_impacts": [],
            "suggestions": [],
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "news_count": len(summaries)
        }

