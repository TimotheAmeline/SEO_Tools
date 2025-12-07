# Configuration for SEO Optimizer (GSC Edition)

# CTR Benchmarks by position (Backlinko 2023 data)
CTR_BENCHMARKS = {
    1: 0.275,  # 27.5%
    2: 0.156,  # 15.6%
    3: 0.107,  # 10.7%
    4: 0.075,  # 7.5%
    5: 0.057,  # 5.7%
    6: 0.046,  # 4.6%
    7: 0.037,  # 3.7%
    8: 0.031,  # 3.1%
    9: 0.026,  # 2.6%
    10: 0.022, # 2.2%
    # Position 11-20
    'page2': 0.01,  # ~1%
    # Position 21+
    'page3+': 0.003  # ~0.3%
}

# Opportunity Detection Thresholds
THRESHOLDS = {
    # CTR must be this % below benchmark to flag
    'ctr_underperformance_ratio': 0.7,  # 30% below benchmark
    
    # Minimum impressions to consider (avoid noise)
    'min_impressions': 100,
    
    # Query match thresholds
    'title_match_threshold': 0.4,  # Min % of query words that should be in title
    'meta_match_threshold': 0.3,   # Min % of query words that should be in meta
}

# GSC API Settings
GSC_CONFIG = {
    'site_url': 'sc-domain:example.com',  # Update this to match your GSC property exactly
    'date_range_days': 90,  # Last 3 months of data
}

# Export Settings
EXPORT_CONFIG = {
    'max_quick_wins': 20,  # Max quick wins to export separately
    'max_recommendations_per_url': 5,  # Max recommendations per URL in report
    'min_score_to_export': 10,  # Minimum opportunity score to include
}