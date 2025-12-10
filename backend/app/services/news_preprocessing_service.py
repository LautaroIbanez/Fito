"""Servicio para preprocesar y estandarizar noticias usando OpenAI."""
import logging
import json
from typing import Dict
from openai import OpenAI
from app.config import (
    OPENAI_API_KEY,
    OPENAI_MODEL,
    OPENAI_TEMPERATURE,
    STANDARDIZED_NEWS_MAX_BULLET_LENGTH,
    STANDARDIZED_NEWS_MIN_BULLETS,
    STANDARDIZED_NEWS_MAX_BULLETS,
    STANDARDIZED_NEWS_SENTIMENT_ENUM
)
from app.models import StandardizedNewsData

logger = logging.getLogger(__name__)


class NewsPreprocessingService:
    """Servicio para preprocesar y estandarizar noticias."""
    
    def __init__(self):
        """Inicializa el cliente de OpenAI."""
        if not OPENAI_API_KEY or OPENAI_API_KEY == "your_openai_api_key_here":
            raise ValueError("OPENAI_API_KEY no está configurada correctamente en app/config.py")
        
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        self.model = OPENAI_MODEL
        self.temperature = OPENAI_TEMPERATURE
    
    def standardize_news(self, article_text: str) -> StandardizedNewsData:
        """
        Estandariza una noticia usando OpenAI para extraer campos estructurados.
        
        Args:
            article_text: Texto completo del artículo
            
        Returns:
            StandardizedNewsData: Datos estandarizados de la noticia
        """
        try:
            prompt = self._build_standardization_prompt(article_text)
            
            logger.info(f"Estandarizando noticia con modelo {self.model}")
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Eres un asistente experto en análisis de noticias financieras. "
                            "Tu tarea es extraer información estructurada de artículos de noticias "
                            "y presentarla en formato JSON estricto. "
                            "Sé preciso y conciso. Cada bullet point del resumen debe tener máximo "
                            f"{STANDARDIZED_NEWS_MAX_BULLET_LENGTH} palabras."
                        )
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=self.temperature,
                response_format={"type": "json_object"},
                timeout=60.0
            )
            
            response_text = response.choices[0].message.content
            standardized_dict = json.loads(response_text)
            
            # Validar y limpiar los datos
            standardized_data = self._validate_and_clean_standardized_data(standardized_dict)
            
            logger.info(f"Noticia estandarizada exitosamente")
            return standardized_data
            
        except json.JSONDecodeError as e:
            logger.error(f"Error parseando JSON de respuesta de OpenAI: {e}")
            raise ValueError(f"Error procesando respuesta de OpenAI: formato JSON inválido")
        except Exception as e:
            error_str = str(e)
            logger.error(f"Error estandarizando noticia con OpenAI: {e}", exc_info=True)
            
            if "401" in error_str or "invalid_api_key" in error_str:
                raise ValueError(
                    "Error de autenticación con OpenAI. Verifica tu API key en app/config.py"
                )
            elif "429" in error_str or "rate_limit" in error_str:
                raise ValueError("Límite de tasa excedido. Por favor, intenta más tarde.")
            elif "insufficient_quota" in error_str:
                raise ValueError("Cuota de OpenAI agotada. Verifica tu cuenta.")
            else:
                raise ValueError(f"Error al estandarizar noticia: {error_str}")
    
    def _build_standardization_prompt(self, article_text: str) -> str:
        """Construye el prompt para estandarización."""
        return f"""Analiza el siguiente artículo de noticias y extrae la información estructurada solicitada.

ARTÍCULO:
{article_text}

INSTRUCCIONES:
Extrae la siguiente información y devuélvela en formato JSON estricto con las siguientes claves:

1. "title": Título del artículo (string, requerido)
2. "publication_date": Fecha de publicación en formato ISO (string, opcional, null si no se encuentra)
3. "source": Fuente/publicación del artículo (string, opcional, null si no se encuentra)
4. "summary_bullets": Array de 3-5 bullets de resumen (cada uno máximo {STANDARDIZED_NEWS_MAX_BULLET_LENGTH} palabras)
5. "key_people_companies": Array de nombres de personas y empresas clave mencionadas (puede estar vacío)
6. "quoted_numbers_metrics": Array de números y métricas citadas (ej: "$1.5B", "15% growth", "Q2 earnings", puede estar vacío)
7. "sentiment": Sentimiento del artículo: uno de ["bullish", "bearish", "neutral"] (string, requerido)
8. "why_it_matters": Una línea explicando por qué esta noticia importa desde la perspectiva de un inversor (string, requerido, máximo 100 palabras)

REGLAS IMPORTANTES:
- El sentimiento debe ser exactamente uno de: {', '.join(STANDARDIZED_NEWS_SENTIMENT_ENUM)}
- Cada bullet en summary_bullets debe tener máximo {STANDARDIZED_NEWS_MAX_BULLET_LENGTH} palabras
- Debes proporcionar entre {STANDARDIZED_NEWS_MIN_BULLETS} y {STANDARDIZED_NEWS_MAX_BULLETS} bullets
- "why_it_matters" debe ser conciso y enfocado en implicaciones para inversores
- Si no encuentras información para un campo opcional, usa null

Responde SOLO con el JSON, sin texto adicional."""
    
    def _validate_and_clean_standardized_data(self, data: Dict) -> StandardizedNewsData:
        """
        Valida y limpia los datos estandarizados.
        Asegura que cumplan con los requisitos del modelo.
        """
        # Validar campos requeridos
        if "title" not in data or not data["title"]:
            raise ValueError("El título es requerido y no puede estar vacío")
        
        if "sentiment" not in data:
            raise ValueError("El sentimiento es requerido")
        
        if "summary_bullets" not in data or not isinstance(data["summary_bullets"], list):
            raise ValueError("summary_bullets debe ser un array")
        
        if "why_it_matters" not in data or not data["why_it_matters"]:
            raise ValueError("why_it_matters es requerido y no puede estar vacío")
        
        # Limpiar y validar bullets
        bullets = data["summary_bullets"]
        cleaned_bullets = []
        for bullet in bullets:
            if isinstance(bullet, str) and bullet.strip():
                # Truncar si excede el límite de palabras
                words = bullet.strip().split()
                if len(words) > STANDARDIZED_NEWS_MAX_BULLET_LENGTH:
                    words = words[:STANDARDIZED_NEWS_MAX_BULLET_LENGTH]
                    cleaned_bullet = " ".join(words)
                    logger.warning(f"Bullet truncado a {STANDARDIZED_NEWS_MAX_BULLET_LENGTH} palabras")
                else:
                    cleaned_bullet = bullet.strip()
                cleaned_bullets.append(cleaned_bullet)
        
        # Validar cantidad de bullets
        if len(cleaned_bullets) < STANDARDIZED_NEWS_MIN_BULLETS:
            raise ValueError(f"Se requieren al menos {STANDARDIZED_NEWS_MIN_BULLETS} bullets, se encontraron {len(cleaned_bullets)}")
        if len(cleaned_bullets) > STANDARDIZED_NEWS_MAX_BULLETS:
            cleaned_bullets = cleaned_bullets[:STANDARDIZED_NEWS_MAX_BULLETS]
            logger.warning(f"Se truncaron bullets a {STANDARDIZED_NEWS_MAX_BULLETS}")
        
        # Limpiar arrays opcionales
        key_people_companies = data.get("key_people_companies", [])
        if not isinstance(key_people_companies, list):
            key_people_companies = []
        
        quoted_numbers_metrics = data.get("quoted_numbers_metrics", [])
        if not isinstance(quoted_numbers_metrics, list):
            quoted_numbers_metrics = []
        
        # Validar sentimiento
        sentiment = data["sentiment"].lower()
        if sentiment not in [s.lower() for s in STANDARDIZED_NEWS_SENTIMENT_ENUM]:
            raise ValueError(f"Sentimiento inválido: {sentiment}. Debe ser uno de {STANDARDIZED_NEWS_SENTIMENT_ENUM}")
        
        # Truncar why_it_matters si es muy largo
        why_it_matters = data["why_it_matters"].strip()
        words = why_it_matters.split()
        if len(words) > 100:
            words = words[:100]
            why_it_matters = " ".join(words)
            logger.warning("why_it_matters truncado a 100 palabras")
        
        return StandardizedNewsData(
            title=data["title"].strip(),
            publication_date=data.get("publication_date"),
            source=data.get("source"),
            summary_bullets=cleaned_bullets,
            key_people_companies=[str(item).strip() for item in key_people_companies if item],
            quoted_numbers_metrics=[str(item).strip() for item in quoted_numbers_metrics if item],
            sentiment=sentiment,
            why_it_matters=why_it_matters
        )


