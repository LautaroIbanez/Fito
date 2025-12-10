"""Motor de reglas plantillado para generar recomendaciones de trading."""
import logging
from typing import Dict, List, Optional, Tuple
from app.config import (
    TRADING_RULES_DEFAULT_PRICE_THRESHOLD_PCT,
    TRADING_RULES_DEFAULT_VOLUME_MULTIPLIER,
    TRADING_RULES_DEFAULT_ATR_MULTIPLIER,
    TRADING_RULES_MIN_CONFIDENCE
)

logger = logging.getLogger(__name__)


class TradingRule:
    """Representa una regla de trading parametrizable."""
    
    def __init__(
        self,
        condition_type: str,  # "price_below", "price_above", "volume_spike", "sentiment_negative", etc.
        action: str,  # "reduce", "stop", "add", "trim", "exit", "watch"
        threshold: Optional[float] = None,
        description: str = "",
        priority: int = 1  # Mayor número = mayor prioridad
    ):
        self.condition_type = condition_type
        self.action = action
        self.threshold = threshold
        self.description = description
        self.priority = priority
    
    def evaluate(
        self,
        market_features: Dict,
        sentiment: str,
        relevance: str,
        urgency: str,
        confidence: float
    ) -> Tuple[bool, Optional[str]]:
        """
        Evalúa si la regla se cumple.
        
        Returns:
            Tuple[bool, Optional[str]]: (se_cumple, razon)
        """
        # Verificar confianza mínima
        if confidence < TRADING_RULES_MIN_CONFIDENCE:
            return False, f"Confianza insuficiente ({confidence:.0%} < {TRADING_RULES_MIN_CONFIDENCE:.0%})"
        
        # Evaluar según tipo de condición
        if self.condition_type == "price_below_threshold":
            price_change = market_features.get("intraday_change_pct")
            if price_change is not None and price_change < -(self.threshold or TRADING_RULES_DEFAULT_PRICE_THRESHOLD_PCT):
                return True, f"Precio cayó {abs(price_change):.2f}% (umbral: {self.threshold or TRADING_RULES_DEFAULT_PRICE_THRESHOLD_PCT}%)"
        
        elif self.condition_type == "price_above_threshold":
            price_change = market_features.get("intraday_change_pct")
            if price_change is not None and price_change > (self.threshold or TRADING_RULES_DEFAULT_PRICE_THRESHOLD_PCT):
                return True, f"Precio subió {price_change:.2f}% (umbral: {self.threshold or TRADING_RULES_DEFAULT_PRICE_THRESHOLD_PCT}%)"
        
        elif self.condition_type == "sentiment_negative":
            if sentiment == "negative":
                return True, "Sentimiento negativo detectado en noticias"
        
        elif self.condition_type == "sentiment_positive":
            if sentiment == "positive":
                return True, "Sentimiento positivo detectado en noticias"
        
        elif self.condition_type == "volume_spike":
            volume_ratio = market_features.get("volume_ratio")
            threshold = self.threshold or TRADING_RULES_DEFAULT_VOLUME_MULTIPLIER
            if volume_ratio is not None and volume_ratio > threshold:
                return True, f"Volumen {volume_ratio:.2f}x el promedio (umbral: {threshold}x)"
        
        elif self.condition_type == "high_relevance":
            if relevance == "high":
                return True, "Alta relevancia de noticias para este activo"
        
        elif self.condition_type == "high_urgency":
            if urgency == "high":
                return True, "Noticias urgentes detectadas"
        
        elif self.condition_type == "atr_breakout":
            # Esta regla requeriría más contexto, simplificada por ahora
            atr = market_features.get("atr")
            if atr is not None:
                return True, f"ATR disponible: {atr:.2f}"
        
        elif self.condition_type == "combined_negative":
            # Combinación: sentimiento negativo + caída de precio
            price_change = market_features.get("intraday_change_pct")
            if sentiment == "negative" and price_change is not None and price_change < -2.0:
                return True, f"Sentimiento negativo + precio cayó {abs(price_change):.2f}%"
        
        elif self.condition_type == "combined_positive":
            # Combinación: sentimiento positivo + subida de precio
            price_change = market_features.get("intraday_change_pct")
            if sentiment == "positive" and price_change is not None and price_change > 2.0:
                return True, f"Sentimiento positivo + precio subió {price_change:.2f}%"
        
        return False, None


class TradingRulesEngine:
    """Motor de reglas para generar recomendaciones de trading."""
    
    def __init__(self):
        """Inicializa el motor con reglas por defecto."""
        self.default_rules = self._create_default_rules()
    
    def _create_default_rules(self) -> List[TradingRule]:
        """Crea reglas por defecto."""
        return [
            # Reglas de reducción/stop
            TradingRule(
                condition_type="combined_negative",
                action="reduce",
                threshold=5.0,
                description="Reducir posición si sentimiento negativo + precio cae >5%",
                priority=5
            ),
            TradingRule(
                condition_type="sentiment_negative",
                action="stop",
                threshold=None,
                description="Considerar stop loss si sentimiento muy negativo",
                priority=4
            ),
            TradingRule(
                condition_type="price_below_threshold",
                action="trim",
                threshold=5.0,
                description="Recortar posición si precio cae >5%",
                priority=3
            ),
            
            # Reglas de adición
            TradingRule(
                condition_type="combined_positive",
                action="add",
                threshold=3.0,
                description="Aumentar posición si sentimiento positivo + precio sube >3%",
                priority=4
            ),
            TradingRule(
                condition_type="sentiment_positive",
                action="add",
                threshold=None,
                description="Considerar aumentar posición con sentimiento positivo",
                priority=2
            ),
            
            # Reglas de monitoreo
            TradingRule(
                condition_type="high_relevance",
                action="watch",
                threshold=None,
                description="Monitorear activo con noticias de alta relevancia",
                priority=1
            ),
            TradingRule(
                condition_type="high_urgency",
                action="watch",
                threshold=None,
                description="Monitorear activo con noticias urgentes",
                priority=2
            ),
            
            # Reglas de salida
            TradingRule(
                condition_type="price_below_threshold",
                action="exit",
                threshold=10.0,
                description="Considerar salida si precio cae >10%",
                priority=6
            ),
        ]
    
    def generate_recommendations(
        self,
        market_features: Dict,
        sentiment: str,
        relevance: str,
        urgency: str,
        confidence: float,
        custom_rules: Optional[List[TradingRule]] = None
    ) -> List[Dict]:
        """
        Genera recomendaciones basadas en reglas y contexto.
        
        Returns:
            List[Dict]: Lista de recomendaciones con condición, acción y motivo
        """
        rules = custom_rules or self.default_rules
        
        # Ordenar reglas por prioridad (mayor primero)
        rules_sorted = sorted(rules, key=lambda r: r.priority, reverse=True)
        
        recommendations = []
        seen_actions = set()  # Evitar recomendaciones duplicadas para la misma acción
        
        for rule in rules_sorted:
            is_triggered, reason = rule.evaluate(
                market_features,
                sentiment,
                relevance,
                urgency,
                confidence
            )
            
            if is_triggered:
                # Evitar duplicados de la misma acción
                action_key = f"{rule.action}_{rule.condition_type}"
                if action_key not in seen_actions:
                    recommendation = {
                        "action": rule.action,
                        "condition": self._format_condition(rule, market_features),
                        "reason": reason or rule.description,
                        "threshold": self._get_threshold_info(rule, market_features),
                        "confidence": confidence,
                        "priority": rule.priority
                    }
                    recommendations.append(recommendation)
                    seen_actions.add(action_key)
        
        # Si no hay recomendaciones, sugerir "watch" por defecto si hay relevancia
        if not recommendations and relevance in ["high", "medium"]:
            recommendations.append({
                "action": "watch",
                "condition": "Monitoreo continuo",
                "reason": f"Noticias de relevancia {relevance} detectadas. Monitorear evolución.",
                "threshold": None,
                "confidence": confidence,
                "priority": 1
            })
        
        # Ordenar por prioridad
        recommendations.sort(key=lambda r: r["priority"], reverse=True)
        
        return recommendations
    
    def _format_condition(self, rule: TradingRule, market_features: Dict) -> str:
        """Formatea la condición de la regla de forma legible."""
        if rule.condition_type == "price_below_threshold":
            threshold = rule.threshold or TRADING_RULES_DEFAULT_PRICE_THRESHOLD_PCT
            return f"Precio cae >{threshold}%"
        elif rule.condition_type == "price_above_threshold":
            threshold = rule.threshold or TRADING_RULES_DEFAULT_PRICE_THRESHOLD_PCT
            return f"Precio sube >{threshold}%"
        elif rule.condition_type == "sentiment_negative":
            return "Sentimiento negativo"
        elif rule.condition_type == "sentiment_positive":
            return "Sentimiento positivo"
        elif rule.condition_type == "volume_spike":
            threshold = rule.threshold or TRADING_RULES_DEFAULT_VOLUME_MULTIPLIER
            return f"Volumen >{threshold}x promedio"
        elif rule.condition_type == "combined_negative":
            return "Sentimiento negativo + caída de precio"
        elif rule.condition_type == "combined_positive":
            return "Sentimiento positivo + subida de precio"
        else:
            return rule.description or rule.condition_type
    
    def _get_threshold_info(self, rule: TradingRule, market_features: Dict) -> Dict:
        """Obtiene información de umbrales para la recomendación."""
        threshold_info = {
            "type": rule.condition_type,
            "value": rule.threshold
        }
        
        # Agregar valores actuales si están disponibles
        if rule.condition_type in ["price_below_threshold", "price_above_threshold", "combined_negative", "combined_positive"]:
            threshold_info["current_price_change"] = market_features.get("intraday_change_pct")
        
        if rule.condition_type == "volume_spike":
            threshold_info["current_volume_ratio"] = market_features.get("volume_ratio")
        
        return threshold_info

