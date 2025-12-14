"""Servicio para logging y tracking de tokens usados en llamadas a OpenAI."""
import logging
from typing import Dict, Optional, Any
from datetime import datetime, timezone
from dataclasses import dataclass, asdict
import json

logger = logging.getLogger(__name__)


@dataclass
class TokenUsage:
    """Estructura para tracking de tokens."""
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    step_name: str
    timestamp: str
    prompt_type: Optional[str] = None
    estimated_cost: Optional[float] = None  # En USD (aproximado)


class TokenLogger:
    """Servicio para logging de tokens usados."""
    
    # Costos aproximados por 1K tokens (gpt-4o)
    COST_PER_1K_TOKENS = {
        "prompt": 0.0025,  # $2.50 por 1M tokens de entrada
        "completion": 0.010  # $10.00 por 1M tokens de salida
    }
    
    def __init__(self):
        self._usage_history: list[TokenUsage] = []
        self._session_total = {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "estimated_cost": 0.0
        }
    
    def log_usage(
        self,
        prompt_tokens: int,
        completion_tokens: int,
        step_name: str,
        prompt_type: Optional[str] = None,
        response: Optional[Any] = None
    ):
        """
        Registra el uso de tokens para un paso específico.
        
        Args:
            prompt_tokens: Tokens de entrada
            completion_tokens: Tokens de salida
            step_name: Nombre del paso (ej: "scenario_generation", "summary_batch_1")
            prompt_type: Tipo de prompt (opcional)
            response: Respuesta de OpenAI (opcional, para extraer tokens reales)
        """
        # Si hay respuesta, intentar extraer tokens reales
        if response and hasattr(response, 'usage'):
            usage = response.usage
            prompt_tokens = usage.prompt_tokens
            completion_tokens = usage.completion_tokens
        
        total_tokens = prompt_tokens + completion_tokens
        
        # Calcular costo estimado
        cost = (
            (prompt_tokens / 1000) * self.COST_PER_1K_TOKENS["prompt"] +
            (completion_tokens / 1000) * self.COST_PER_1K_TOKENS["completion"]
        )
        
        usage = TokenUsage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            step_name=step_name,
            timestamp=datetime.now(timezone.utc).isoformat(),
            prompt_type=prompt_type,
            estimated_cost=cost
        )
        
        self._usage_history.append(usage)
        
        # Actualizar totales de sesión
        self._session_total["prompt_tokens"] += prompt_tokens
        self._session_total["completion_tokens"] += completion_tokens
        self._session_total["total_tokens"] += total_tokens
        self._session_total["estimated_cost"] += cost
        
        # Log detallado
        logger.info(
            f"[TOKENS] {step_name} | "
            f"Prompt: {prompt_tokens}, Completion: {completion_tokens}, "
            f"Total: {total_tokens} | Costo: ${cost:.4f}"
        )
    
    def get_step_summary(self, step_name: str) -> Dict:
        """Obtiene resumen de tokens para un paso específico."""
        step_usages = [u for u in self._usage_history if u.step_name == step_name]
        
        if not step_usages:
            return {
                "step_name": step_name,
                "calls": 0,
                "total_tokens": 0,
                "total_cost": 0.0
            }
        
        total_tokens = sum(u.total_tokens for u in step_usages)
        total_cost = sum(u.estimated_cost for u in step_usages)
        
        return {
            "step_name": step_name,
            "calls": len(step_usages),
            "prompt_tokens": sum(u.prompt_tokens for u in step_usages),
            "completion_tokens": sum(u.completion_tokens for u in step_usages),
            "total_tokens": total_tokens,
            "total_cost": total_cost
        }
    
    def get_session_summary(self) -> Dict:
        """Obtiene resumen de tokens de la sesión actual."""
        return {
            **self._session_total,
            "total_calls": len(self._usage_history),
            "breakdown": {
                step: self.get_step_summary(step)
                for step in set(u.step_name for u in self._usage_history)
            }
        }
    
    def print_summary(self):
        """Imprime un resumen de tokens en el log."""
        summary = self.get_session_summary()
        logger.info("=" * 60)
        logger.info("RESUMEN DE TOKENS - SESIÓN ACTUAL")
        logger.info("=" * 60)
        logger.info(f"Total de llamadas: {summary['total_calls']}")
        logger.info(f"Tokens de entrada: {summary['prompt_tokens']:,}")
        logger.info(f"Tokens de salida: {summary['completion_tokens']:,}")
        logger.info(f"Total de tokens: {summary['total_tokens']:,}")
        logger.info(f"Costo estimado: ${summary['estimated_cost']:.4f}")
        logger.info("\nDesglose por paso:")
        for step, step_summary in summary["breakdown"].items():
            logger.info(
                f"  {step}: {step_summary['calls']} llamadas, "
                f"{step_summary['total_tokens']:,} tokens, "
                f"${step_summary['total_cost']:.4f}"
            )
        logger.info("=" * 60)
    
    def reset_session(self):
        """Reinicia las estadísticas de la sesión."""
        self._usage_history.clear()
        self._session_total = {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "estimated_cost": 0.0
        }
        logger.info("Estadísticas de tokens reiniciadas")


# Instancia global del logger
token_logger = TokenLogger()
