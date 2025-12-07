import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Set
from config import CTR_BENCHMARKS, THRESHOLDS
import re

class SEOAnalyzer:
    """Analyze SEO performance using GSC data and page metadata"""
    
    @staticmethod
    def calculate_ctr_benchmark(position: float) -> float:
        """Get expected CTR for a given position"""
        if position <= 10:
            return CTR_BENCHMARKS.get(int(position), 0.02)
        elif position <= 20:
            return CTR_BENCHMARKS['page2']
        else:
            return CTR_BENCHMARKS['page3+']
    
    @staticmethod
    def analyze_ctr_performance(row: pd.Series) -> Dict:
        """Analyze CTR performance against benchmarks"""
        position = row.get('position', 0)
        actual_ctr = row.get('ctr', 0)
        impressions = row.get('impressions', 0)
        
        if position == 0 or impressions < THRESHOLDS['min_impressions']:
            return {'ctr_opportunity': False}
        
        expected_ctr = SEOAnalyzer.calculate_ctr_benchmark(position)
        ctr_ratio = actual_ctr / expected_ctr if expected_ctr > 0 else 0
        
        # Calculate potential clicks if CTR was at benchmark
        potential_clicks = impressions * expected_ctr
        current_clicks = row.get('clicks', 0)
        missed_clicks = max(0, potential_clicks - current_clicks)
        
        return {
            'ctr_opportunity': ctr_ratio < THRESHOLDS['ctr_underperformance_ratio'],
            'expected_ctr': expected_ctr,
            'actual_ctr': actual_ctr,
            'ctr_ratio': ctr_ratio,
            'ctr_gap': expected_ctr - actual_ctr,
            'missed_clicks': int(missed_clicks),
            'potential_clicks': int(potential_clicks)
        }
    
    @staticmethod
    def analyze_title_meta_match(row: pd.Series) -> Dict:
        """Analyze how well title/meta match ranking queries"""
        queries = row.get('top_queries', [])
        if not queries:
            queries = row.get('query', [])
        
        title = str(row.get('title', '')).lower()
        meta_desc = str(row.get('meta_description', '')).lower()
        h1 = str(row.get('h1', '')).lower()
        
        result = {
            'title_issues': [],
            'meta_issues': [],
            'optimization_potential': False,
            'missing_keywords': set()
        }
        
        if not queries:
            return result
        
        # Analyze top queries
        top_queries = queries[:5] if isinstance(queries, list) else [queries]
        
        for query in top_queries:
            if not query:
                continue
                
            query_lower = query.lower()
            query_words = set(re.findall(r'\b\w+\b', query_lower))
            
            # Skip brand queries
            if 'examplebrand' in query_lower:
                continue
            
            # Check exact match first
            if query_lower not in title and query_lower not in meta_desc:
                # Check word match
                title_words = set(re.findall(r'\b\w+\b', title))
                meta_words = set(re.findall(r'\b\w+\b', meta_desc))
                
                title_match_ratio = len(query_words & title_words) / len(query_words) if query_words else 0
                meta_match_ratio = len(query_words & meta_words) / len(query_words) if query_words else 0
                
                if title_match_ratio < THRESHOLDS['title_match_threshold']:
                    result['title_issues'].append(f"Missing query terms: '{query}'")
                    result['missing_keywords'].update(query_words - title_words)
                    result['optimization_potential'] = True
                
                if meta_match_ratio < THRESHOLDS['meta_match_threshold']:
                    result['meta_issues'].append(f"Meta missing terms from: '{query}'")
                    result['optimization_potential'] = True
        
        # Check title/meta length issues
        title_length = row.get('title_length', len(title))
        meta_length = row.get('meta_length', len(meta_desc))
        
        if title_length < 30:
            result['title_issues'].append("Title too short (<30 chars)")
            result['optimization_potential'] = True
        elif title_length > 60:
            result['title_issues'].append("Title too long (>60 chars)")
            
        if meta_length < 120:
            result['meta_issues'].append("Meta description too short (<120 chars)")
            result['optimization_potential'] = True
        elif meta_length > 160:
            result['meta_issues'].append("Meta description too long (>160 chars)")
        
        return result
    
    @staticmethod
    def analyze_content_depth(row: pd.Series) -> Dict:
        """Analyze if content depth matches query intent"""
        word_count = row.get('word_count', 0)
        queries = row.get('top_queries', [])
        position = row.get('position', 0)
        
        result = {
            'content_issues': [],
            'content_expansion_needed': False
        }
        
        # Pages ranking 11-20 often need more content
        if 11 <= position <= 20 and word_count < 1500:
            result['content_issues'].append(f"Page 2 ranking with only {word_count} words")
            result['content_expansion_needed'] = True
        
        # Check for thin content on competitive queries
        if word_count < 300 and position > 10:
            result['content_issues'].append("Thin content (<300 words)")
            result['content_expansion_needed'] = True
        
        # Analyze query types
        informational_keywords = ['how', 'what', 'why', 'guide', 'tutorial', 'tips']
        if queries:
            for query in queries[:5]:
                if any(keyword in query.lower() for keyword in informational_keywords):
                    if word_count < 1000:
                        result['content_issues'].append(
                            f"Informational query '{query}' but only {word_count} words"
                        )
                        result['content_expansion_needed'] = True
                    break
        
        return result
    
    @staticmethod
    def calculate_opportunity_score(row: pd.Series, analysis_results: Dict) -> float:
        """Calculate opportunity score for prioritization"""
        score = 0
        
        # Base score from impressions (log scale to prevent domination)
        impressions = row.get('impressions', 0)
        if impressions > 0:
            score += min(np.log10(impressions) * 5, 25)  # Max 25 points
        
        # CTR opportunity (biggest impact)
        if analysis_results.get('ctr_opportunity'):
            missed_clicks = analysis_results.get('missed_clicks', 0)
            score += min(missed_clicks / 10, 30)  # Max 30 points
        
        # Position opportunity
        position = row.get('position', 0)
        if 4 <= position <= 10:  # Striking distance
            score += (11 - position) * 3  # 3-21 points
        elif 11 <= position <= 20:  # Page 2
            score += 15
        
        # Title/Meta optimization potential
        if analysis_results.get('optimization_potential'):
            score += 15
            if len(analysis_results.get('title_issues', [])) > 1:
                score += 5
        
        # Content depth issues
        if analysis_results.get('content_expansion_needed'):
            score += 10
        
        # Boost for high-value pages
        if row.get('clicks', 0) > 100:  # Already getting traffic
            score *= 1.2
        
        return round(score, 2)
    
    @staticmethod
    def classify_opportunity(analysis_results: Dict, row: pd.Series) -> List[str]:
        """Classify the type of opportunity"""
        types = []
        
        if analysis_results.get('ctr_opportunity'):
            types.append('CTR_OPTIMIZATION')
        
        position = row.get('position', 0)
        if 4 <= position <= 10:
            types.append('STRIKING_DISTANCE')
        elif 11 <= position <= 20:
            types.append('PAGE2_PUSH')
        
        if analysis_results.get('title_issues'):
            types.append('TITLE_OPTIMIZATION')
        
        if analysis_results.get('meta_issues'):
            types.append('META_OPTIMIZATION')
        
        if analysis_results.get('content_expansion_needed'):
            types.append('CONTENT_EXPANSION')
        
        return types if types else ['GENERAL_OPTIMIZATION']
