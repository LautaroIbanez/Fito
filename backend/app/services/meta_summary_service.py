"""Servicio para generar metarresumen combinando resúmenes de lotes."""
import logging
import re
from typing import List, Dict, Optional
from app.services.local_nlp import get_local_nlp_service

logger = logging.getLogger(__name__)


class MetaSummaryService:
    """Genera un metarresumen combinando resúmenes de múltiples lotes."""
    
    def __init__(self):
        """Inicializa el servicio de NLP local."""
        self.nlp_service = get_local_nlp_service()
        logger.info("MetaSummaryService inicializado (sin LLM)")
    
    def generate_meta_summary(
        self,
        batch_summaries: List[Dict],
        max_sentences: int = 5,
        max_chars: Optional[int] = None,
        deduplicate: bool = True
    ) -> str:
        """
        Genera un metarresumen combinando resúmenes de lotes.
        
        Args:
            batch_summaries: Lista de diccionarios con 'summary' (texto del resumen)
            max_sentences: Número máximo de frases en el metarresumen
            max_chars: Límite máximo de caracteres
            deduplicate: Si True, elimina frases duplicadas o muy similares
        
        Returns:
            Metarresumen como string
        """
        if not batch_summaries:
            return ""
        
        # Extraer todos los textos de resumen
        all_summaries = []
        for batch in batch_summaries:
            summary_text = batch.get("summary", "")
            if summary_text and not summary_text.startswith("[Error"):
                all_summaries.append(summary_text)
        
        if not all_summaries:
            return ""
        
        # Combinar todos los resúmenes
        combined_text = " ".join(all_summaries)
        
        # Dividir en oraciones
        sentences = self._split_sentences(combined_text)
        
        if not sentences:
            # Fallback: usar primeros caracteres del texto combinado
            fallback = combined_text[:max_chars] if max_chars else combined_text[:500]
            logger.warning(f"[MOTOR LOCAL] [META_SUMMARY] No se pudieron dividir oraciones, usando fallback: {len(fallback)} chars")
            return fallback
        
        # Deduplicar si está habilitado
        if deduplicate:
            sentences = self._deduplicate_sentences(sentences)
        
        # Analizar con NLP para calcular importancia
        analysis = self.nlp_service.analyze_news(combined_text)
        entities = []
        for entity_list in analysis.get("entities", {}).values():
            entities.extend(entity_list)
        keywords = analysis.get("keywords", [])
        
        # Calcular scores de importancia
        sentence_scores = []
        for sentence in sentences:
            score = self._calculate_importance_score(sentence, entities, keywords)
            sentence_scores.append((sentence, score))
        
        # Ordenar por score descendente
        sentence_scores.sort(key=lambda x: x[1], reverse=True)
        
        # Seleccionar top N frases
        selected_sentences = []
        total_chars = 0
        
        for sentence, score in sentence_scores:
            if max_chars and total_chars + len(sentence) > max_chars:
                break
            
            selected_sentences.append(sentence)
            total_chars += len(sentence)
            
            if len(selected_sentences) >= max_sentences:
                break
        
        # Si no se seleccionaron oraciones (todos los scores fueron 0 o muy bajos),
        # usar las primeras oraciones como fallback
        if not selected_sentences and sentences:
            logger.warning(f"[MOTOR LOCAL] [META_SUMMARY] No se seleccionaron oraciones por score, usando primeras {max_sentences} como fallback")
            selected_sentences = sentences[:max_sentences]
            total_chars = sum(len(s) for s in selected_sentences)
        
        # Ordenar por posición original para mantener coherencia
        if selected_sentences:
            selected_with_positions = [
                (sent, combined_text.find(sent)) for sent in selected_sentences
            ]
            selected_with_positions.sort(key=lambda x: x[1])
            final_sentences = [sent for sent, _ in selected_with_positions]
        else:
            # Fallback final: usar primeros caracteres
            logger.warning(f"[MOTOR LOCAL] [META_SUMMARY] Fallback final: usando primeros caracteres del texto combinado")
            final_sentences = []
            meta_summary = combined_text[:max_chars] if max_chars else combined_text[:500]
            return meta_summary
        
        # Unir frases
        meta_summary = " ".join(final_sentences)
        
        # Log trazable (motor local)
        logger.info(
            f"[MOTOR LOCAL] [META_SUMMARY] Combinados {len(batch_summaries)} lotes → "
            f"{len(sentences)} oraciones totales → "
            f"{len(final_sentences)} oraciones seleccionadas, {len(meta_summary)} chars | "
            f"Entidades: {len(entities)}, Keywords: {len(keywords)} (sin LLM)"
        )
        
        return meta_summary
    
    def _split_sentences(self, text: str) -> List[str]:
        """Divide el texto en oraciones."""
        if not text or not text.strip():
            return []
        
        # Patrón más robusto para dividir oraciones
        # Buscar puntos, exclamaciones, interrogaciones seguidos de espacio o fin de línea
        sentence_pattern = r'[.!?]+(?:\s+|$)'
        sentences = re.split(sentence_pattern, text)
        
        cleaned = []
        for sent in sentences:
            sent = sent.strip()
            # Aceptar oraciones más cortas (mínimo 15 caracteres) para capturar más contenido
            if sent and len(sent) >= 15:
                cleaned.append(sent)
        
        # Si no se encontraron oraciones con el patrón, dividir por puntos y comas
        if not cleaned:
            # Dividir por puntos, comas, o saltos de línea
            alternative_splits = re.split(r'[.,;]\s+|\n+', text)
            for sent in alternative_splits:
                sent = sent.strip()
                if sent and len(sent) >= 15:
                    cleaned.append(sent)
        
        # Si aún no hay oraciones, usar el texto completo como una oración
        if not cleaned and text.strip():
            cleaned.append(text.strip())
        
        return cleaned
    
    def _deduplicate_sentences(self, sentences: List[str]) -> List[str]:
        """Elimina oraciones duplicadas o muy similares."""
        if not sentences:
            return []
        
        unique_sentences = []
        seen_normalized = set()
        
        for sentence in sentences:
            # Normalizar para comparación
            normalized = self._normalize_sentence(sentence)
            
            # Verificar similitud (si más del 80% de palabras coinciden, es duplicado)
            is_duplicate = False
            for seen in seen_normalized:
                similarity = self._calculate_similarity(normalized, seen)
                if similarity > 0.8:
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                unique_sentences.append(sentence)
                seen_normalized.add(normalized)
        
        return unique_sentences
    
    def _normalize_sentence(self, sentence: str) -> str:
        """Normaliza una oración para comparación."""
        # Convertir a minúsculas, eliminar puntuación, ordenar palabras
        normalized = re.sub(r'[^\w\s]', '', sentence.lower())
        words = sorted(normalized.split())
        return " ".join(words)
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calcula similitud entre dos textos normalizados (Jaccard)."""
        words1 = set(text1.split())
        words2 = set(text2.split())
        
        if not words1 and not words2:
            return 1.0
        if not words1 or not words2:
            return 0.0
        
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        
        return intersection / union if union > 0 else 0.0
    
    def _calculate_importance_score(
        self,
        sentence: str,
        entities: List[str],
        keywords: List[str]
    ) -> float:
        """Calcula score de importancia para una oración en el contexto del metarresumen."""
        score = 0.0
        sentence_lower = sentence.lower()
        
        # Entidades (alto peso)
        entity_matches = sum(1 for entity in entities if entity.lower() in sentence_lower)
        score += entity_matches * 2.0
        
        # Keywords (medio peso)
        keyword_matches = sum(1 for keyword in keywords if keyword.lower() in sentence_lower)
        score += keyword_matches * 1.0
        
        # Números/métricas (información concreta)
        number_pattern = r'\d+[.,]?\d*[%$BMK]?'
        number_matches = len(re.findall(number_pattern, sentence))
        score += number_matches * 0.5
        
        # Longitud ideal
        length = len(sentence)
        if 50 <= length <= 150:
            score += 1.0
        elif 20 <= length < 50 or 150 < length <= 250:
            score += 0.5
        
        # Score base mínimo: todas las oraciones tienen al menos un score mínimo
        # para asegurar que siempre se seleccione algo
        if score == 0.0:
            score = 0.1  # Score mínimo para que no se descarte completamente
        
        return score
