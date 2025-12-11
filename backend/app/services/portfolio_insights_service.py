"""Servicio para generar insights profesionales sobre la cartera usando IA."""
import logging
import json
from typing import List, Dict, Optional
from datetime import datetime, timezone
from openai import OpenAI

from app.config import OPENAI_API_KEY, OPENAI_MODEL, OPENAI_TEMPERATURE
from app.models import PortfolioItemResponse

logger = logging.getLogger(__name__)


class PortfolioInsightsService:
    """
    Servicio que genera insights profesionales sobre la cartera.
    Actúa como un inversor profesional que analiza la cartera y busca noticias del sector.
    """
    
    def __init__(self):
        """Inicializa el cliente de OpenAI."""
        if not OPENAI_API_KEY or OPENAI_API_KEY == "your_openai_api_key_here":
            raise ValueError("OPENAI_API_KEY no está configurada correctamente")
        
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        self.model = OPENAI_MODEL
        self.temperature = OPENAI_TEMPERATURE
    
    def generate_professional_insights(
        self,
        portfolio_items: List[PortfolioItemResponse],
        portfolio_value: float,
        recent_news_count: int = 0
    ) -> List[Dict[str, str]]:
        """
        Genera insights profesionales sobre la cartera.
        
        Args:
            portfolio_items: Lista de items de la cartera
            portfolio_value: Valor total de la cartera
            recent_news_count: Número de noticias recientes disponibles
            
        Returns:
            Lista de insights con 'title' y 'explanation'
        """
        try:
            # Construir contexto de la cartera
            portfolio_context = self._build_portfolio_context(portfolio_items, portfolio_value)
            
            # Construir prompt para el análisis profesional
            system_prompt = (
                "Eres un inversor profesional con décadas de experiencia en gestión de carteras. "
                "Tu rol es analizar carteras de inversión y proporcionar insights accionables basados en: "
                "1. Análisis técnico y fundamental de los activos en la cartera "
                "2. Noticias recientes del sector y del mercado "
                "3. Tendencias macroeconómicas relevantes "
                "4. Riesgos y oportunidades identificados "
                "\n"
                "IMPORTANTE: "
                "- Siempre explica el POR QUÉ de cada conclusión "
                "- Menciona noticias o eventos específicos cuando sea relevante "
                "- Sé específico sobre sectores, activos o condiciones de mercado "
                "- Proporciona contexto sobre por qué algo es importante "
                "- Si no hay suficiente información, sé honesto al respecto "
                "- Mantén un tono profesional pero accesible "
                "- Máximo 3-4 insights, priorizando los más relevantes y accionables"
            )
            
            user_prompt = f"""
Analiza la siguiente cartera de inversión y genera insights profesionales:

{portfolio_context}

Contexto adicional:
- Hay {recent_news_count} noticias recientes disponibles en el sistema
- El análisis debe considerar noticias del sector, condiciones de mercado y tendencias macroeconómicas

Genera insights que:
1. Identifiquen riesgos o oportunidades específicas
2. Expliquen el POR QUÉ de cada conclusión (menciona noticias, eventos o tendencias relevantes)
3. Sean accionables y relevantes para un inversor
4. Consideren la composición actual de la cartera

Responde en formato JSON con la siguiente estructura:
{{
  "insights": [
    {{
      "title": "Título conciso del insight (máximo 80 caracteres)",
      "explanation": "Explicación detallada del por qué, mencionando noticias, eventos o análisis específico (máximo 200 caracteres)"
    }}
  ]
}}
"""
            
            logger.info(f"Generando insights profesionales para cartera con {len(portfolio_items)} activos")
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=self.temperature,
                response_format={"type": "json_object"},
                max_tokens=800,
                timeout=90.0
            )
            
            content = response.choices[0].message.content
            analysis_data = json.loads(content)
            
            insights = analysis_data.get("insights", [])
            
            # Validar y limpiar insights
            validated_insights = []
            for insight in insights:
                if isinstance(insight, dict) and "title" in insight and "explanation" in insight:
                    validated_insights.append({
                        "title": str(insight["title"]).strip(),
                        "explanation": str(insight["explanation"]).strip()
                    })
            
            logger.info(f"Generados {len(validated_insights)} insights profesionales")
            return validated_insights
            
        except json.JSONDecodeError as e:
            logger.error(f"Error parseando JSON de insights: {e}\nContenido: {content}", exc_info=True)
            # Retornar insight por defecto
            return [{
                "title": "Análisis en proceso",
                "explanation": "El sistema está procesando información de mercado para generar insights personalizados."
            }]
        except Exception as e:
            logger.error(f"Error generando insights profesionales: {e}", exc_info=True)
            # Retornar insight por defecto
            return [{
                "title": "Análisis temporalmente no disponible",
                "explanation": "No se pudieron generar insights en este momento. Intenta nuevamente más tarde."
            }]
    
    def _build_portfolio_context(
        self,
        portfolio_items: List[PortfolioItemResponse],
        portfolio_value: float
    ) -> str:
        """Construye el contexto de la cartera para el análisis."""
        if not portfolio_items:
            return "Cartera vacía - No hay activos registrados."
        
        context_parts = [f"Valor total de la cartera: ${portfolio_value:,.2f}\n"]
        context_parts.append(f"Total de activos: {len(portfolio_items)}\n\n")
        context_parts.append("Composición de la cartera:\n")
        
        # Calcular concentraciones
        for item in portfolio_items:
            item_value = 0.0
            if item.total_value:
                try:
                    item_value = float(item.total_value.replace(',', ''))
                except (ValueError, AttributeError):
                    pass
            elif item.quantity and item.price:
                try:
                    qty = float(item.quantity.replace(',', ''))
                    price = float(item.price.replace(',', ''))
                    item_value = qty * price
                except (ValueError, AttributeError):
                    pass
            
            percentage = (item_value / portfolio_value * 100) if portfolio_value > 0 else 0
            
            item_info = f"- {item.name}"
            if item.symbol:
                item_info += f" ({item.symbol})"
            item_info += f" - Tipo: {item.asset_type}"
            if item_value > 0:
                item_info += f" - Valor: ${item_value:,.2f} ({percentage:.1f}%)"
            if item.quantity:
                item_info += f" - Cantidad: {item.quantity}"
            if item.price:
                item_info += f" - Precio unitario: ${item.price}"
            
            context_parts.append(item_info)
        
        # Análisis de concentración
        if portfolio_value > 0:
            context_parts.append("\nAnálisis de concentración:")
            sorted_items = sorted(
                [(item, float(item.total_value.replace(',', '')) if item.total_value else 0.0) 
                 for item in portfolio_items],
                key=lambda x: x[1],
                reverse=True
            )
            
            if sorted_items and sorted_items[0][1] > 0:
                top_item, top_value = sorted_items[0]
                top_pct = (top_value / portfolio_value) * 100
                context_parts.append(f"- Posición principal: {top_item.name} ({top_pct:.1f}% del total)")
        
        return "\n".join(context_parts)

