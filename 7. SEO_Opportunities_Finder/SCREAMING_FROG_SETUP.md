Screaming Frog Setup Guide
Quick Export Instructions
Open Screaming Frog
Crawl your site: Enter https://www.example.com and click Start
Wait for crawl to complete
Export the right data:
Go to: Internal tab
Click: Export button
Choose: Export All
Save as: data/inputs/screaming_frog_export.csv
Recommended Screaming Frog Settings
Before crawling, configure these for better data:

Configuration > Spider > Crawl
✅ Crawl Internal Links
✅ Crawl Canonicals
✅ Crawl Pagination
Configuration > Spider > Extraction
✅ Page Titles
✅ Meta Description
✅ H1
✅ H2
✅ Word Count
Configuration > Speed
Max Threads: 5 (be nice to your server)
Max URI/s: 2
What the Tool Uses from Screaming Frog
Title tags - To match against ranking queries
Meta descriptions - To identify optimization opportunities
H1s - For content relevance analysis
Word count - To identify thin content
Status codes - To filter only live pages
Indexability - To focus on indexable pages only
Alternative: API Mode (If Available)
If you have Screaming Frog with API access:

bash
# Command line crawl
screamingfrog --crawl https://www.example.com --export-tabs "Internal:All" --output-folder ./data/inputs/
No Screaming Frog? No Problem!
The tool works with GSC data only. You'll miss:

Title/meta optimization opportunities
Content depth analysis
Technical issues
But you'll still get:

CTR optimization opportunities
Position-based opportunities
Query-based insights
