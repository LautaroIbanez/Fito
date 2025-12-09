"""Servicio para interactuar con OpenAI API."""
import logging
from typing import Dict, List
from openai import OpenAI
from app.config import (
    OPENAI_API_KEY,
    OPENAI_MODEL,
    OPENAI_TEMPERATURE,
    OPENAI_MAX_TOKENS
)
from app.models import NewsItemResponse, PortfolioItemResponse
from datetime import datetime

logger = logging.getLogger(__name__)


class OpenAIService:
    """Servicio para generar análisis con OpenAI."""
    
    def __init__(self):
        """Inicializa el cliente de OpenAI."""
        if not OPENAI_API_KEY or OPENAI_API_KEY == "your_openai_api_key_here":
            raise ValueError("OPENAI_API_KEY no está configurada correctamente en app/config.py")
        
        # Verificar que la key tenga el formato correcto
        if not OPENAI_API_KEY.startswith("sk-"):
            logger.warning("La API key no parece tener el formato correcto (debería empezar con 'sk-')")
        
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        self.model = OPENAI_MODEL
        self.temperature = OPENAI_TEMPERATURE
        self.max_tokens = OPENAI_MAX_TOKENS
    
    def build_prompt(
        self, 
        news_items: List[NewsItemResponse],
        portfolio_items: List[PortfolioItemResponse] = None
    ) -> str:
        """Construye el prompt para OpenAI con las noticias y la cartera."""
        prompt_parts = [
            "Eres un analista financiero experto. Analiza las siguientes noticias en el contexto de la cartera de inversión del usuario y proporciona recomendaciones específicas.\n\n"
        ]
        
        # Sección de cartera
        if portfolio_items:
            prompt_parts.append("CARTERA DE INVERSIÓN ACTUAL:\n")
            prompt_parts.append("=" * 50 + "\n")
            
            # Agrupar por tipo de activo
            by_type = {}
            for item in portfolio_items:
                if item.asset_type not in by_type:
                    by_type[item.asset_type] = []
                by_type[item.asset_type].append(item)
            
            for asset_type, items in by_type.items():
                prompt_parts.append(f"\n{asset_type.upper()}:\n")
                for item in items:
                    prompt_parts.append(f"  - {item.name}")
                    if item.symbol:
                        prompt_parts.append(f" ({item.symbol})")
                    if item.quantity:
                        prompt_parts.append(f" | Cantidad: {item.quantity}")
                    if item.price:
                        prompt_parts.append(f" | Precio: {item.price}")
                    if item.total_value:
                        prompt_parts.append(f" | Valor Total: {item.total_value}")
                    if item.currency:
                        prompt_parts.append(f" {item.currency}")
                    if item.notes:
                        prompt_parts.append(f" | Notas: {item.notes}")
                    prompt_parts.append("\n")
            
            prompt_parts.append("\n" + "=" * 50 + "\n\n")
        
        # Sección de noticias
        prompt_parts.append("NOTICIAS RECIENTES:\n")
        prompt_parts.append("=" * 50 + "\n")
        
        for idx, item in enumerate(news_items, 1):
            prompt_parts.append(f"\n{idx}. ")
            if item.title:
                prompt_parts.append(f"Título: {item.title}\n")
            if item.source:
                prompt_parts.append(f"Fuente: {item.source}\n")
            prompt_parts.append(f"Fecha: {item.created_at}\n")
            prompt_parts.append(f"Contenido: {item.body[:500]}...\n")  # Primeros 500 caracteres
            prompt_parts.append("-" * 50)
        
        prompt_parts.append("\n\n" + "=" * 50 + "\n")
        prompt_parts.append("INSTRUCCIONES PARA EL ANÁLISIS:\n\n")
        prompt_parts.append("Basándote en las noticias y la cartera actual, proporciona un análisis estructurado con las siguientes secciones:\n\n")
        prompt_parts.append("1. RESUMEN EJECUTIVO: Un resumen conciso de la situación general y su impacto potencial en los mercados.\n\n")
        prompt_parts.append("2. RIESGOS IDENTIFICADOS: Lista de riesgos potenciales detectados que podrían afectar la cartera.\n\n")
        prompt_parts.append("3. ACTORES CLAVE: Personas, organizaciones o entidades mencionadas relevantes para las inversiones.\n\n")
        prompt_parts.append("4. SEÑALES TEMPRANAS: Indicadores o tendencias emergentes que podrían impactar los activos en la cartera.\n\n")
        prompt_parts.append("5. RECOMENDACIONES DE CARTERA: Esta es la sección más importante. Debes proporcionar:\n")
        prompt_parts.append("   - Activos a CONSIDERAR VENDER o REDUCIR (con justificación basada en las noticias)\n")
        prompt_parts.append("   - Activos NUEVOS a CONSIDERAR AGREGAR (con justificación basada en las noticias)\n")
        prompt_parts.append("   - Ajustes de asignación recomendados\n")
        prompt_parts.append("   - Razones específicas basadas en el análisis de las noticias\n\n")
        prompt_parts.append("6. CONCLUSIONES ACCIONABLES: Resumen de acciones concretas recomendadas para el usuario.\n")
        
        return "".join(prompt_parts)
    
    def generate_analysis(
        self, 
        news_items: List[NewsItemResponse],
        portfolio_items: List[PortfolioItemResponse] = None
    ) -> Dict:
        """Genera análisis usando OpenAI considerando noticias y cartera."""
        if not news_items:
            raise ValueError("Se requiere al menos una noticia para generar el análisis")
        
        try:
            prompt = self.build_prompt(news_items, portfolio_items)
            
            portfolio_count = len(portfolio_items) if portfolio_items else 0
            logger.info(f"Generando análisis para {len(news_items)} noticias y {portfolio_count} items de cartera con modelo {self.model}")
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "Eres un analista financiero experto especializado en análisis de carteras de inversión. Proporcionas recomendaciones específicas y accionables basadas en noticias del mercado, considerando el contexto de la cartera actual del usuario. Tus recomendaciones deben ser claras, justificadas y prácticas."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                timeout=60.0  # Timeout de 60 segundos
            )
            
            analysis_text = response.choices[0].message.content
            
            # Parsear el análisis en secciones
            analysis = self._parse_analysis(analysis_text)
            
            return {
                "raw_analysis": analysis_text,
                "structured_analysis": analysis,
                "model_used": self.model,
                "tokens_used": response.usage.total_tokens if hasattr(response, 'usage') else None
            }
            
        except Exception as e:
            error_str = str(e)
            logger.error(f"Error generando análisis con OpenAI: {e}", exc_info=True)
            
            # Mensajes de error más específicos
            if "401" in error_str or "invalid_api_key" in error_str or "Incorrect API key" in error_str:
                raise ValueError(
                    "Error de autenticación con OpenAI. La API key es incorrecta o ha expirado. "
                    "Por favor, verifica tu API key en app/config.py y asegúrate de que sea válida. "
                    "Puedes obtener una nueva key en: https://platform.openai.com/account/api-keys"
                )
            elif "429" in error_str or "rate_limit" in error_str:
                raise ValueError("Límite de tasa excedido. Por favor, intenta más tarde.")
            elif "insufficient_quota" in error_str or "quota" in error_str:
                raise ValueError("Cuota de OpenAI agotada. Por favor, verifica tu cuenta de OpenAI.")
            else:
                raise ValueError(f"Error al generar análisis: {error_str}")
    
    def _parse_analysis(self, text: str) -> Dict:
        """Parsea el texto del análisis en secciones estructuradas."""
        sections = {
            "resumen_ejecutivo": "",
            "riesgos_identificados": "",
            "actores_clave": "",
            "senales_tempranas": "",
            "recomendaciones_cartera": "",
            "conclusiones_accionables": ""
        }
        
        # Buscar secciones por títulos comunes
        text_lower = text.lower()
        
        # Resumen ejecutivo
        if "resumen ejecutivo" in text_lower or "resumen" in text_lower:
            start = text_lower.find("resumen")
            end = text_lower.find("riesgos", start) if "riesgos" in text_lower[start:] else len(text)
            sections["resumen_ejecutivo"] = text[start:end].strip()
        
        # Riesgos
        if "riesgos" in text_lower:
            start = text_lower.find("riesgos")
            end = text_lower.find("actores", start) if "actores" in text_lower[start:] else len(text)
            sections["riesgos_identificados"] = text[start:end].strip()
        
        # Actores clave
        if "actores" in text_lower:
            start = text_lower.find("actores")
            end = text_lower.find("señales", start) if "señales" in text_lower[start:] else len(text)
            sections["actores_clave"] = text[start:end].strip()
        
        # Señales tempranas
        if "señales" in text_lower or "señal" in text_lower:
            start = text_lower.find("señales") if "señales" in text_lower else text_lower.find("señal")
            end = text_lower.find("conclusiones", start) if "conclusiones" in text_lower[start:] else len(text)
            sections["senales_tempranas"] = text[start:end].strip()
        
        # Recomendaciones de cartera
        if "recomendaciones" in text_lower and "cartera" in text_lower:
            start = text_lower.find("recomendaciones")
            end = text_lower.find("conclusiones", start) if "conclusiones" in text_lower[start:] else len(text)
            sections["recomendaciones_cartera"] = text[start:end].strip()
        elif "cartera" in text_lower:
            # Buscar sección de cartera aunque no tenga el título exacto
            start = text_lower.find("cartera")
            end = text_lower.find("conclusiones", start) if "conclusiones" in text_lower[start:] else len(text)
            sections["recomendaciones_cartera"] = text[start:end].strip()
        
        # Conclusiones
        if "conclusiones" in text_lower:
            start = text_lower.find("conclusiones")
            sections["conclusiones_accionables"] = text[start:].strip()
        
        # Si no se encontraron secciones, usar el texto completo
        if not any(sections.values()):
            sections["resumen_ejecutivo"] = text
        
        return sections

