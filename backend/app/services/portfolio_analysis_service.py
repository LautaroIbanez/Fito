"""Servicio para análisis de cartera basado en noticias estandarizadas."""
import logging
import json
from typing import List, Dict, Tuple
from datetime import datetime, timezone
from openai import OpenAI
from app.config import (
    OPENAI_API_KEY,
    OPENAI_MODEL,
    OPENAI_TEMPERATURE,
    PORTFOLIO_ANALYSIS_CONFIDENCE_LEVELS,
    PORTFOLIO_ANALYSIS_ACTIONS,
    PORTFOLIO_ANALYSIS_MAX_FOLLOWUP_QUESTIONS
)
from app.models import (
    StandardizedNewsData,
    NewsItemAnalysis,
    PortfolioAnalysisAggregate,
    PortfolioAnalysisResponse
)
from app.services.prompt_packaging_service import PromptPackagingService

logger = logging.getLogger(__name__)


class PortfolioAnalysisService:
    """Servicio para análisis de cartera desde perspectiva de inversor experimentado."""
    
    def __init__(self):
        """Inicializa el cliente de OpenAI."""
        if not OPENAI_API_KEY or OPENAI_API_KEY == "your_openai_api_key_here":
            raise ValueError("OPENAI_API_KEY no está configurada correctamente en app/config.py")
        
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        self.model = OPENAI_MODEL
        self.temperature = OPENAI_TEMPERATURE
        self.packaging_service = PromptPackagingService()
    
    def analyze_portfolio(
        self, 
        standardized_news_items: List[Dict],
        portfolio_items: List[Dict] = None
    ) -> PortfolioAnalysisResponse:
        """
        Analiza el impacto de noticias estandarizadas en la cartera.
        
        Args:
            standardized_news_items: Lista de diccionarios con datos estandarizados de noticias
            portfolio_items: Lista opcional de items de cartera para contexto
            
        Returns:
            PortfolioAnalysisResponse: Análisis estructurado con items individuales y vista agregada
        """
        if not standardized_news_items:
            raise ValueError("Se requiere al menos una noticia estandarizada para el análisis")
        
        try:
            prompt, packaging_metadata = self._build_analysis_prompt(standardized_news_items, portfolio_items)
            
            logger.info(
                f"Generando análisis de cartera: {len(standardized_news_items)} noticias estandarizadas, "
                f"{packaging_metadata['items_included']} items incluidos en prompt, "
                f"{packaging_metadata['items_fallback']} en modo fallback, "
                f"~{packaging_metadata['total_tokens_estimate']} tokens estimados"
            )
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Eres un inversor experimentado con décadas de experiencia en análisis de carteras. "
                            "Tu estilo es conciso, probabilístico y consciente del riesgo. "
                            "Evalúas noticias desde la perspectiva de su impacto en tesis de inversión existentes. "
                            "Eres directo, evitas jerga innecesaria, y te enfocas en implicaciones accionables. "
                            "Siempre consideras tanto oportunidades como riesgos."
                        )
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=self.temperature,
                response_format={"type": "json_object"},
                timeout=90.0
            )
            
            response_text = response.choices[0].message.content
            analysis_dict = json.loads(response_text)
            
            # Validar y estructurar la respuesta
            analysis_response = self._validate_and_structure_response(
                analysis_dict, 
                standardized_news_items
            )
            
            logger.info("Análisis de cartera generado exitosamente")
            return analysis_response
            
        except json.JSONDecodeError as e:
            logger.error(f"Error parseando JSON de respuesta de OpenAI: {e}")
            raise ValueError(f"Error procesando respuesta de OpenAI: formato JSON inválido")
        except Exception as e:
            error_str = str(e)
            logger.error(f"Error generando análisis de cartera: {e}", exc_info=True)
            
            if "401" in error_str or "invalid_api_key" in error_str:
                raise ValueError(
                    "Error de autenticación con OpenAI. Verifica tu API key en app/config.py"
                )
            elif "429" in error_str or "rate_limit" in error_str:
                raise ValueError("Límite de tasa excedido. Por favor, intenta más tarde.")
            elif "insufficient_quota" in error_str:
                raise ValueError("Cuota de OpenAI agotada. Verifica tu cuenta.")
            else:
                raise ValueError(f"Error al generar análisis de cartera: {error_str}")
    
    def _build_analysis_prompt(
        self, 
        standardized_news_items: List[Dict],
        portfolio_items: List[Dict] = None
    ) -> Tuple[str, Dict]:
        """
        Construye el prompt para análisis de cartera usando empaquetado conciso.
        
        Returns:
            Tuple[str, Dict]: (prompt, metadata) donde metadata incluye info de empaquetado
        """
        # Construir template base con instrucciones
        base_template_parts = [
            "Eres un inversor experimentado evaluando el impacto de noticias en una cartera de inversión.\n",
            "IMPORTANTE: Usa SOLO los campos estandarizados proporcionados. NO uses texto crudo de artículos.\n\n",
            "INSTRUCCIONES DE ANÁLISIS:\n",
            "=" * 60 + "\n\n",
            "Para CADA noticia, proporciona:\n",
            "1. thesis_impact: Impacto en la tesis de inversión (2-3 oraciones, conciso)\n",
            "2. risk_flags: Array de banderas de riesgo identificadas (puede estar vacío)\n",
            f"3. confidence_level: Uno de {', '.join(PORTFOLIO_ANALYSIS_CONFIDENCE_LEVELS)}\n",
            f"4. next_action: Una de {', '.join(PORTFOLIO_ANALYSIS_ACTIONS)}\n",
            f"5. followup_questions: Array de 1-2 preguntas de seguimiento para diligencia\n\n",
            "Además, proporciona una vista AGREGADA:\n",
            "1. top_3_opportunities: Top 3 oportunidades identificadas (array de strings)\n",
            "2. top_3_risks: Top 3 riesgos identificados (array de strings)\n",
            "3. market_read: Lectura del mercado en un párrafo (máx 200 palabras)\n\n",
            "TONO Y ESTILO:\n",
            "- Conciso y directo\n",
            "- Probabilístico (evita certezas absolutas)\n",
            "- Consciente del riesgo\n",
            "- Enfocado en implicaciones accionables\n",
            "- Evita jerga innecesaria\n\n",
            "FORMATO DE RESPUESTA (JSON estricto):\n",
            "{\n",
            '  "items": [\n',
            '    {\n',
            '      "news_id": <id de la noticia>,\n',
            '      "news_title": "<título>",\n',
            '      "thesis_impact": "<texto>",\n',
            '      "risk_flags": ["<flag1>", "<flag2>"],\n',
            f'      "confidence_level": "<{"/".join(PORTFOLIO_ANALYSIS_CONFIDENCE_LEVELS)}>",\n',
            f'      "next_action": "<{"/".join(PORTFOLIO_ANALYSIS_ACTIONS)}>",\n',
            '      "followup_questions": ["<pregunta1>", "<pregunta2>"]\n',
            '    },\n',
            '    ...\n',
            '  ],\n',
            '  "aggregate": {\n',
            '    "top_3_opportunities": ["<op1>", "<op2>", "<op3>"],\n',
            '    "top_3_risks": ["<risk1>", "<risk2>", "<risk3>"],\n',
            '    "market_read": "<párrafo>"\n',
            '  }\n',
            '}\n'
        ]
        base_template = "".join(base_template_parts)
        
        # Construir contexto de cartera
        portfolio_context = ""
        if portfolio_items:
            portfolio_parts = [
                "CONTEXTO DE CARTERA:\n",
                "=" * 60 + "\n"
            ]
            for item in portfolio_items:
                portfolio_parts.append(f"- {item.get('name', 'Unknown')}")
                if item.get('symbol'):
                    portfolio_parts.append(f"  Símbolo: {item.get('symbol')}")
                if item.get('asset_type'):
                    portfolio_parts.append(f"  Tipo: {item.get('asset_type')}")
                portfolio_parts.append("")
            portfolio_context = "\n".join(portfolio_parts)
        
        # Usar servicio de empaquetado para noticias
        packaged_prompt, packaging_metadata = self.packaging_service.package_standardized_news(
            standardized_news_items,
            base_prompt_template=base_template,
            portfolio_context=portfolio_context
        )
        
        return packaged_prompt, packaging_metadata
    
    def _validate_and_structure_response(
        self, 
        analysis_dict: Dict,
        standardized_news_items: List[Dict]
    ) -> PortfolioAnalysisResponse:
        """
        Valida y estructura la respuesta del análisis.
        """
        # Validar estructura básica
        if "items" not in analysis_dict:
            raise ValueError("La respuesta debe incluir 'items'")
        if "aggregate" not in analysis_dict:
            raise ValueError("La respuesta debe incluir 'aggregate'")
        
        # Crear mapa de IDs de noticias para validación
        news_id_map = {item.get('id', idx): item for idx, item in enumerate(standardized_news_items, 1)}
        
        # Validar items
        items = []
        for item_dict in analysis_dict["items"]:
            # Validar campos requeridos
            required_fields = ["news_id", "news_title", "thesis_impact", "confidence_level", 
                             "next_action", "followup_questions"]
            for field in required_fields:
                if field not in item_dict:
                    raise ValueError(f"Item de análisis falta campo requerido: {field}")
            
            # Validar que el news_id existe en las noticias proporcionadas
            news_id = item_dict["news_id"]
            if news_id not in news_id_map:
                # Intentar usar el índice si el ID no coincide
                try:
                    idx = int(news_id) - 1
                    if 0 <= idx < len(standardized_news_items):
                        news_id = standardized_news_items[idx].get('id', news_id)
                    else:
                        logger.warning(f"News ID {news_id} no encontrado, usando ID proporcionado")
                except (ValueError, IndexError):
                    logger.warning(f"News ID {news_id} no encontrado, usando ID proporcionado")
            
            # Validar y limpiar
            item = NewsItemAnalysis(
                news_id=news_id,
                news_title=item_dict["news_title"].strip(),
                thesis_impact=item_dict["thesis_impact"].strip(),
                risk_flags=[flag.strip() for flag in item_dict.get("risk_flags", []) if flag.strip()],
                confidence_level=item_dict["confidence_level"],
                next_action=item_dict["next_action"],
                followup_questions=item_dict["followup_questions"]
            )
            items.append(item)
        
        # Validar aggregate
        aggregate_dict = analysis_dict["aggregate"]
        required_aggregate_fields = ["top_3_opportunities", "top_3_risks", "market_read"]
        for field in required_aggregate_fields:
            if field not in aggregate_dict:
                raise ValueError(f"Aggregate falta campo requerido: {field}")
        
        # Validar que haya exactamente 3 oportunidades y 3 riesgos
        opportunities = aggregate_dict["top_3_opportunities"]
        risks = aggregate_dict["top_3_risks"]
        
        if not isinstance(opportunities, list) or len(opportunities) != 3:
            raise ValueError("top_3_opportunities debe ser un array con exactamente 3 elementos")
        
        if not isinstance(risks, list) or len(risks) != 3:
            raise ValueError("top_3_risks debe ser un array con exactamente 3 elementos")
        
        aggregate = PortfolioAnalysisAggregate(
            top_3_opportunities=[op.strip() for op in opportunities if op.strip()],
            top_3_risks=[risk.strip() for risk in risks if risk.strip()],
            market_read=aggregate_dict["market_read"].strip()
        )
        
        return PortfolioAnalysisResponse(
            items=items,
            aggregate=aggregate,
            analyzed_news_count=len(items),
            generated_at=datetime.now(timezone.utc).isoformat()
        )

