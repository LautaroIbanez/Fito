"""Servicio para scoring de noticias basado en relevancia, sentimiento y decay temporal."""
import logging
import re
from typing import Dict, List, Tuple
from datetime import datetime, timezone, timedelta
from app.models import NewsItemResponse, PortfolioItemResponse
from app.config import (
    NEWS_STALE_DAYS,
    NEWS_OBSOLETE_DAYS,
    NEWS_SCORE_DECAY_FACTOR,
    NEWS_SCORE_TICKER_MATCH,
    NEWS_SCORE_CATEGORY_MATCH,
    NEWS_SCORE_POSITIVE_SENTIMENT,
    NEWS_SCORE_NEGATIVE_SENTIMENT,
    NEWS_SCORE_NEUTRAL_SENTIMENT,
    NEWS_SCORE_BASE
)

logger = logging.getLogger(__name__)

# Palabras clave positivas para análisis de sentimiento
POSITIVE_KEYWORDS = [
    "crece", "crecimiento", "aumenta", "aumento", "sube", "subida", "alza", "alza",
    "positivo", "favorable", "mejora", "mejoras", "éxito", "ganancias", "beneficios",
    "fortalece", "fortalecimiento", "optimista", "optimismo", "recuperación",
    "expansión", "expande", "récord", "record", "supera", "superior", "ganar",
    "ventaja", "competitivo", "liderazgo", "innovación", "rentable", "dividendos"
]

# Palabras clave negativas para análisis de sentimiento
NEGATIVE_KEYWORDS = [
    "cae", "caída", "baja", "bajada", "descenso", "decrece", "decrecimiento",
    "negativo", "desfavorable", "empeora", "pérdida", "pérdidas", "pierde",
    "crisis", "riesgo", "riesgos", "inestable", "volatilidad", "incertidumbre",
    "recesión", "contracción", "déficit", "deuda", "quiebra", "quiebras",
    "despidos", "desempleo", "inflación", "devaluación", "conflicto", "conflictos",
    "sanción", "sanciones", "investigación", "fraude", "escándalo"
]

# Mapeo de tipos de activo a palabras clave de búsqueda
ASSET_TYPE_KEYWORDS = {
    "acciones": ["acciones", "acciones", "stock", "stocks", "equity", "empresa", "empresas", "corporación", "corporaciones", "cotización", "cotiza"],
    "bonos": ["bonos", "bono", "bond", "bonds", "renta fija", "deuda", "títulos", "emisión", "emisiones"],
    "etf": ["etf", "etfs", "fondo cotizado", "fondos cotizados", "exchange traded fund"],
    "fondos": ["fondo", "fondos", "mutual fund", "investment fund", "fondo de inversión"],
    "divisas": ["divisas", "divisa", "moneda", "monedas", "currency", "forex", "tipo de cambio", "dólar", "euro", "peso"],
    "otros": ["activo", "activos", "inversión", "inversiones", "portfolio", "cartera"]
}


class NewsScoringService:
    """Servicio para calcular scores de noticias."""
    
    def __init__(self):
        self.stale_days = NEWS_STALE_DAYS
        self.obsolete_days = NEWS_OBSOLETE_DAYS
        self.decay_factor = NEWS_SCORE_DECAY_FACTOR
        self.ticker_match_score = NEWS_SCORE_TICKER_MATCH
        self.category_match_score = NEWS_SCORE_CATEGORY_MATCH
        self.positive_sentiment_score = NEWS_SCORE_POSITIVE_SENTIMENT
        self.negative_sentiment_score = NEWS_SCORE_NEGATIVE_SENTIMENT
        self.neutral_sentiment_score = NEWS_SCORE_NEUTRAL_SENTIMENT
        self.base_score = NEWS_SCORE_BASE
    
    def parse_news_date(self, date_str: str) -> datetime:
        """Parsea fecha ISO a datetime."""
        try:
            if 'T' in date_str:
                dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            else:
                dt = datetime.fromisoformat(date_str)
            
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            
            return dt
        except (ValueError, AttributeError) as e:
            logger.warning(f"Error parseando fecha '{date_str}': {e}")
            return datetime.now(timezone.utc)
    
    def calculate_age_days(self, date_str: str) -> int:
        """Calcula días de antigüedad de una noticia."""
        news_date = self.parse_news_date(date_str)
        now = datetime.now(timezone.utc)
        age = (now - news_date).days
        return max(0, age)
    
    def is_obsolete(self, date_str: str) -> bool:
        """Determina si una noticia es obsoleta según umbral configurable."""
        age_days = self.calculate_age_days(date_str)
        return age_days > self.obsolete_days
    
    def calculate_temporal_decay(self, date_str: str) -> float:
        """
        Calcula factor de decay temporal usando factor exponencial.
        Score_decayed = Score_base * (decay_factor ^ age_days)
        """
        age_days = self.calculate_age_days(date_str)
        decay_multiplier = self.decay_factor ** age_days
        return decay_multiplier
    
    def extract_portfolio_symbols(self, portfolio_items: List[PortfolioItemResponse]) -> List[str]:
        """Extrae todos los símbolos/tickers de la cartera."""
        symbols = []
        for item in portfolio_items:
            if item.symbol:
                symbols.append(item.symbol.upper())
        return symbols
    
    def extract_portfolio_categories(self, portfolio_items: List[PortfolioItemResponse]) -> List[str]:
        """Extrae todas las categorías/tipos de activos de la cartera."""
        categories = set()
        for item in portfolio_items:
            categories.add(item.asset_type.lower())
        return list(categories)
    
    def detect_ticker_mentions(self, text: str, symbols: List[str]) -> int:
        """
        Detecta menciones de tickers/símbolos en el texto.
        Retorna número de menciones encontradas.
        """
        if not symbols or not text:
            return 0
        
        text_upper = text.upper()
        mentions = 0
        
        for symbol in symbols:
            # Buscar símbolo como palabra completa (evitar matches parciales)
            pattern = r'\b' + re.escape(symbol.upper()) + r'\b'
            matches = len(re.findall(pattern, text_upper))
            mentions += matches
        
        return mentions
    
    def detect_category_mentions(self, text: str, categories: List[str]) -> int:
        """
        Detecta menciones de categorías/tipos de activos en el texto.
        Retorna número de menciones encontradas.
        """
        if not categories or not text:
            return 0
        
        text_lower = text.lower()
        mentions = 0
        
        for category in categories:
            keywords = ASSET_TYPE_KEYWORDS.get(category, [category])
            for keyword in keywords:
                # Buscar keyword como palabra completa
                pattern = r'\b' + re.escape(keyword.lower()) + r'\b'
                matches = len(re.findall(pattern, text_lower))
                mentions += matches
        
        return mentions
    
    def analyze_sentiment(self, text: str) -> Tuple[str, float]:
        """
        Analiza sentimiento básico del texto.
        Retorna: (sentiment_type, sentiment_score)
        """
        if not text:
            return ("neutral", self.neutral_sentiment_score)
        
        text_lower = text.lower()
        
        positive_count = sum(1 for keyword in POSITIVE_KEYWORDS if keyword in text_lower)
        negative_count = sum(1 for keyword in NEGATIVE_KEYWORDS if keyword in text_lower)
        
        if positive_count > negative_count:
            return ("positive", self.positive_sentiment_score)
        elif negative_count > positive_count:
            return ("negative", self.negative_sentiment_score)
        else:
            return ("neutral", self.neutral_sentiment_score)
    
    def calculate_news_score(
        self,
        news_item: NewsItemResponse,
        portfolio_items: List[PortfolioItemResponse] = None
    ) -> Dict:
        """
        Calcula score completo de una noticia.
        
        Score = (Base + TickerMatches * TickerScore + CategoryMatches * CategoryScore + SentimentScore) * TemporalDecay
        """
        score = self.base_score
        score_components = {
            "base": self.base_score,
            "ticker_matches": 0,
            "ticker_score": 0.0,
            "category_matches": 0,
            "category_score": 0.0,
            "sentiment_type": "neutral",
            "sentiment_score": 0.0,
            "temporal_decay": 1.0,
            "age_days": 0,
            "is_obsolete": False
        }
        
        # Calcular edad
        age_days = self.calculate_age_days(news_item.created_at)
        score_components["age_days"] = age_days
        score_components["is_obsolete"] = self.is_obsolete(news_item.created_at)
        
        # Detectar menciones de tickers
        if portfolio_items:
            symbols = self.extract_portfolio_symbols(portfolio_items)
            ticker_mentions = self.detect_ticker_mentions(news_item.body, symbols)
            if news_item.title:
                ticker_mentions += self.detect_ticker_mentions(news_item.title, symbols)
            
            if ticker_mentions > 0:
                ticker_score = ticker_mentions * self.ticker_match_score
                score += ticker_score
                score_components["ticker_matches"] = ticker_mentions
                score_components["ticker_score"] = ticker_score
        
        # Detectar menciones de categorías
        if portfolio_items:
            categories = self.extract_portfolio_categories(portfolio_items)
            category_mentions = self.detect_category_mentions(news_item.body, categories)
            if news_item.title:
                category_mentions += self.detect_category_mentions(news_item.title, categories)
            
            if category_mentions > 0:
                category_score = category_mentions * self.category_match_score
                score += category_score
                score_components["category_matches"] = category_mentions
                score_components["category_score"] = category_score
        
        # Analizar sentimiento
        sentiment_type, sentiment_score = self.analyze_sentiment(news_item.body)
        if news_item.title:
            title_sentiment, title_score = self.analyze_sentiment(news_item.title)
            # Usar el sentimiento más fuerte
            if abs(title_score) > abs(sentiment_score):
                sentiment_type = title_sentiment
                sentiment_score = title_score
        
        score += sentiment_score
        score_components["sentiment_type"] = sentiment_type
        score_components["sentiment_score"] = sentiment_score
        
        # Aplicar decay temporal
        temporal_decay = self.calculate_temporal_decay(news_item.created_at)
        final_score = score * temporal_decay
        score_components["temporal_decay"] = temporal_decay
        
        return {
            "news_id": news_item.id,
            "score": round(final_score, 2),
            "components": score_components
        }
    
    def score_and_sort_news(
        self,
        news_items: List[NewsItemResponse],
        portfolio_items: List[PortfolioItemResponse] = None
    ) -> List[Tuple[NewsItemResponse, Dict]]:
        """
        Calcula scores para todas las noticias y las ordena por score descendente.
        Retorna lista de tuplas: (news_item, score_dict)
        """
        scored_news = []
        
        for news_item in news_items:
            score_dict = self.calculate_news_score(news_item, portfolio_items)
            scored_news.append((news_item, score_dict))
        
        # Ordenar por score descendente
        scored_news.sort(key=lambda x: x[1]["score"], reverse=True)
        
        return scored_news

