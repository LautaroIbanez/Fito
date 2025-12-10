"""Servicio para generar explicaciones profesionales de recomendaciones."""
import logging
from typing import Dict, Optional
from app.config import (
    TRADING_RULES_DEFAULT_PRICE_THRESHOLD_PCT,
    TRADING_RULES_DEFAULT_VOLUME_MULTIPLIER
)

logger = logging.getLogger(__name__)


class RecommendationExplanationService:
    """Servicio para generar explicaciones de recomendaciones."""
    
    def generate_explanation(
        self,
        action: str,
        condition: str,
        threshold_data: Dict,
        inputs: Dict,
        asset_name: str,
        sector: Optional[str] = None
    ) -> str:
        """
        Genera explicación profesional de por qué la condición/umbral es relevante.
        
        Args:
            action: Acción recomendada
            condition: Condición que activa la recomendación
            threshold_data: Datos de umbrales
            inputs: Variables consideradas (sentimiento, precio, volumen, etc.)
            asset_name: Nombre del activo
            sector: Sector del activo (opcional)
        
        Returns:
            str: Explicación profesional
        """
        explanation_parts = []
        
        # Explicación base según acción
        action_explanation = self._get_action_explanation(action, asset_name)
        explanation_parts.append(action_explanation)
        
        # Explicación de la condición
        condition_explanation = self._explain_condition(
            condition,
            threshold_data,
            inputs,
            sector
        )
        explanation_parts.append(condition_explanation)
        
        # Explicación de variables clave
        variables_explanation = self._explain_key_variables(inputs, threshold_data)
        if variables_explanation:
            explanation_parts.append(variables_explanation)
        
        return " ".join(explanation_parts)
    
    def _get_action_explanation(self, action: str, asset_name: str) -> str:
        """Genera explicación base de la acción."""
        action_explanations = {
            "add": f"Se recomienda aumentar la exposición a {asset_name} debido a señales positivas identificadas.",
            "reduce": f"Se recomienda reducir la posición en {asset_name} para gestionar riesgos identificados.",
            "trim": f"Se recomienda recortar parcialmente la posición en {asset_name} ante condiciones adversas.",
            "exit": f"Se recomienda considerar salir completamente de {asset_name} ante señales de riesgo significativo.",
            "stop": f"Se recomienda implementar stop loss en {asset_name} para proteger capital ante movimientos adversos.",
            "watch": f"Se recomienda monitorear de cerca {asset_name} ante cambios en condiciones de mercado."
        }
        return action_explanations.get(action.lower(), f"Acción recomendada: {action} para {asset_name}.")
    
    def _explain_condition(
        self,
        condition: str,
        threshold_data: Dict,
        inputs: Dict,
        sector: Optional[str] = None
    ) -> str:
        """Explica por qué la condición/umbral es relevante."""
        explanations = []
        
        # Explicar umbrales de precio
        if threshold_data and threshold_data.get("type") in ["price_below_threshold", "price_above_threshold"]:
            threshold_value = threshold_data.get("value") or TRADING_RULES_DEFAULT_PRICE_THRESHOLD_PCT
            current_change = threshold_data.get("current_price_change")
            
            if current_change is not None:
                if threshold_data["type"] == "price_below_threshold":
                    explanations.append(
                        f"El precio ha caído {abs(current_change):.2f}%, superando el umbral de {threshold_value}% "
                        f"considerado significativo para movimientos de corrección."
                    )
                else:
                    explanations.append(
                        f"El precio ha subido {current_change:.2f}%, superando el umbral de {threshold_value}% "
                        f"que indica momentum positivo."
                    )
            else:
                explanations.append(
                    f"El umbral de {threshold_value}% de variación de precio es relevante porque "
                    f"representa un movimiento significativo que puede indicar cambio de tendencia."
                )
        
        # Explicar umbrales de volumen
        if threshold_data and threshold_data.get("type") == "volume_spike":
            threshold_value = threshold_data.get("value") or TRADING_RULES_DEFAULT_VOLUME_MULTIPLIER
            current_ratio = threshold_data.get("current_volume_ratio")
            
            if current_ratio is not None:
                explanations.append(
                    f"El volumen actual es {current_ratio:.2f}x el promedio, superando el umbral de {threshold_value}x. "
                    f"Esto indica interés institucional o cambio en la dinámica de trading."
                )
            else:
                explanations.append(
                    f"Un volumen {threshold_value}x superior al promedio indica alta participación del mercado "
                    f"y puede confirmar la validez del movimiento de precio."
                )
        
        # Explicar sentimiento
        sentiment = inputs.get("sentiment")
        if sentiment:
            if sentiment == "negative":
                explanations.append(
                    "El sentimiento negativo de las noticias sugiere que pueden persistir presiones a la baja, "
                    "haciendo relevante considerar medidas defensivas."
                )
            elif sentiment == "positive":
                explanations.append(
                    "El sentimiento positivo de las noticias indica que pueden continuar las condiciones favorables, "
                    "apoyando decisiones de aumento de exposición."
                )
        
        # Explicar relevancia sectorial
        if sector:
            relevance = inputs.get("relevance")
            if relevance == "high":
                explanations.append(
                    f"La alta relevancia de las noticias para el sector {sector} sugiere que el impacto "
                    f"puede extenderse a múltiples activos del sector."
                )
        
        # Explicación genérica si no hay detalles específicos
        if not explanations:
            explanations.append(
                "La condición se basa en el análisis combinado de múltiples factores de mercado y noticias."
            )
        
        return " ".join(explanations)
    
    def _explain_key_variables(self, inputs: Dict, threshold_data: Dict) -> Optional[str]:
        """Explica las variables clave consideradas."""
        variables = []
        
        # Sentimiento
        if inputs.get("sentiment"):
            sentiment = inputs["sentiment"]
            sentiment_text = {
                "positive": "positivo",
                "negative": "negativo",
                "neutral": "neutro"
            }.get(sentiment, sentiment)
            variables.append(f"sentimiento {sentiment_text}")
        
        # Precio
        if inputs.get("intraday_change_pct") is not None:
            change = inputs["intraday_change_pct"]
            variables.append(f"variación de precio intradía de {change:+.2f}%")
        
        # Volumen
        if inputs.get("volume_ratio") is not None:
            volume_ratio = inputs["volume_ratio"]
            variables.append(f"volumen {volume_ratio:.2f}x el promedio")
        
        # Relevancia
        if inputs.get("relevance"):
            relevance = inputs["relevance"]
            variables.append(f"relevancia {relevance}")
        
        # Urgencia
        if inputs.get("urgency"):
            urgency = inputs["urgency"]
            variables.append(f"urgencia {urgency}")
        
        if variables:
            return f"Variables consideradas: {', '.join(variables)}."
        
        return None

