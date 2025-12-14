"""Servicio para gestionar plantillas de prompts y optimizar uso de tokens."""
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
import hashlib
import json

logger = logging.getLogger(__name__)

# Contexto fijo del sistema (instrucciones, tono, disclaimers)
SYSTEM_CONTEXTS = {
    "situation_summary": (
        "Eres un analista financiero experto. Tu tarea es generar un resumen conciso "
        "y claro de la situación actual del mercado basado en las noticias proporcionadas. "
        "El resumen debe ser breve (2-4 párrafos máximo), directo y enfocado en los puntos clave. "
        "Evita jerga técnica innecesaria. Sé objetivo y basado en hechos."
    ),
    "scenario_generation": (
        "Eres un estratega financiero experto especializado en generación de escenarios. "
        "Generas escenarios realistas basados en datos y noticias del mercado. "
        "Cada escenario incluye supuestos claros, riesgos identificados e invalidadores. "
        "Eres preciso, evitas especulación sin fundamento, y siempre basas tus escenarios "
        "en la información proporcionada."
    ),
    "portfolio_analysis": (
        "Eres un inversor experimentado con décadas de experiencia en análisis de carteras. "
        "Tu estilo es conciso, probabilístico y consciente del riesgo. "
        "Evalúas noticias desde la perspectiva de su impacto en tesis de inversión existentes. "
        "Eres directo, evitas jerga innecesaria, y te enfocas en implicaciones accionables. "
        "Siempre consideras tanto oportunidades como riesgos."
    ),
    "technical_analysis": (
        "Eres un analista técnico experto. Interpretas indicadores técnicos y señales de trading "
        "en el contexto de noticias y datos fundamentales. Proporcionas análisis concisos y accionables. "
        "Evitas sobreinterpretación y te basas en datos concretos."
    )
}

# Límites de longitud para diferentes tipos de datos
LENGTH_LIMITS = {
    "news_item": 500,  # Caracteres por noticia
    "news_list": 10,   # Máximo de noticias en prompt
    "price_points": 50,  # Máximo de puntos de precio
    "signals": 10,     # Máximo de señales
    "technical_indicators": 5,  # Máximo de indicadores a mencionar
    "total_prompt_chars": 8000  # Límite total de caracteres en prompt
}


class PromptTemplateService:
    """Servicio para gestionar plantillas de prompts y optimizar tokens."""
    
    def __init__(self):
        self.length_limits = LENGTH_LIMITS
        self.system_contexts = SYSTEM_CONTEXTS
    
    def get_system_context(self, context_type: str) -> str:
        """Obtiene el contexto del sistema para un tipo de prompt."""
        return self.system_contexts.get(context_type, "")
    
    def truncate_news_item(self, news_item: Dict, max_chars: int = None) -> Dict:
        """
        Trunca una noticia individual para limitar su longitud.
        
        Args:
            news_item: Diccionario con datos de noticia
            max_chars: Máximo de caracteres (default: LENGTH_LIMITS["news_item"])
        
        Returns:
            Noticia truncada
        """
        max_chars = max_chars or self.length_limits["news_item"]
        
        truncated = news_item.copy()
        
        # Truncar body si existe
        if "body" in truncated and len(truncated["body"]) > max_chars:
            truncated["body"] = truncated["body"][:max_chars] + "..."
        
        # Truncar summary si existe
        if "summary" in truncated and isinstance(truncated["summary"], str):
            if len(truncated["summary"]) > max_chars:
                truncated["summary"] = truncated["summary"][:max_chars] + "..."
        
        # Truncar standardized_data.summary si existe
        if "standardized_data" in truncated and isinstance(truncated["standardized_data"], dict):
            std_data = truncated["standardized_data"].copy()
            if "summary" in std_data and isinstance(std_data["summary"], str):
                if len(std_data["summary"]) > max_chars:
                    std_data["summary"] = std_data["summary"][:max_chars] + "..."
            truncated["standardized_data"] = std_data
        
        return truncated
    
    def truncate_news_list(
        self, 
        news_items: List[Dict], 
        max_items: int = None,
        max_chars_per_item: int = None
    ) -> List[Dict]:
        """
        Trunca una lista de noticias, limitando cantidad y longitud individual.
        
        Args:
            news_items: Lista de noticias
            max_items: Máximo de noticias (default: LENGTH_LIMITS["news_list"])
            max_chars_per_item: Máximo de caracteres por noticia
        
        Returns:
            Lista truncada de noticias
        """
        max_items = max_items or self.length_limits["news_list"]
        max_chars_per_item = max_chars_per_item or self.length_limits["news_item"]
        
        # Limitar cantidad
        truncated_list = news_items[:max_items]
        
        # Truncar cada noticia
        return [self.truncate_news_item(item, max_chars_per_item) for item in truncated_list]
    
    def truncate_price_data(
        self,
        price_points: List[Dict],
        max_points: int = None
    ) -> List[Dict]:
        """
        Trunca datos de precio, manteniendo solo los más recientes.
        
        Args:
            price_points: Lista de puntos de precio
            max_points: Máximo de puntos (default: LENGTH_LIMITS["price_points"])
        
        Returns:
            Lista truncada de puntos de precio
        """
        max_points = max_points or self.length_limits["price_points"]
        return price_points[-max_points:]  # Mantener los más recientes
    
    def truncate_signals(
        self,
        signals: List[Dict],
        max_signals: int = None
    ) -> List[Dict]:
        """
        Trunca lista de señales, manteniendo solo las más recientes.
        
        Args:
            signals: Lista de señales
            max_signals: Máximo de señales (default: LENGTH_LIMITS["signals"])
        
        Returns:
            Lista truncada de señales
        """
        max_signals = max_signals or self.length_limits["signals"]
        return signals[-max_signals:]  # Mantener las más recientes
    
    def estimate_tokens(self, text: str) -> int:
        """
        Estima el número de tokens en un texto.
        Aproximación: 1 token ≈ 4 caracteres (para español/inglés mixto).
        
        Args:
            text: Texto a estimar
        
        Returns:
            Estimación de tokens
        """
        return len(text) // 4
    
    def validate_prompt_length(self, prompt: str, max_chars: int = None) -> tuple[bool, int, int]:
        """
        Valida la longitud de un prompt.
        
        Args:
            prompt: Prompt a validar
            max_chars: Máximo de caracteres permitidos
        
        Returns:
            Tuple (is_valid, char_count, estimated_tokens)
        """
        max_chars = max_chars or self.length_limits["total_prompt_chars"]
        char_count = len(prompt)
        estimated_tokens = self.estimate_tokens(prompt)
        is_valid = char_count <= max_chars
        
        return (is_valid, char_count, estimated_tokens)
    
    def build_optimized_prompt(
        self,
        template_type: str,
        variable_data: Dict,
        max_total_chars: int = None
    ) -> Dict[str, Any]:
        """
        Construye un prompt optimizado usando plantillas.
        
        Args:
            template_type: Tipo de plantilla (situation_summary, scenario_generation, etc.)
            variable_data: Datos variables a insertar
            max_total_chars: Máximo total de caracteres
        
        Returns:
            Dict con prompt, metadata y validación
        """
        max_total_chars = max_total_chars or self.length_limits["total_prompt_chars"]
        
        # Obtener contexto del sistema
        system_context = self.get_system_context(template_type)
        
        # Truncar datos variables según el tipo
        truncated_data = self._truncate_variable_data(template_type, variable_data)
        
        # Construir prompt usando plantilla específica
        user_prompt = self._build_user_prompt(template_type, truncated_data)
        
        # Validar longitud
        full_prompt = system_context + "\n\n" + user_prompt
        is_valid, char_count, estimated_tokens = self.validate_prompt_length(full_prompt, max_total_chars)
        
        if not is_valid:
            logger.warning(
                f"Prompt excede límite: {char_count} chars, {estimated_tokens} tokens estimados. "
                f"Truncando datos variables..."
            )
            # Aplicar truncamiento más agresivo
            truncated_data = self._apply_aggressive_truncation(template_type, variable_data)
            user_prompt = self._build_user_prompt(template_type, truncated_data)
            full_prompt = system_context + "\n\n" + user_prompt
            is_valid, char_count, estimated_tokens = self.validate_prompt_length(full_prompt, max_total_chars)
        
        return {
            "system_content": system_context,
            "user_content": user_prompt,
            "full_prompt": full_prompt,
            "char_count": char_count,
            "estimated_tokens": estimated_tokens,
            "is_valid": is_valid,
            "truncated_data": truncated_data
        }
    
    def _truncate_variable_data(self, template_type: str, variable_data: Dict) -> Dict:
        """Trunca datos variables según el tipo de plantilla."""
        truncated = variable_data.copy()
        
        if template_type == "situation_summary":
            if "news_items" in truncated:
                truncated["news_items"] = self.truncate_news_list(truncated["news_items"])
        
        elif template_type == "scenario_generation":
            if "related_news_items" in truncated:
                truncated["related_news_items"] = self.truncate_news_list(truncated["related_news_items"])
        
        elif template_type == "technical_analysis":
            if "price_points" in truncated:
                truncated["price_points"] = self.truncate_price_data(truncated["price_points"])
            if "signals" in truncated:
                truncated["signals"] = self.truncate_signals(truncated["signals"])
        
        return truncated
    
    def _apply_aggressive_truncation(self, template_type: str, variable_data: Dict) -> Dict:
        """Aplica truncamiento más agresivo si el prompt aún es muy largo."""
        truncated = variable_data.copy()
        
        # Reducir límites a la mitad
        if template_type == "situation_summary":
            if "news_items" in truncated:
                truncated["news_items"] = self.truncate_news_list(
                    truncated["news_items"],
                    max_items=self.length_limits["news_list"] // 2,
                    max_chars_per_item=self.length_limits["news_item"] // 2
                )
        
        elif template_type == "scenario_generation":
            if "related_news_items" in truncated:
                truncated["related_news_items"] = self.truncate_news_list(
                    truncated["related_news_items"],
                    max_items=self.length_limits["news_list"] // 2,
                    max_chars_per_item=self.length_limits["news_item"] // 2
                )
        
        return truncated
    
    def _build_user_prompt(self, template_type: str, variable_data: Dict) -> str:
        """Construye el prompt del usuario según el tipo de plantilla."""
        if template_type == "situation_summary":
            return self._build_situation_summary_prompt(variable_data)
        elif template_type == "scenario_generation":
            return self._build_scenario_generation_prompt(variable_data)
        elif template_type == "technical_analysis":
            return self._build_technical_analysis_prompt(variable_data)
        else:
            raise ValueError(f"Tipo de plantilla desconocido: {template_type}")
    
    def _build_situation_summary_prompt(self, data: Dict) -> str:
        """Construye prompt para resumen de situación."""
        news_items = data.get("news_items", [])
        batch_number = data.get("batch_number")
        total_batches = data.get("total_batches")
        
        news_text = ""
        for idx, news in enumerate(news_items, 1):
            standardized = news.get("standardized_data") or {}
            # Si standardized_data es None o no tiene summary, usar body o title
            if isinstance(standardized, dict):
                summary = standardized.get("summary") or news.get("body") or news.get("title") or "Sin contenido"
            else:
                summary = news.get("body") or news.get("title") or "Sin contenido"
            
            # Limitar longitud del summary
            if len(summary) > 200:
                summary = summary[:200] + "..."
            
            sentiment = standardized.get("sentiment", "neutral") if isinstance(standardized, dict) else "neutral"
            news_text += f"\n{idx}. [{sentiment.upper()}] {summary}\n"
        
        batch_info = ""
        if batch_number and total_batches:
            batch_info = f"\n[Lote {batch_number} de {total_batches}]\n"
        
        return f"""Genera un resumen conciso de la situación actual del mercado basado en estas noticias:{batch_info}

NOTICIAS:
{news_text}

Resumen (2-4 párrafos máximo, enfocado en puntos clave):"""
    
    def _build_scenario_generation_prompt(self, data: Dict) -> str:
        """Construye prompt para generación de escenarios."""
        driver = data.get("driver", {})
        related_news = data.get("related_news_items", [])
        
        driver_name = driver.get("driver", "Unknown")
        driver_description = driver.get("description", "")
        
        news_summaries = []
        for news in related_news:
            standardized = news.get("standardized_data") or {}
            if isinstance(standardized, dict):
                summary = standardized.get("summary") or news.get("body") or news.get("title") or ""
                sentiment = standardized.get("sentiment", "neutral")
                tickers = standardized.get("tickers", [])[:5]
                categories = standardized.get("categories", [])[:3]
            else:
                summary = news.get("body") or news.get("title") or ""
                sentiment = "neutral"
                tickers = []
                categories = []
            
            news_summaries.append({
                "summary": summary[:300],
                "sentiment": sentiment,
                "tickers": tickers,
                "categories": categories
            })
        
        return f"""Genera tres escenarios para el siguiente driver temático del mercado:

DRIVER: {driver_name}
DESCRIPCIÓN: {driver_description}

NOTICIAS RELACIONADAS:
{json.dumps(news_summaries, indent=2, ensure_ascii=False)}

Genera tres tipos de escenarios:

1. BASE (escenario base): El escenario más probable basado en las noticias actuales
2. RISK (escenario de riesgo): Un escenario negativo que podría materializarse
3. OPPORTUNITY (escenario de oportunidad): Un escenario positivo que podría materializarse

Para cada escenario, proporciona:
- title: Título conciso del escenario
- description: Descripción detallada (2-3 párrafos)
- assumptions: Lista de supuestos clave (mínimo 2, máximo 5)
- risks: Lista de riesgos asociados (mínimo 1, máximo 3)
- invalidators: Lista de condiciones que invalidarían el escenario (mínimo 1, máximo 3)
- confidence: Nivel de confianza (0.0-1.0)
- timeframe: Horizonte temporal estimado (ej: "3-6 meses", "1-2 semanas")
- market_impact: Impacto esperado en el mercado (1-2 oraciones breves)
- suggested_actions: Lista de acciones sugeridas (2-3 items)
- triggers: Lista de eventos o condiciones trigger a monitorear (2-3 items)

IMPORTANTE: Responde ÚNICAMENTE en formato JSON válido con esta estructura exacta:
{{
    "base": {{
        "title": "Título del escenario base",
        "description": "Descripción detallada...",
        "assumptions": [
            {{"description": "Supuesto 1", "probability": 0.7, "timeframe": "3 meses"}}
        ],
        "risks": [
            {{"description": "Riesgo 1", "severity": "medium", "mitigation": "Estrategia de mitigación"}}
        ],
        "invalidators": [
            {{"condition": "Condición que invalida", "description": "Por qué invalida"}}
        ],
        "confidence": 0.75,
        "timeframe": "3-6 meses",
        "market_impact": "Impacto esperado en el mercado...",
        "suggested_actions": ["Acción 1", "Acción 2"],
        "triggers": ["Evento 1", "Evento 2"]
    }},
    "risk": {{
        "title": "Título del escenario de riesgo",
        "description": "Descripción detallada...",
        "assumptions": [...],
        "risks": [...],
        "invalidators": [...],
        "confidence": 0.65,
        "timeframe": "1-3 meses",
        "market_impact": "Impacto esperado en el mercado...",
        "suggested_actions": ["Acción 1", "Acción 2"],
        "triggers": ["Evento 1", "Evento 2"]
    }},
    "opportunity": {{
        "title": "Título del escenario de oportunidad",
        "description": "Descripción detallada...",
        "assumptions": [...],
        "risks": [...],
        "invalidators": [...],
        "confidence": 0.60,
        "timeframe": "6-12 meses",
        "market_impact": "Impacto esperado en el mercado...",
        "suggested_actions": ["Acción 1", "Acción 2"],
        "triggers": ["Evento 1", "Evento 2"]
    }}
}}"""
    
    def _build_technical_analysis_prompt(self, data: Dict) -> str:
        """Construye prompt para análisis técnico."""
        symbol = data.get("symbol", "Activo")
        price_points = data.get("price_points", [])
        indicators = data.get("indicators", {})
        signals = data.get("signals", [])
        
        # Resumen de precios (últimos 5 puntos)
        recent_prices = price_points[-5:] if len(price_points) > 5 else price_points
        price_list = [f"${p.get('close', 0):.2f}" for p in recent_prices]
        price_summary = f"Últimos precios: {', '.join(price_list)}"
        
        # Resumen de indicadores
        indicators_summary = []
        if indicators.get("sma5"):
            indicators_summary.append(f"SMA5: {indicators['sma5']:.2f}")
        if indicators.get("sma15"):
            indicators_summary.append(f"SMA15: {indicators['sma15']:.2f}")
        if indicators.get("rsi"):
            indicators_summary.append(f"RSI: {indicators['rsi']:.2f}")
        if indicators.get("macd"):
            macd = indicators["macd"]
            indicators_summary.append(f"MACD: {macd.get('macd', 0):.4f}, Signal: {macd.get('signal', 0):.4f}")
        
        # Resumen de señales (últimas 5)
        recent_signals = signals[-5:] if len(signals) > 5 else signals
        signals_summary = "\n".join([
            f"- {s['type'].upper()}: {s['reason']} (Precio: ${s['price']:.2f})"
            for s in recent_signals
        ]) if recent_signals else "No hay señales recientes"
        
        return f"""Analiza la situación técnica del activo {symbol}:

{price_summary}

Indicadores técnicos:
{', '.join(indicators_summary) if indicators_summary else 'No disponibles'}

Señales detectadas:
{signals_summary}

Proporciona un análisis técnico conciso (2-3 párrafos) integrando estos datos con el contexto del mercado."""
    
    def _build_meta_summary_prompt(self, data: Dict) -> str:
        """Construye prompt para meta-resumen de lotes."""
        batch_summaries = data.get("batch_summaries", [])
        
        summaries_text = ""
        for batch_summary in batch_summaries:
            summaries_text += f"\nLote {batch_summary['batch_number']} ({batch_summary['news_count']} noticias):\n"
            summaries_text += f"{batch_summary['summary']}\n"
        
        return f"""Genera un meta-resumen ejecutivo consolidado (2-4 párrafos) que sintetice la situación actual del mercado 
basado en los siguientes resúmenes parciales de diferentes lotes de noticias.

El meta-resumen debe:
- Integrar los puntos clave de todos los lotes
- Identificar tendencias y patrones comunes
- Proporcionar una visión general coherente y concisa
- Evitar redundancias entre lotes

RESÚMENES PARCIALES:
{summaries_text}

Genera el meta-resumen ejecutivo consolidado:"""
