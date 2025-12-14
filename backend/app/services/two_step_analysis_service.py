"""Servicio de análisis de noticias en dos pasos: normalización y análisis de inversor."""
import logging
import json
from typing import Dict, List, Optional
from datetime import datetime, timezone
from openai import OpenAI

from app.config import OPENAI_API_KEY, OPENAI_MODEL, OPENAI_TEMPERATURE
from app.models import NewsItemResponse, PortfolioItemResponse
from app.services.sentiment_service import get_sentiment_service
from app.services.sector_service import get_sector_service
from app.services.local_nlp import get_local_nlp_service

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
        Paso 1: Normaliza un lote de noticias crudas usando NLP local (sin LLM).
        
        Extrae: title, date, source, plain_bullets, tickers, geo_tags, 
        sector_tags, uncertainty, source_urls, duplication_notes.
        
        Returns:
            List[Dict]: Lista de noticias normalizadas en formato JSON
        """
        if not news_items:
            return []
        
        logger.info(f"Normalizando {len(news_items)} noticias usando NLP local (sin LLM)")
        
        normalized_list = []
        sentiment_service = get_sentiment_service()
        sector_service = get_sector_service()
        nlp_service = get_local_nlp_service()
        
        for item in news_items:
            try:
                # Combinar título y cuerpo
                full_text = f"{item.title or ''} {item.body}".strip()
                
                # Extraer datos usando NLP local
                analysis = nlp_service.analyze_news(full_text)
                
                # Análisis de sentimiento
                sentiment_result = sentiment_service.analyze_sentiment(
                    text=item.body,
                    title=item.title
                )
                
                # Clasificación de sector
                sector_result = sector_service.classify_sector(
                    text=item.body,
                    title=item.title
                )
                
                # Extraer tickers
                tickers = analysis["tickers"]
                # Agregar sufijo .US si no tiene (asumir US por defecto)
                tickers_with_suffix = [
                    f"{t}.US" if "." not in t else t 
                    for t in tickers
                ]
                
                # Extraer ubicaciones geográficas
                geo_tags = analysis["entities"].get("GPE", [])
                
                # Convertir sector a formato de tags
                sector_tags = []
                if sector_result["primary_sector"]:
                    # Mapear a formato estándar
                    sector_mapping = {
                        "tecnología": "TECH",
                        "finanzas": "FINANCE",
                        "energía": "ENERGY",
                        "salud": "HEALTH",
                        "consumo": "CONSUMER",
                        "industria": "INDUSTRIAL",
                        "telecomunicaciones": "TELECOM",
                        "bienes raíces": "REAL_ESTATE"
                    }
                    primary_sector = sector_result["primary_sector"]
                    sector_tag = sector_mapping.get(primary_sector, primary_sector.upper())
                    sector_tags = [sector_tag]
                
                # Generar bullets básicos (primeras 2 oraciones del texto)
                sentences = full_text.split('.')[:2]
                plain_bullets = [s.strip() + '.' for s in sentences if s.strip()]
                if not plain_bullets:
                    plain_bullets = [full_text[:200] + "..."]
                
                # Parsear fecha
                try:
                    if isinstance(item.created_at, str):
                        date_str = item.created_at
                    else:
                        date_str = item.created_at.isoformat() if item.created_at else None
                except:
                    date_str = None
                
                # Determinar incertidumbre (si falta información clave)
                uncertainty = (
                    not tickers_with_suffix and 
                    not geo_tags and 
                    not sector_tags and
                    len(full_text) < 100
                )
                
                normalized_item = {
                    "id": item.id,
                    "title": item.title or "Sin título",
                    "date": date_str,
                    "source": item.source or "Desconocida",
                    "plain_bullets": plain_bullets,
                    "tickers": tickers_with_suffix,
                    "geo_tags": geo_tags,
                    "sector_tags": sector_tags,
                    "uncertainty": uncertainty,
                    "source_urls": [],
                    "duplication_notes": "",
                    "sentiment": sentiment_result["sentiment"],  # Agregar sentimiento
                    "sentiment_confidence": sentiment_result["confidence"],
                    "sector_confidence": sector_result["confidence"]
                }
                
                normalized_list.append(normalized_item)
                
                logger.debug(
                    f"Noticia ID {item.id} normalizada localmente: "
                    f"sentiment={sentiment_result['sentiment']}, "
                    f"sector={sector_result['primary_sector']}, "
                    f"tickers={len(tickers_with_suffix)}, "
                    f"geo_tags={len(geo_tags)}"
                )
                
            except Exception as e:
                logger.error(f"Error normalizando noticia ID {item.id}: {e}", exc_info=True)
                # Crear item básico de fallback
                normalized_list.append({
                    "id": item.id,
                    "title": item.title or "Sin título",
                    "date": item.created_at.isoformat() if item.created_at else None,
                    "source": item.source or "Desconocida",
                    "plain_bullets": [item.body[:200] + "..." if len(item.body) > 200 else item.body],
                    "tickers": [],
                    "geo_tags": [],
                    "sector_tags": [],
                    "uncertainty": True,
                    "source_urls": [],
                    "duplication_notes": f"Error en normalización: {str(e)}",
                    "sentiment": "neutral",
                    "sentiment_confidence": 0.0,
                    "sector_confidence": 0.0
                })
        
        logger.info(
            f"Normalizadas {len(normalized_list)} noticias exitosamente usando NLP local "
            f"(sin llamadas a OpenAI para sentimiento/sectores)"
        )
        return normalized_list
    
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
        """
        Crea normalización básica usando NLP local (sin LLM) como fallback.
        Este método delega a normalize_news_batch que ya usa NLP local.
        """
        logger.warning(f"Usando normalización de fallback local para {len(news_items)} noticias")
        return self.normalize_news_batch(news_items)
    
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

