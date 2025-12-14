"""Servicio centralizado para optimización de prompts y control de flujo."""
import logging
from typing import Dict, Optional, Tuple, Any
from app.services.prompt_template_service import PromptTemplateService
from app.services.prompt_cache_service import PromptCacheService, CACHE_TTL
from app.services.token_logger import token_logger

logger = logging.getLogger(__name__)


class PromptOptimizationService:
    """Servicio centralizado para optimizar prompts y evitar llamadas redundantes."""
    
    def __init__(self):
        self.template_service = PromptTemplateService()
        self.cache_service = PromptCacheService()
    
    def should_make_api_call(
        self,
        prompt_type: str,
        static_data: Dict,
        variable_data: Dict = None,
        min_data_required: int = 1
    ) -> Tuple[bool, Optional[str], Optional[Any]]:
        """
        Determina si se debe hacer una llamada a la API o usar caché.
        
        Args:
            prompt_type: Tipo de prompt
            static_data: Datos estáticos
            variable_data: Datos variables
            min_data_required: Mínimo de datos requeridos (ej: mínimo de noticias)
        
        Returns:
            Tuple (should_call, reason, cached_response)
            - should_call: True si se debe llamar a la API
            - reason: Razón por la que no se debe llamar (si should_call=False)
            - cached_response: Respuesta cacheada (si existe)
        """
        # 1. Verificar datos mínimos
        if variable_data:
            data_count = self._count_data_items(prompt_type, variable_data)
            if data_count < min_data_required:
                return (False, f"Datos insuficientes: {data_count} < {min_data_required}", None)
        
        # 2. Verificar caché
        cached_response = self.cache_service.get(
            prompt_type=prompt_type,
            static_data=static_data,
            variable_data=variable_data,
            cache_ttl=CACHE_TTL.get(prompt_type, CACHE_TTL["static"])
        )
        
        if cached_response:
            logger.info(f"Usando respuesta cacheada para {prompt_type}")
            return (False, "Respuesta disponible en caché", cached_response)
        
        # 3. Validar prompt antes de construir (estimación temprana)
        if variable_data:
            prompt_data = self.template_service.build_optimized_prompt(
                template_type=prompt_type,
                variable_data=variable_data
            )
            
            if not prompt_data.get("is_valid", True):
                return (
                    False,
                    f"Prompt inválido: {prompt_data.get('char_count', 0)} chars, "
                    f"{prompt_data.get('estimated_tokens', 0)} tokens estimados",
                    None
                )
        
        return (True, None, None)
    
    def _count_data_items(self, prompt_type: str, variable_data: Dict) -> int:
        """Cuenta los items de datos relevantes según el tipo de prompt."""
        if prompt_type == "situation_summary":
            return len(variable_data.get("news_items", []))
        elif prompt_type == "scenario_generation":
            return len(variable_data.get("related_news_items", []))
        elif prompt_type == "technical_analysis":
            return len(variable_data.get("price_points", []))
        return 0
    
    def log_api_call(
        self,
        prompt_type: str,
        step_name: str,
        response: Any,
        cache_key: Optional[str] = None
    ):
        """
        Registra una llamada a la API y opcionalmente cachea la respuesta.
        
        Args:
            prompt_type: Tipo de prompt
            step_name: Nombre del paso
            response: Respuesta de OpenAI
            cache_key: Clave de caché (opcional, para cachear después)
        """
        if response and hasattr(response, 'usage') and response.usage:
            token_logger.log_usage(
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
                step_name=step_name,
                prompt_type=prompt_type,
                response=response
            )
    
    def cache_response(
        self,
        prompt_type: str,
        static_data: Dict,
        response: Any,
        variable_data: Dict = None,
        token_count: int = None
    ) -> str:
        """
        Cachea una respuesta.
        
        Args:
            prompt_type: Tipo de prompt
            static_data: Datos estáticos
            response: Respuesta a cachear
            variable_data: Datos variables
            token_count: Número de tokens usados
        
        Returns:
            Clave de caché generada
        """
        return self.cache_service.set(
            prompt_type=prompt_type,
            static_data=static_data,
            response=response,
            variable_data=variable_data,
            token_count=token_count,
            cache_ttl=CACHE_TTL.get(prompt_type, CACHE_TTL["static"])
        )
