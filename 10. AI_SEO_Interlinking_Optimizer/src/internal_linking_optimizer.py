#!/usr/bin/env python3

import argparse
import networkx as nx
import pandas as pd
import numpy as np
from tqdm import tqdm
from scipy.sparse import csr_matrix
from pathlib import Path
import logging
from typing import Dict, List, Tuple, Set
import re
import requests
import xml.etree.ElementTree as ET
from urllib.parse import urlparse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SitemapParser:
    def __init__(self, sitemap_urls: List[str]):
        """Initialize the sitemap parser.
        
        Args:
            sitemap_urls: List of sitemap URLs to parse
        """
        self.sitemap_urls = sitemap_urls
        self.valid_urls = set()
        
    def parse_sitemap(self, sitemap_url: str) -> Set[str]:
        """Parse a single sitemap and extract URLs."""
        logger.info(f"Parsing sitemap: {sitemap_url}")
        try:
            response = requests.get(sitemap_url)
            response.raise_for_status()
            
            # Parse XML
            root = ET.fromstring(response.content)
            
            # Extract URLs from sitemap
            urls = set()
            for url in root.findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}loc'):
                urls.add(url.text)
            
            return urls
        except Exception as e:
            logger.error(f"Error parsing sitemap {sitemap_url}: {str(e)}")
            return set()
    
    def get_valid_urls(self) -> Set[str]:
        """Get all valid URLs from all sitemaps."""
        for sitemap_url in self.sitemap_urls:
            urls = self.parse_sitemap(sitemap_url)
            self.valid_urls.update(urls)
        
        # Normalize URLs
        self.valid_urls = {self.normalize_url(url) for url in self.valid_urls}
        logger.info(f"Found {len(self.valid_urls)} valid URLs in sitemaps")
        return self.valid_urls
    
    @staticmethod
    def normalize_url(url: str) -> str:
        """Normalize URLs by removing trailing slashes and converting to lowercase."""
        return url.rstrip('/').lower()

class InternalLinkingOptimizer:
    def __init__(self, internal_all_path: str, all_inlinks_path: str, sitemap_urls: List[str]):
        """Initialize the Internal Linking Optimizer.
        
        Args:
            internal_all_path: Path to the internal_all.csv file
            all_inlinks_path: Path to the all_inlinks.csv file
            sitemap_urls: List of sitemap URLs to parse
        """
        self.internal_all_path = internal_all_path
        self.all_inlinks_path = all_inlinks_path
        self.sitemap_parser = SitemapParser(sitemap_urls)
        self.graph = nx.DiGraph()
        self.page_attributes = None
        self.pagerank_scores = None
        
    def normalize_url(self, url: str) -> str:
        """Normalize URLs by removing trailing slashes and converting to lowercase."""
        return url.rstrip('/').lower()
    
    def load_data(self):
        """Load and preprocess the input data."""
        # First get valid URLs from sitemaps
        valid_urls = self.sitemap_parser.get_valid_urls()
        
        logger.info("Loading page metadata...")
        self.page_attributes = pd.read_csv(self.internal_all_path, low_memory=False)
        
        # Filter for 200 status code pages and valid URLs from sitemap
        self.page_attributes = self.page_attributes[
            (self.page_attributes['Status Code'] == 200) &
            (self.page_attributes['Address'].apply(self.normalize_url).isin(valid_urls))
        ]
        
        # Normalize URLs
        self.page_attributes['Address'] = self.page_attributes['Address'].apply(self.normalize_url)
        
        logger.info("Loading inlink data...")
        inlinks_df = pd.read_csv(self.all_inlinks_path, low_memory=False)
        
        # Normalize source and target URLs
        inlinks_df['From'] = inlinks_df['From'].apply(self.normalize_url)
        inlinks_df['To'] = inlinks_df['To'].apply(self.normalize_url)
        
        # Filter for valid links (both source and target have 200 status and are in sitemap)
        valid_urls = set(self.page_attributes['Address'])
        inlinks_df = inlinks_df[
            inlinks_df['From'].isin(valid_urls) & 
            inlinks_df['To'].isin(valid_urls)
        ]
        
        return inlinks_df
    
    def build_graph(self, inlinks_df: pd.DataFrame):
        """Build the directed graph from inlink data."""
        logger.info("Building graph...")
        
        # Add nodes with attributes
        for _, row in tqdm(self.page_attributes.iterrows(), total=len(self.page_attributes)):
            self.graph.add_node(
                row['Address'],
                title=row.get('Title', ''),
                h1=row.get('H1-1', ''),
                word_count=row.get('Word Count', 0),
                depth=row.get('Depth', 0)
            )
        
        # Add edges with attributes
        for _, row in tqdm(inlinks_df.iterrows(), total=len(inlinks_df)):
            self.graph.add_edge(
                row['From'],
                row['To'],
                anchor_text=row.get('Anchor Text', ''),
                link_location=row.get('Link Position', '')
            )
    
    def calculate_pagerank(self):
        """Calculate PageRank scores with custom weights based on link location."""
        logger.info("Calculating PageRank...")
        
        # Create weight matrix based on link location
        weights = {}
        for u, v, data in self.graph.edges(data=True):
            # Adjust weights based on link location
            location_weight = 1.0
            if data.get('link_location') == 'header':
                location_weight = 0.5  # Header links get less weight
            elif data.get('link_location') == 'footer':
                location_weight = 0.3  # Footer links get even less weight
            elif data.get('link_location') == 'main_content':
                location_weight = 1.5  # Main content links get more weight
            
            weights[(u, v)] = location_weight
        
        # Calculate PageRank with custom weights
        self.pagerank_scores = nx.pagerank(
            self.graph,
            weight=lambda u, v: weights.get((u, v), 1.0)
        )
    
    def find_orphaned_content(self, min_inlinks: int = 2) -> pd.DataFrame:
        """Find pages with few inbound links but good content."""
        logger.info("Finding orphaned content...")
        
        orphaned_pages = []
        for node in self.graph.nodes():
            in_degree = self.graph.in_degree(node)
            if in_degree < min_inlinks:
                node_data = self.graph.nodes[node]
                orphaned_pages.append({
                    'URL': node,
                    'Inbound Links': in_degree,
                    'Title': node_data.get('title', ''),
                    'H1': node_data.get('h1', ''),
                    'Word Count': node_data.get('word_count', 0),
                    'PageRank': self.pagerank_scores.get(node, 0)
                })
        
        return pd.DataFrame(orphaned_pages)
    
    def find_authority_leaks(self, pagerank_threshold: float = 0.001) -> pd.DataFrame:
        """Find high-PageRank pages linking to low-value destinations."""
        logger.info("Finding authority leaks...")
        
        leaks = []
        for u, v in self.graph.edges():
            if self.pagerank_scores.get(u, 0) > pagerank_threshold:
                edge_data = self.graph.get_edge_data(u, v)
                leaks.append({
                    'Source URL': u,
                    'Target URL': v,
                    'Source PageRank': self.pagerank_scores.get(u, 0),
                    'Target PageRank': self.pagerank_scores.get(v, 0),
                    'Anchor Text': edge_data.get('anchor_text', ''),
                    'Link Location': edge_data.get('link_location', '')
                })
        
        return pd.DataFrame(leaks)
    
    def find_non_200_links(self) -> pd.DataFrame:
        """Find internal links that point to non-200 status pages."""
        logger.info("Finding non-200 status internal links...")
        
        # Load all inlinks data without filtering
        all_inlinks = pd.read_csv(self.all_inlinks_path, low_memory=False)
        
        # Load all page data to get status codes
        all_pages = pd.read_csv(self.internal_all_path, low_memory=False)
        
        # Create a mapping of URLs to their status codes
        url_status_map = dict(zip(
            all_pages['Address'].apply(self.normalize_url),
            all_pages['Status Code']
        ))
        
        # Filter for internal links only
        internal_links = all_inlinks[
            all_inlinks['From'].apply(self.normalize_url).isin(self.sitemap_parser.valid_urls)
        ]
        
        # Add status codes for target URLs
        internal_links['Target Status'] = internal_links['To'].apply(
            lambda x: url_status_map.get(self.normalize_url(x), 'Unknown')
        )
        
        # Filter for non-200 status links
        non_200_links = internal_links[internal_links['Target Status'] != 200]
        
        # Get redirect targets for 301/302 links
        redirects = all_pages[
            all_pages['Status Code'].isin([301, 302]) &
            all_pages['Address'].apply(self.normalize_url).isin(
                non_200_links['To'].apply(self.normalize_url)
            )
        ]
        
        # Create a mapping of redirect sources to their targets
        redirect_map = dict(zip(
            redirects['Address'].apply(self.normalize_url),
            redirects['Redirect URL'].apply(self.normalize_url)
        ))
        
        # Add redirect target information
        non_200_links['Redirect Target'] = non_200_links['To'].apply(
            lambda x: redirect_map.get(self.normalize_url(x), '')
        )
        
        # Prepare the report
        report = []
        for _, row in non_200_links.iterrows():
            report.append({
                'Source URL': row['From'],
                'Target URL': row['To'],
                'Status Code': row['Target Status'],
                'Redirect Target': row['Redirect Target'],
                'Anchor Text': row.get('Anchor Text', ''),
                'Link Location': row.get('Link Position', ''),
                'Recommendation': (
                    f"Update link to point directly to {row['Redirect Target']}"
                    if row['Redirect Target'] and row['Target Status'] in [301, 302]
                    else f"Fix broken link (Status: {row['Target Status']})"
                )
            })
        
        return pd.DataFrame(report)
    
    def generate_recommendations(self) -> pd.DataFrame:
        """Generate specific linking recommendations."""
        logger.info("Generating recommendations...")
        
        recommendations = []
        orphaned_pages = self.find_orphaned_content()
        
        for _, orphan in orphaned_pages.iterrows():
            # Find potential source pages with high PageRank
            potential_sources = [
                node for node in self.graph.nodes()
                if self.pagerank_scores.get(node, 0) > 0.001
                and node != orphan['URL']
            ]
            
            for source in potential_sources:
                # Generate suggested anchor text based on target page title/H1
                anchor_text = orphan['H1'] if orphan['H1'] else orphan['Title']
                
                recommendations.append({
                    'Source URL': source,
                    'Target URL': orphan['URL'],
                    'Suggested Anchor': anchor_text,
                    'Impact Score': self.pagerank_scores.get(source, 0) * 0.5,
                    'Source PageRank': self.pagerank_scores.get(source, 0),
                    'Target PageRank': self.pagerank_scores.get(orphan['URL'], 0)
                })
        
        return pd.DataFrame(recommendations)
    
    def generate_reports(self, output_path: str):
        """Generate all analysis reports and save to Excel."""
        logger.info("Generating reports...")
        
        # Create PageRank analysis
        pagerank_analysis = pd.DataFrame([
            {
                'URL': node,
                'PageRank': score,
                'Inbound Links': self.graph.in_degree(node),
                'Outbound Links': self.graph.out_degree(node),
                'Title': self.graph.nodes[node].get('title', ''),
                'H1': self.graph.nodes[node].get('h1', ''),
                'Word Count': self.graph.nodes[node].get('word_count', 0)
            }
            for node, score in self.pagerank_scores.items()
        ])
        
        # Generate other reports
        optimization_recommendations = self.generate_recommendations()
        orphaned_content = self.find_orphaned_content()
        authority_leaks = self.find_authority_leaks()
        non_200_links = self.find_non_200_links()
        
        # Save to Excel
        with pd.ExcelWriter(output_path) as writer:
            pagerank_analysis.to_excel(writer, sheet_name='pagerank_analysis', index=False)
            optimization_recommendations.to_excel(writer, sheet_name='optimization_recommendations', index=False)
            orphaned_content.to_excel(writer, sheet_name='orphaned_content', index=False)
            authority_leaks.to_excel(writer, sheet_name='authority_leaks', index=False)
            non_200_links.to_excel(writer, sheet_name='non_200_links', index=False)
        
        logger.info(f"Reports saved to {output_path}")

def main():
    parser = argparse.ArgumentParser(description='Internal Linking Optimizer')
    parser.add_argument('--internal-all', required=True, help='Path to internal_all.csv')
    parser.add_argument('--all-inlinks', required=True, help='Path to all_inlinks.csv')
    parser.add_argument('--output', required=True, help='Path for output Excel file')
    parser.add_argument('--sitemaps', nargs='+', default=[
        "https://www.example.com/sitemap.xml",
        "https://www.example.com/templates-sitemap.xml",
    ], help='Sitemap URLs')
    
    args = parser.parse_args()
    
    optimizer = InternalLinkingOptimizer(args.internal_all, args.all_inlinks, args.sitemaps)
    
    # Process data
    inlinks_df = optimizer.load_data()
    optimizer.build_graph(inlinks_df)
    optimizer.calculate_pagerank()
    
    # Generate reports
    optimizer.generate_reports(args.output)

if __name__ == '__main__':
    main() 
