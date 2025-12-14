"""Cargador de diccionarios para NLP local."""
import logging
import json
from typing import Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class DictionaryLoader:
    """Cargador centralizado de diccionarios."""
    
    def __init__(self):
        """Inicializa el cargador."""
        self.config_dir = Path(__file__).parent.parent.parent / "nlp_config"
        self._dictionaries: Dict[str, Dict[str, Any]] = {}
    
    def load_dictionary(self, filename: str) -> Dict[str, Any]:
        """
        Carga un diccionario desde un archivo JSON.
        
        Args:
            filename: Nombre del archivo (ej: "sentiment_dict.json")
        
        Returns:
            Diccionario cargado o diccionario vacío si hay error
        """
        if filename in self._dictionaries:
            return self._dictionaries[filename]
        
        try:
            file_path = self.config_dir / filename
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    dictionary = json.load(f)
                self._dictionaries[filename] = dictionary
                logger.info(f"Diccionario cargado: {filename}")
                return dictionary
            else:
                logger.warning(f"Archivo de diccionario no encontrado: {file_path}")
                return {}
        except Exception as e:
            logger.error(f"Error cargando diccionario {filename}: {e}")
            return {}
    
    def reload_dictionary(self, filename: str) -> Dict[str, Any]:
        """
        Recarga un diccionario desde disco.
        
        Args:
            filename: Nombre del archivo
        
        Returns:
            Diccionario recargado
        """
        if filename in self._dictionaries:
            del self._dictionaries[filename]
        return self.load_dictionary(filename)
    
    def get_dictionary_version(self, filename: str) -> Optional[str]:
        """
        Obtiene la versión de un diccionario.
        
        Args:
            filename: Nombre del archivo
        
        Returns:
            Versión del diccionario o None
        """
        dictionary = self.load_dictionary(filename)
        return dictionary.get("version")


# Instancia global del cargador
_dictionary_loader_instance: Optional[DictionaryLoader] = None


def get_dictionary_loader() -> DictionaryLoader:
    """Obtiene la instancia global del cargador de diccionarios."""
    global _dictionary_loader_instance
    if _dictionary_loader_instance is None:
        _dictionary_loader_instance = DictionaryLoader()
    return _dictionary_loader_instance
