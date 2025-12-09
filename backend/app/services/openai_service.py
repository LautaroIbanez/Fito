"""Servicio para interactuar con OpenAI API."""
import logging
from typing import Dict, List, Tuple
from openai import OpenAI
from app.config import (
    OPENAI_API_KEY,
    OPENAI_MODEL,
    OPENAI_TEMPERATURE,
    OPENAI_MAX_TOKENS,
    NEWS_STALE_DAYS,
    MAX_SECTION_LENGTH,
    MIN_RECOMMENDATION_EVIDENCE
)
from app.models import NewsItemResponse, PortfolioItemResponse
from datetime import datetime, timedelta, timezone

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
        self.stale_days = NEWS_STALE_DAYS
        self.max_section_length = MAX_SECTION_LENGTH
        self.min_recommendation_evidence = MIN_RECOMMENDATION_EVIDENCE
    
    def _is_news_stale(self, news_date_str: str) -> Tuple[bool, int]:
        """
        Determina si una noticia es "stale" (desactualizada) y retorna
        la cantidad de días de antigüedad.
        
        Returns:
            Tuple[bool, int]: (es_stale, días_antigüedad)
        """
        try:
            # Parsear fecha ISO
            if 'T' in news_date_str:
                news_date = datetime.fromisoformat(news_date_str.replace('Z', '+00:00'))
            else:
                news_date = datetime.fromisoformat(news_date_str)
            
            # Asegurar timezone-aware
            if news_date.tzinfo is None:
                news_date = news_date.replace(tzinfo=timezone.utc)
            
            now = datetime.now(timezone.utc)
            age_days = (now - news_date).days
            
            is_stale = age_days > self.stale_days
            return is_stale, age_days
            
        except (ValueError, AttributeError) as e:
            logger.warning(f"Error parseando fecha de noticia '{news_date_str}': {e}")
            # Si no se puede parsear, asumir que es fresca
            return False, 0
    
    def _format_portfolio_snapshot(self, portfolio_items: List[PortfolioItemResponse]) -> str:
        """Formatea el snapshot de la cartera con todos los detalles relevantes."""
        if not portfolio_items:
            return ""
        
        lines = [
            "SNAPSHOT DE CARTERA ACTUAL",
            "=" * 60,
            f"Fecha de snapshot: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}",
            f"Total de activos: {len(portfolio_items)}",
            "",
        ]
        
        # Agrupar por tipo de activo
        by_type = {}
        for item in portfolio_items:
            if item.asset_type not in by_type:
                by_type[item.asset_type] = []
            by_type[item.asset_type].append(item)
        
        # Calcular pesos aproximados si hay valores totales
        total_portfolio_value = 0
        for items in by_type.values():
            for item in items:
                if item.total_value:
                    try:
                        # Intentar parsear valor numérico
                        value_str = item.total_value.replace(',', '').strip()
                        total_portfolio_value += float(value_str)
                    except (ValueError, AttributeError):
                        pass
        
        # Formatear por tipo
        for asset_type, items in sorted(by_type.items()):
            lines.append(f"\n{asset_type.upper()} ({len(items)} activo{'s' if len(items) != 1 else ''}):")
            lines.append("-" * 40)
            
            for item in items:
                item_lines = [f"  • {item.name}"]
                
                if item.symbol:
                    item_lines.append(f"    Símbolo: {item.symbol}")
                
                if item.total_value:
                    item_lines.append(f"    Valor Total: {item.total_value} {item.currency or 'USD'}")
                    
                    # Calcular peso si es posible
                    if total_portfolio_value > 0:
                        try:
                            value_str = item.total_value.replace(',', '').strip()
                            item_value = float(value_str)
                            weight_pct = (item_value / total_portfolio_value) * 100
                            item_lines.append(f"    Peso Aprox: {weight_pct:.2f}%")
                        except (ValueError, AttributeError):
                            pass
                
                if item.quantity:
                    item_lines.append(f"    Cantidad: {item.quantity}")
                
                if item.price:
                    item_lines.append(f"    Precio Unitario: {item.price} {item.currency or 'USD'}")
                
                # Fechas de creación y última actualización
                if item.created_at:
                    item_lines.append(f"    Agregado: {item.created_at}")
                if item.updated_at and item.updated_at != item.created_at:
                    item_lines.append(f"    Última Actualización: {item.updated_at}")
                
                if item.notes:
                    item_lines.append(f"    Notas: {item.notes}")
                
                lines.append("\n".join(item_lines))
                lines.append("")
        
        return "\n".join(lines)
    
    def _format_news_list(self, news_items: List[NewsItemResponse]) -> Tuple[str, int, int]:
        """
        Formatea la lista de noticias clasificándolas como frescas o stale.
        
        Returns:
            Tuple[str, int, int]: (prompt_text, fresh_count, stale_count)
        """
        lines = [
            "LISTADO DE NOTICIAS",
            "=" * 60,
            f"Fecha de análisis: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}",
            f"Noticias cargadas: {len(news_items)}",
            "",
        ]
        
        fresh_news = []
        stale_news = []
        
        for item in news_items:
            is_stale, age_days = self._is_news_stale(item.created_at)
            if is_stale:
                stale_news.append((item, age_days))
            else:
                fresh_news.append((item, age_days))
        
        # Ordenar: frescas primero (más recientes), luego stale
        fresh_news.sort(key=lambda x: x[1])  # Por antigüedad ascendente
        stale_news.sort(key=lambda x: x[1], reverse=True)  # Por antigüedad descendente
        
        # Sección de noticias frescas
        if fresh_news:
            lines.append("📰 NOTICIAS FRESCAS (Relevancia Alta):")
            lines.append("-" * 40)
            for idx, (item, age_days) in enumerate(fresh_news, 1):
                lines.append(f"\n{idx}. {item.title or 'Sin título'}")
                if item.source:
                    lines.append(f"   Fuente: {item.source}")
                lines.append(f"   Fecha de carga: {item.created_at}")
                lines.append(f"   Antigüedad: {age_days} día{'s' if age_days != 1 else ''}")
                lines.append(f"   Contenido: {item.body[:600]}...")  # Primeros 600 caracteres
                lines.append("")
        else:
            lines.append("⚠️ No hay noticias frescas en el sistema.")
            lines.append("")
        
        # Sección de noticias desactualizadas
        if stale_news:
            lines.append("⚠️ NOTICIAS DESACTUALIZADAS (Relevancia Débil):")
            lines.append("-" * 40)
            lines.append(f"ADVERTENCIA: Las siguientes {len(stale_news)} noticias tienen más de {self.stale_days} días de antigüedad.")
            lines.append("Trátalas como CONTEXTO HISTÓRICO, no como información actual.")
            lines.append("")
            
            for idx, (item, age_days) in enumerate(stale_news, 1):
                lines.append(f"{idx}. {item.title or 'Sin título'}")
                if item.source:
                    lines.append(f"   Fuente: {item.source}")
                lines.append(f"   Fecha de carga: {item.created_at}")
                lines.append(f"   Antigüedad: {age_days} días ⚠️ DESACTUALIZADA")
                lines.append(f"   Contenido (contexto histórico): {item.body[:400]}...")
                lines.append("")
        
        prompt_text = "\n".join(lines)
        return prompt_text, len(fresh_news), len(stale_news)
    
    def build_prompt(
        self, 
        news_items: List[NewsItemResponse],
        portfolio_items: List[PortfolioItemResponse] = None
    ) -> str:
        """
        Construye el prompt para OpenAI con snapshot de cartera y noticias clasificadas.
        """
        prompt_parts = [
            "Eres un analista financiero experto. Analiza el contexto proporcionado y genera recomendaciones específicas y accionables.\n",
            "IMPORTANTE: No inventes correlaciones que no sean evidentes. Si no hay relación clara entre las noticias y los activos, indícalo claramente.\n\n"
        ]
        
        # 1. Snapshot de cartera
        if portfolio_items:
            prompt_parts.append(self._format_portfolio_snapshot(portfolio_items))
            prompt_parts.append("\n" + "=" * 60 + "\n\n")
        else:
            prompt_parts.append("CARTERA: No hay activos registrados en la cartera.\n")
            prompt_parts.append("=" * 60 + "\n\n")
        
        # 2. Listado de noticias con clasificación
        news_text, fresh_count, stale_count = self._format_news_list(news_items)
        prompt_parts.append(news_text)
        prompt_parts.append("\n" + "=" * 60 + "\n\n")
        
        # 3. Instrucciones específicas de análisis
        prompt_parts.append("INSTRUCCIONES PARA EL ANÁLISIS:\n")
        prompt_parts.append("=" * 60 + "\n\n")
        
        prompt_parts.append("1. CONTEXTO DE NOTICIAS:\n")
        prompt_parts.append(f"   - Noticias frescas ({fresh_count}): Úsalas como información ACTUAL y RELEVANTE.\n")
        if stale_count > 0:
            prompt_parts.append(f"   - Noticias desactualizadas ({stale_count}): Úsalas SOLO como contexto histórico.\n")
            prompt_parts.append("     NO fuerces vínculos entre noticias antiguas y la cartera actual.\n")
            prompt_parts.append("     Si una noticia desactualizada es irrelevante para decisiones actuales, indícalo.\n")
        prompt_parts.append("\n")
        
        prompt_parts.append("2. ANÁLISIS DE CARTERA:\n")
        if portfolio_items:
            prompt_parts.append("   - Revisa cada activo en la cartera considerando las noticias frescas.\n")
            prompt_parts.append("   - Identifica riesgos y oportunidades específicas para los activos actuales.\n")
        else:
            prompt_parts.append("   - No hay cartera actual, enfócate en recomendaciones generales basadas en noticias.\n")
        prompt_parts.append("\n")
        
        prompt_parts.append("3. REGLAS CRÍTICAS DE FORMATO:\n")
        prompt_parts.append("   ❌ NO inventes correlaciones entre noticias y activos si no son evidentes.\n")
        prompt_parts.append("   ❌ NO fuerces relaciones entre noticias desactualizadas y decisiones actuales.\n")
        prompt_parts.append("   ❌ NO generes relleno hipotético o especulativo sin respaldo claro en noticias.\n")
        prompt_parts.append("   ✅ Si una noticia NO tiene relación clara con un activo, di: 'Sin relación evidente'.\n")
        prompt_parts.append("   ✅ Prioriza noticias frescas sobre desactualizadas para recomendaciones.\n")
        prompt_parts.append("   ✅ Sé honesto si no hay suficiente información para una recomendación.\n")
        prompt_parts.append("   ✅ MANTÉN RESPUESTAS CONCISAS: máximo 300 caracteres por sección.\n")
        prompt_parts.append("   ✅ Si no hay señales claras, di 'Sin recomendaciones' en lugar de inventar.\n")
        prompt_parts.append("\n")
        
        # Contar noticias frescas para validación
        _, fresh_count, _ = self._format_news_list(news_items)
        can_suggest_new = fresh_count >= self.min_recommendation_evidence
        
        prompt_parts.append("4. ESTRUCTURA MINIMALISTA DEL ANÁLISIS (MÁXIMO 300 CARACTERES POR SECCIÓN):\n")
        prompt_parts.append("\n")
        prompt_parts.append("1. IMPACTO EN CARTERA (RESUMEN CORTO):\n")
        prompt_parts.append("   - 2-3 oraciones máximo sobre el impacto potencial en la cartera actual.\n")
        prompt_parts.append("   - Si no hay impacto claro, escribe: 'Impacto limitado o no evidente'.\n")
        prompt_parts.append("\n")
        
        if portfolio_items:
            prompt_parts.append("2. ACCIONES RECOMENDADAS (MANTENER/AJUSTAR):\n")
            prompt_parts.append("   - Lista concisa de activos a: MANTENER, REDUCIR, o AUMENTAR.\n")
            prompt_parts.append("   - Una línea por activo con justificación breve basada en noticias frescas.\n")
            prompt_parts.append("   - Si no hay acciones claras, escribe: 'Mantener posición actual'.\n")
            prompt_parts.append("\n")
        else:
            prompt_parts.append("2. ACCIONES RECOMENDADAS:\n")
            prompt_parts.append("   - Lista concisa de acciones sugeridas basadas en noticias frescas.\n")
            prompt_parts.append("   - Si no hay acciones claras, escribe: 'Sin recomendaciones específicas'.\n")
            prompt_parts.append("\n")
        
        if can_suggest_new:
            prompt_parts.append("3. NUEVOS ACTIVOS (SOLO SI HAY SEÑALES CLARAS):\n")
            prompt_parts.append(f"   - Solo sugiere nuevos activos si hay al menos {self.min_recommendation_evidence} noticia(s) fresca(s) con señales claras.\n")
            prompt_parts.append("   - Lista concisa: nombre del activo + razón breve basada en noticias.\n")
            prompt_parts.append("   - Si NO hay señales claras, escribe: 'Sin sugerencias de nuevos activos'.\n")
            prompt_parts.append("   - NO inventes activos o razones sin respaldo en noticias frescas.\n")
        else:
            prompt_parts.append("3. NUEVOS ACTIVOS:\n")
            prompt_parts.append(f"   - NO hay suficientes noticias frescas ({fresh_count} < {self.min_recommendation_evidence}) para sugerir nuevos activos.\n")
            prompt_parts.append("   - Responde: 'Sin sugerencias: insuficientes noticias frescas'.\n")
        prompt_parts.append("\n")
        
        prompt_parts.append("IMPORTANTE: Responde SOLO con estas 3 secciones. NO agregues secciones adicionales.\n")
        prompt_parts.append("Mantén cada sección por debajo de 300 caracteres. Evita relleno o especulación.\n")
        
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
            _, fresh_count, stale_count = self._format_news_list(news_items)
            
            logger.info(
                f"Generando análisis: {len(news_items)} noticias ({fresh_count} frescas, {stale_count} stale), "
                f"{portfolio_count} items de cartera, modelo {self.model}"
            )
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Eres un analista financiero experto especializado en análisis de carteras de inversión. "
                            "Proporcionas recomendaciones MINIMALISTAS y CONCISAS basadas exclusivamente en noticias del mercado. "
                            "CRÍTICO: No inventes correlaciones entre noticias y activos si no son evidentes. "
                            "Sé honesto cuando no hay suficiente información o relación clara. "
                            "Prioriza noticias frescas sobre desactualizadas. "
                            "MANTÉN RESPUESTAS CORTAS: máximo 300 caracteres por sección. "
                            "NO generes relleno hipotético o especulativo sin respaldo claro en noticias. "
                            "Si no hay señales claras, di 'Sin recomendaciones' en lugar de inventar. "
                            "Tus recomendaciones deben ser claras, justificadas, prácticas y CONCISAS."
                        )
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
            
            # Parsear y validar el análisis en secciones
            analysis = self._parse_analysis(analysis_text)
            
            # Validar formato con contador de noticias frescas
            validated_sections = self._validate_and_format_response(analysis_text, fresh_count)
            
            # Combinar análisis parseado con validación
            final_analysis = {
                "impacto_cartera": validated_sections.get("impacto_cartera") or analysis.get("impacto_cartera", ""),
                "acciones_recomendadas": validated_sections.get("acciones_recomendadas") or analysis.get("acciones_recomendadas", ""),
                "nuevos_activos": validated_sections.get("nuevos_activos") or analysis.get("nuevos_activos", ""),
                # Mantener campos antiguos para compatibilidad
                "resumen_ejecutivo": analysis.get("resumen_ejecutivo", ""),
                "riesgos_identificados": analysis.get("riesgos_identificados", ""),
                "actores_clave": analysis.get("actores_clave", ""),
                "senales_tempranas": analysis.get("senales_tempranas", ""),
                "recomendaciones_cartera": analysis.get("recomendaciones_cartera", ""),
                "conclusiones_accionables": analysis.get("conclusiones_accionables", "")
            }
            
            return {
                "raw_analysis": analysis_text,
                "structured_analysis": final_analysis,
                "model_used": self.model,
                "tokens_used": response.usage.total_tokens if hasattr(response, 'usage') else None,
                "metadata": {
                    "fresh_news_count": fresh_count,
                    "stale_news_count": stale_count,
                    "portfolio_count": portfolio_count,
                    "format_version": "minimalist_v1"
                }
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
    
    def _truncate_section(self, text: str, max_length: int = None) -> str:
        """
        Trunca una sección de texto al máximo de caracteres permitido.
        Si se trunca, añade '...' al final.
        """
        if max_length is None:
            max_length = self.max_section_length
        
        if len(text) <= max_length:
            return text
        
        # Truncar en el último espacio antes del límite para evitar cortar palabras
        # Si no hay espacios, truncar directamente
        truncate_pos = max_length - 3
        if truncate_pos > 0:
            truncated = text[:truncate_pos].rsplit(' ', 1)[0] if ' ' in text[:truncate_pos] else text[:truncate_pos]
            result = truncated + "..."
            # Asegurar que no exceda el límite
            if len(result) > max_length:
                result = text[:max_length - 3] + "..."
            return result
        else:
            return text[:max_length]
    
    def _validate_and_format_response(self, analysis_text: str, fresh_count: int) -> Dict:
        """
        Valida y formatea la respuesta del análisis para asegurar estructura concisa.
        Limita la longitud de cada sección y valida que no haya relleno hipotético.
        """
        text_lower = analysis_text.lower()
        
        sections = {
            "impacto_cartera": "",
            "acciones_recomendadas": "",
            "nuevos_activos": ""
        }
        
        # Buscar sección 1: Impacto en Cartera
        impact_keywords = ["impacto", "1.", "impacto en cartera", "resumen"]
        impact_start = -1
        for keyword in impact_keywords:
            if keyword in text_lower:
                impact_start = text_lower.find(keyword)
                break
        
        if impact_start >= 0:
            # Buscar inicio de siguiente sección o fin
            next_section_markers = ["2.", "acciones recomendadas", "nuevos activos", "3."]
            impact_end = len(analysis_text)
            for marker in next_section_markers:
                marker_pos = text_lower.find(marker, impact_start + 10)
                if marker_pos > impact_start and marker_pos < impact_end:
                    impact_end = marker_pos
            
            sections["impacto_cartera"] = analysis_text[impact_start:impact_end].strip()
            # Limpiar numeración y títulos
            sections["impacto_cartera"] = sections["impacto_cartera"].split(":", 1)[-1].strip()
            sections["impacto_cartera"] = sections["impacto_cartera"].split("\n", 1)[0] if "\n" in sections["impacto_cartera"] else sections["impacto_cartera"]
        
        # Buscar sección 2: Acciones Recomendadas
        actions_keywords = ["acciones recomendadas", "2.", "mantener", "ajustar", "reducir", "aumentar"]
        actions_start = -1
        for keyword in actions_keywords:
            if keyword in text_lower:
                keyword_pos = text_lower.find(keyword)
                if actions_start < 0 or keyword_pos < actions_start:
                    actions_start = keyword_pos
                break
        
        if actions_start >= 0:
            next_section_markers = ["3.", "nuevos activos", "sugerencias"]
            actions_end = len(analysis_text)
            for marker in next_section_markers:
                marker_pos = text_lower.find(marker, actions_start + 10)
                if marker_pos > actions_start and marker_pos < actions_end:
                    actions_end = marker_pos
            
            sections["acciones_recomendadas"] = analysis_text[actions_start:actions_end].strip()
            sections["acciones_recomendadas"] = sections["acciones_recomendadas"].split(":", 1)[-1].strip()
        
        # Buscar sección 3: Nuevos Activos
        new_assets_keywords = ["nuevos activos", "3.", "sugerencias", "nuevo activo"]
        new_assets_start = -1
        for keyword in new_assets_keywords:
            if keyword in text_lower:
                keyword_pos = text_lower.find(keyword)
                if new_assets_start < 0 or keyword_pos < new_assets_start:
                    new_assets_start = keyword_pos
                break
        
        if new_assets_start >= 0:
            sections["nuevos_activos"] = analysis_text[new_assets_start:].strip()
            sections["nuevos_activos"] = sections["nuevos_activos"].split(":", 1)[-1].strip()
        
        # Validar que no haya sugerencias sin respaldo
        if fresh_count < self.min_recommendation_evidence:
            # Si no hay suficientes noticias frescas, forzar mensaje de "sin sugerencias"
            if sections["nuevos_activos"]:
                new_lower = sections["nuevos_activos"].lower()
                if "sin sugerencias" not in new_lower and "insuficientes" not in new_lower:
                    sections["nuevos_activos"] = "Sin sugerencias: insuficientes noticias frescas para respaldar nuevas recomendaciones."
        
        # Truncar cada sección al máximo permitido
        for key in sections:
            if sections[key]:
                sections[key] = self._truncate_section(sections[key])
        
        # Si no se encontraron secciones, usar el texto completo pero truncado
        if not any(sections.values()):
            sections["impacto_cartera"] = self._truncate_section(analysis_text)
        
        return sections
    
    def _parse_analysis(self, text: str) -> Dict:
        """
        Parsea el texto del análisis en secciones estructuradas (compatibilidad con formato anterior).
        Mantiene estructura antigua para compatibilidad, pero prefiere el formato nuevo.
        """
        # Intentar primero el formato nuevo (minimalista)
        text_lower = text.lower()
        fresh_count = 0  # Se calculará desde el contexto si es necesario
        
        # Detectar si es formato nuevo (tiene "impacto en cartera" o "1." seguido de impacto)
        is_new_format = "impacto en cartera" in text_lower or (
            "1." in text and ("impacto" in text_lower[:200] or "resumen corto" in text_lower[:200])
        )
        
        if is_new_format:
            # Usar el nuevo formatter
            sections_dict = self._validate_and_format_response(text, fresh_count)
            return {
                "impacto_cartera": sections_dict.get("impacto_cartera", ""),
                "acciones_recomendadas": sections_dict.get("acciones_recomendadas", ""),
                "nuevos_activos": sections_dict.get("nuevos_activos", ""),
                # Mantener campos antiguos para compatibilidad
                "resumen_ejecutivo": sections_dict.get("impacto_cartera", ""),
                "riesgos_identificados": "",
                "actores_clave": "",
                "senales_tempranas": "",
                "recomendaciones_cartera": sections_dict.get("acciones_recomendadas", "") + "\n" + sections_dict.get("nuevos_activos", ""),
                "conclusiones_accionables": sections_dict.get("acciones_recomendadas", "")
            }
        
        # Formato antiguo (compatibilidad)
        sections = {
            "impacto_cartera": "",
            "acciones_recomendadas": "",
            "nuevos_activos": "",
            "resumen_ejecutivo": "",
            "riesgos_identificados": "",
            "actores_clave": "",
            "senales_tempranas": "",
            "recomendaciones_cartera": "",
            "conclusiones_accionables": ""
        }
        
        # Resumen ejecutivo / Impacto
        if "resumen ejecutivo" in text_lower or "impacto" in text_lower:
            start = text_lower.find("resumen") if "resumen" in text_lower else text_lower.find("impacto")
            end = text_lower.find("riesgos", start) if "riesgos" in text_lower[start:] else len(text)
            if end == len(text):
                end = text_lower.find("acciones", start) if "acciones" in text_lower[start:] else len(text)
            content = text[start:end].strip()
            sections["resumen_ejecutivo"] = self._truncate_section(content)
            sections["impacto_cartera"] = self._truncate_section(content)
        
        # Acciones recomendadas
        if "acciones recomendadas" in text_lower or "recomendaciones" in text_lower:
            start = text_lower.find("acciones") if "acciones recomendadas" in text_lower else text_lower.find("recomendaciones")
            end = text_lower.find("nuevos activos", start) if "nuevos activos" in text_lower[start:] else len(text)
            if end == len(text):
                end = text_lower.find("conclusiones", start) if "conclusiones" in text_lower[start:] else len(text)
            content = text[start:end].strip()
            sections["acciones_recomendadas"] = self._truncate_section(content)
            sections["recomendaciones_cartera"] = self._truncate_section(content)
        
        # Nuevos activos
        if "nuevos activos" in text_lower:
            start = text_lower.find("nuevos activos")
            end = text_lower.find("conclusiones", start) if "conclusiones" in text_lower[start:] else len(text)
            content = text[start:end].strip()
            sections["nuevos_activos"] = self._truncate_section(content)
        
        # Si no se encontraron secciones, usar el texto completo pero truncado
        if not any(sections.values()):
            truncated = self._truncate_section(text)
            sections["resumen_ejecutivo"] = truncated
            sections["impacto_cartera"] = truncated
        
        return sections
