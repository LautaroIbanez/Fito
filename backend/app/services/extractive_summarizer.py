"""Servicio de resumen extractivo basado en reglas (sin LLM)."""
import logging
import re
from typing import List, Dict, Tuple, Optional
from app.services.local_nlp import get_local_nlp_service

logger = logging.getLogger(__name__)


class ExtractiveSummarizer:
    """Genera resúmenes extractivos seleccionando frases con mayor densidad de información."""
    
    def __init__(self):
        """Inicializa el servicio de NLP local."""
        self.nlp_service = get_local_nlp_service()
        logger.info("ExtractiveSummarizer inicializado (sin LLM)")
    
    def summarize_news(
        self,
        text: str,
        title: Optional[str] = None,
        max_sentences: int = 3,
        max_chars: Optional[int] = None
    ) -> str:
        """
        Genera un resumen extractivo seleccionando las frases más informativas.
        
        Args:
            text: Texto completo de la noticia
            title: Título de la noticia (opcional, se usa para contexto)
            max_sentences: Número máximo de frases a seleccionar (default: 3)
            max_chars: Límite máximo de caracteres (opcional, sobrescribe max_sentences si se alcanza antes)
        
        Returns:
            Resumen extractivo como string
        """
        if not text or not text.strip():
            return ""
        
        # Combinar título y texto para análisis
        full_text = f"{title} {text}" if title else text
        
        # Analizar con NLP local
        analysis = self.nlp_service.analyze_news(full_text)
        
        # Extraer entidades y keywords
        entities = analysis.get("entities", {})
        all_entities = []
        for entity_type, entity_list in entities.items():
            all_entities.extend(entity_list)
        
        # Obtener keywords del análisis
        keywords = analysis.get("keywords", [])
        
        # Dividir en oraciones
        sentences = self._split_sentences(text)
        
        if not sentences:
            return text[:200] + "..." if len(text) > 200 else text
        
        # Calcular score de densidad para cada oración
        sentence_scores = []
        for sentence in sentences:
            score = self._calculate_density_score(sentence, all_entities, keywords)
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
        
        # Ordenar las frases seleccionadas por su posición original en el texto
        # para mantener coherencia narrativa
        selected_with_positions = [
            (sent, text.find(sent)) for sent in selected_sentences
        ]
        selected_with_positions.sort(key=lambda x: x[1])
        final_sentences = [sent for sent, _ in selected_with_positions]
        
        # Unir frases
        summary = " ".join(final_sentences)
        
        # Log trazable (motor local)
        logger.debug(
            f"[MOTOR LOCAL] [EXTRACTIVE_SUMMARY] Texto analizado: {len(text)} chars, "
            f"{len(sentences)} oraciones | "
            f"Seleccionadas: {len(final_sentences)} oraciones, {len(summary)} chars | "
            f"Entidades: {len(all_entities)}, Keywords: {len(keywords)} (sin LLM)"
        )
        
        return summary
    
    def summarize_batch(
        self,
        news_items: List[Dict],
        max_sentences_per_news: int = 2,
        max_chars_per_news: Optional[int] = None,
        max_total_chars: Optional[int] = None
    ) -> List[Dict]:
        """
        Genera resúmenes extractivos para un lote de noticias.
        
        Args:
            news_items: Lista de diccionarios con 'title' y 'body' (o 'text')
            max_sentences_per_news: Máximo de frases por noticia
            max_chars_per_news: Límite de caracteres por noticia
            max_total_chars: Límite total de caracteres para todo el lote
        
        Returns:
            Lista de diccionarios con 'id', 'title', 'summary', 'char_count'
        """
        summaries = []
        total_chars = 0
        
        for item in news_items:
            # Obtener texto y título
            text = item.get("body") or item.get("text") or ""
            title = item.get("title")
            item_id = item.get("id")
            
            if not text:
                continue
            
            # Generar resumen
            summary = self.summarize_news(
                text=text,
                title=title,
                max_sentences=max_sentences_per_news,
                max_chars=max_chars_per_news
            )
            
            # Verificar límite total
            if max_total_chars and total_chars + len(summary) > max_total_chars:
                # Truncar si es necesario
                remaining = max_total_chars - total_chars
                if remaining > 50:  # Solo si queda espacio significativo
                    summary = summary[:remaining] + "..."
                else:
                    break  # No agregar más resúmenes
            
            summaries.append({
                "id": item_id,
                "title": title,
                "summary": summary,
                "char_count": len(summary)
            })
            
            total_chars += len(summary)
        
        logger.info(
            f"[MOTOR LOCAL] [EXTRACTIVE_BATCH] Procesado lote: {len(news_items)} noticias → "
            f"{len(summaries)} resúmenes, {total_chars} chars totales (sin LLM)"
        )
        
        return summaries
    
    def _split_sentences(self, text: str) -> List[str]:
        """Divide el texto en oraciones."""
        # Patrón para dividir oraciones (considera . ! ? seguidos de espacio o fin de línea)
        sentence_pattern = r'[.!?]+(?:\s+|$)'
        sentences = re.split(sentence_pattern, text)
        
        # Limpiar y filtrar
        cleaned = []
        for sent in sentences:
            sent = sent.strip()
            if sent and len(sent) > 10:  # Mínimo de caracteres
                cleaned.append(sent)
        
        return cleaned
    
    def _calculate_density_score(
        self,
        sentence: str,
        entities: List[str],
        keywords: List[str]
    ) -> float:
        """
        Calcula un score de densidad de información para una oración.
        
        Factores:
        - Presencia de entidades (ORG, PERSON, GPE)
        - Presencia de keywords
        - Longitud de la oración (oraciones muy cortas o muy largas tienen menos peso)
        - Posición en el texto (primeras oraciones tienen más peso)
        """
        score = 0.0
        sentence_lower = sentence.lower()
        
        # Peso por entidades (alto)
        entity_matches = sum(1 for entity in entities if entity.lower() in sentence_lower)
        score += entity_matches * 2.0
        
        # Peso por keywords (medio)
        keyword_matches = sum(1 for keyword in keywords if keyword.lower() in sentence_lower)
        score += keyword_matches * 1.0
        
        # Peso por longitud (oraciones de 50-150 caracteres son ideales)
        length = len(sentence)
        if 50 <= length <= 150:
            score += 1.0
        elif 20 <= length < 50 or 150 < length <= 250:
            score += 0.5
        else:
            score += 0.1  # Muy cortas o muy largas
        
        # Peso por números/métricas (indicador de información concreta)
        number_pattern = r'\d+[.,]?\d*[%$BMK]?'
        number_matches = len(re.findall(number_pattern, sentence))
        score += number_matches * 0.5
        
        return score
