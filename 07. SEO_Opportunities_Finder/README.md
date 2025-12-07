SEO Performance Optimizer
A Python tool that identifies SEO optimization opportunities by analyzing Google Search Console data and Screaming Frog crawls.

What It Does
Finds CTR optimization opportunities - Pages ranking well but with poor CTR
Identifies striking distance pages - Pages ranking 4-10 that can reach top 3
Spots page 2 opportunities - Pages stuck on page 2 that need work
Detects title/meta mismatches - When your metadata doesn't match what you rank for
Highlights content gaps - Thin content that needs expansion
Setup
1. Install Requirements
bash
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
2. Set Up Google Search Console Access
Create OAuth credentials:

bash
python quick_auth.py
Or use the service account method (see main guide).

3. Configure the Tool
Edit config.py:

python
'site_url': 'https://www.example.com',  # Your exact GSC property
4. (Optional) Add Screaming Frog Data
See SCREAMING_FROG_SETUP.md for instructions.

Usage
bash
python src/main.py
Output Files
data/outputs/seo_opportunities.csv - All opportunities ranked by score
data/outputs/opportunity_report.txt - Detailed recommendations
data/outputs/quick_wins.csv - Easy fixes you can do today
Understanding the Scores
50+ = High priority, significant traffic opportunity
25-50 = Medium priority, worth doing
10-25 = Low priority, do if you have time
Quick Wins vs Long-term
Quick Wins (can do today):

Title tag updates
Meta description rewrites
Long-term (need more effort):

Content expansion
Moving from page 2 to page 1
Customization
Adjust thresholds in config.py:

min_impressions: Minimum impressions to consider (default: 100)
ctr_underperformance_ratio: How much below benchmark (default: 0.7 = 30% below)
