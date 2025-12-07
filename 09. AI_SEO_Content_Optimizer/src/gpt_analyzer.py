import os
from typing import Dict, List, Optional
import logging
from openai import OpenAI
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

class GPTAnalyzer:
    def __init__(self, model: str = "gpt-4-turbo-preview"):
        load_dotenv()
        self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.model = model

    def _create_analysis_prompt(self, target_content: Dict, competitor_contents: List[Dict], serp_features: Dict) -> str:
        """Create a prompt for GPT analysis."""
        prompt = f"""Analyze the following content for SEO optimization opportunities.

        Target URL Content:
        - Title: {target_content['meta_tags'].get('title', 'N/A')}
        - Meta Description: {target_content['meta_tags'].get('description', 'N/A')}
        - Main Content Length: {len(target_content['main_content'].split())} words
        - Headings Structure: {target_content['headings']}

        Competitor URLs ({len(competitor_contents)}):
        {self._format_competitor_content(competitor_contents)}

        SERP Features:
        {self._format_serp_features(serp_features)}

        Please provide specific, actionable recommendations for:
        1. Title tag optimization (with character count)
        2. Meta description improvement (with character count)
        3. Heading structure enhancements
        4. Content additions and modifications
        5. Internal linking suggestions
        6. SERP feature opportunities
        7. Conversion improvement recommendations

        Format the response as a structured analysis with clear sections and bullet points."""
        
        return prompt

    def _format_competitor_content(self, competitor_contents: List[Dict]) -> str:
        """Format competitor content for the prompt."""
        formatted = []
        for i, content in enumerate(competitor_contents, 1):
            formatted.append(f"""
            Competitor {i}:
            - Title: {content['meta_tags'].get('title', 'N/A')}
            - Meta Description: {content['meta_tags'].get('description', 'N/A')}
            - Main Content Length: {len(content['main_content'].split())} words
            - Headings Structure: {content['headings']}
            """)
        return "\n".join(formatted)

    def _format_serp_features(self, serp_features: Dict) -> str:
        """Format SERP features for the prompt."""
        features = []
        for feature, value in serp_features.items():
            features.append(f"- {feature}: {value}")
        return "\n".join(features)

    def analyze_content(self, target_content: Dict, competitor_contents: List[Dict], serp_features: Dict) -> Optional[Dict]:
        """Analyze content using GPT and return recommendations."""
        try:
            prompt = self._create_analysis_prompt(target_content, competitor_contents, serp_features)
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert SEO content analyst specializing in content optimization and competitive analysis."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=2000
            )
            
            # Parse the response into structured recommendations
            analysis = self._parse_gpt_response(response.choices[0].message.content)
            return analysis
            
        except Exception as e:
            logger.error(f"Error in GPT analysis: {e}")
            return None

    def _parse_gpt_response(self, response: str) -> Dict:
        """Parse the GPT response into a structured format."""
        sections = {
            'title_optimization': [],
            'meta_description': [],
            'heading_structure': [],
            'content_modifications': [],
            'internal_linking': [],
            'serp_features': [],
            'conversion_optimization': []
        }
        
        current_section = None
        for line in response.split('\n'):
            line = line.strip()
            if not line:
                continue
                
            # Check for section headers
            if line.lower().startswith(('title', 'meta description', 'heading', 'content', 'internal linking', 'serp', 'conversion')):
                current_section = self._get_section_key(line.lower())
                continue
                
            # Add content to current section
            if current_section and line.startswith(('-', '*', '•')):
                sections[current_section].append(line.lstrip('- *•').strip())
        
        return sections

    def _get_section_key(self, line: str) -> str:
        """Map section headers to dictionary keys."""
        if 'title' in line:
            return 'title_optimization'
        elif 'meta' in line:
            return 'meta_description'
        elif 'heading' in line:
            return 'heading_structure'
        elif 'content' in line:
            return 'content_modifications'
        elif 'internal' in line:
            return 'internal_linking'
        elif 'serp' in line:
            return 'serp_features'
        elif 'conversion' in line:
            return 'conversion_optimization'
        return 'content_modifications'  # Default section 