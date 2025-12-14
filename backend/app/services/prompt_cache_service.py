"""Servicio para cachear respuestas de prompts y evitar re-llamadas redundantes."""
import logging
import hashlib
import json
from typing import Dict, Optional, Any
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

# Tiempo de expiración del caché (en segundos)
CACHE_TTL = {
    "static": 3600 * 24,  # 24 horas para respuestas estáticas
    "dynamic": 300,       # 5 minutos para datos dinámicos (precios, indicadores)
    "scenarios": 1800,    # 30 minutos para escenarios
    "summary": 600        # 10 minutos para resúmenes
}


@dataclass
class CachedResponse:
    """Estructura para respuestas cacheadas."""
    key: str
    response: Any
    created_at: str
    expires_at: str
    token_count: Optional[int] = None
    prompt_hash: Optional[str] = None
    data_hash: Optional[str] = None  # Hash de los datos variables


class PromptCacheService:
    """Servicio para gestionar caché de respuestas de prompts."""
    
    def __init__(self):
        self._cache: Dict[str, CachedResponse] = {}
        self._cache_stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0
        }
    
    def _generate_cache_key(
        self,
        prompt_type: str,
        static_data: Dict,
        variable_data: Dict = None
    ) -> str:
        """
        Genera una clave de caché basada en el tipo y datos estáticos.
        
        Args:
            prompt_type: Tipo de prompt
            static_data: Datos estáticos (instrucciones, contexto)
            variable_data: Datos variables (opcional, para invalidación)
        
        Returns:
            Clave de caché (hash)
        """
        # Solo usar datos estáticos para la clave principal
        key_data = {
            "type": prompt_type,
            "static": static_data
        }
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def _generate_data_hash(self, variable_data: Dict) -> str:
        """Genera hash de datos variables para detectar cambios."""
        if not variable_data:
            return ""
        key_str = json.dumps(variable_data, sort_keys=True)
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def get(
        self,
        prompt_type: str,
        static_data: Dict,
        variable_data: Dict = None,
        cache_ttl: int = None
    ) -> Optional[Any]:
        """
        Obtiene una respuesta del caché si existe y no ha expirado.
        
        Args:
            prompt_type: Tipo de prompt
            static_data: Datos estáticos
            variable_data: Datos variables (para validar si cambió)
            cache_ttl: Tiempo de vida del caché en segundos
        
        Returns:
            Respuesta cacheada o None si no existe/expirada
        """
        cache_key = self._generate_cache_key(prompt_type, static_data)
        cached = self._cache.get(cache_key)
        
        if not cached:
            self._cache_stats["misses"] += 1
            return None
        
        # Verificar expiración
        expires_at = datetime.fromisoformat(cached.expires_at)
        if datetime.now(timezone.utc) > expires_at:
            logger.debug(f"Cache expirado para {prompt_type}: {cache_key}")
            del self._cache[cache_key]
            self._cache_stats["evictions"] += 1
            self._cache_stats["misses"] += 1
            return None
        
        # Si hay datos variables, verificar que no hayan cambiado
        if variable_data:
            current_data_hash = self._generate_data_hash(variable_data)
            if cached.data_hash != current_data_hash:
                logger.debug(f"Datos variables cambiaron para {prompt_type}: {cache_key}")
                self._cache_stats["misses"] += 1
                return None
        
        self._cache_stats["hits"] += 1
        logger.debug(f"Cache hit para {prompt_type}: {cache_key}")
        return cached.response
    
    def set(
        self,
        prompt_type: str,
        static_data: Dict,
        response: Any,
        variable_data: Dict = None,
        token_count: int = None,
        cache_ttl: int = None
    ) -> str:
        """
        Almacena una respuesta en el caché.
        
        Args:
            prompt_type: Tipo de prompt
            static_data: Datos estáticos
            response: Respuesta a cachear
            variable_data: Datos variables (opcional)
            token_count: Número de tokens usados
            cache_ttl: Tiempo de vida del caché en segundos
        
        Returns:
            Clave de caché generada
        """
        cache_key = self._generate_cache_key(prompt_type, static_data)
        cache_ttl = cache_ttl or CACHE_TTL.get(prompt_type, CACHE_TTL["static"])
        
        created_at = datetime.now(timezone.utc)
        expires_at = created_at + timedelta(seconds=cache_ttl)
        
        cached_response = CachedResponse(
            key=cache_key,
            response=response,
            created_at=created_at.isoformat(),
            expires_at=expires_at.isoformat(),
            token_count=token_count,
            data_hash=self._generate_data_hash(variable_data) if variable_data else None
        )
        
        self._cache[cache_key] = cached_response
        logger.debug(f"Cache set para {prompt_type}: {cache_key}, expira en {cache_ttl}s")
        
        return cache_key
    
    def invalidate(self, prompt_type: str = None, cache_key: str = None):
        """
        Invalida entradas del caché.
        
        Args:
            prompt_type: Tipo de prompt a invalidar (invalida todos de ese tipo)
            cache_key: Clave específica a invalidar
        """
        if cache_key:
            if cache_key in self._cache:
                del self._cache[cache_key]
                logger.debug(f"Cache invalidado: {cache_key}")
        elif prompt_type:
            keys_to_remove = [
                key for key, cached in self._cache.items()
                if cached.key.startswith(prompt_type)
            ]
            for key in keys_to_remove:
                del self._cache[key]
            logger.debug(f"Cache invalidado para tipo: {prompt_type} ({len(keys_to_remove)} entradas)")
    
    def clear_expired(self):
        """Limpia entradas expiradas del caché."""
        now = datetime.now(timezone.utc)
        keys_to_remove = []
        
        for key, cached in self._cache.items():
            expires_at = datetime.fromisoformat(cached.expires_at)
            if now > expires_at:
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            del self._cache[key]
            self._cache_stats["evictions"] += 1
        
        if keys_to_remove:
            logger.info(f"Limpiadas {len(keys_to_remove)} entradas expiradas del caché")
    
    def get_stats(self) -> Dict:
        """Obtiene estadísticas del caché."""
        total = self._cache_stats["hits"] + self._cache_stats["misses"]
        hit_rate = (self._cache_stats["hits"] / total * 100) if total > 0 else 0
        
        return {
            "cache_size": len(self._cache),
            "hits": self._cache_stats["hits"],
            "misses": self._cache_stats["misses"],
            "evictions": self._cache_stats["evictions"],
            "hit_rate": f"{hit_rate:.2f}%"
        }
