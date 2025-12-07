"""
CLI module for SEO Auto QA tool.
Handles command-line interface and user interaction.
"""

import click
import asyncio
import yaml
import logging
from typing import List, Optional
from datetime import datetime, timedelta
from .crawler import SEOCrawler
from .storage import Storage
from .comparator import SEOComparator
from .reporter import SEOReporter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@click.group()
def cli():
    """SEO Auto QA - Automated SEO Quality Assurance Testing Tool"""
    pass

@cli.command()
@click.option('--config', '-c', default='config.yaml', help='Path to configuration file')
def init(config: str):
    """Initialize the SEO Auto QA tool with configuration."""
    try:
        # Create default config if it doesn't exist
        with open(config, 'w') as f:
            yaml.dump({
                'crawler': {
                    'max_pages': 100,
                    'timeout': 30000,
                    'user_agent': 'SEO Auto QA Bot/1.0',
                    'javascript_enabled': True,
                    'wait_for_network_idle': True,
                    'viewport': {
                        'width': 1920,
                        'height': 1080
                    }
                },
                'storage': {
                    'database_url': 'sqlite:///seo_qa.db',
                    'history_retention_days': 90
                },
                'monitoring': {
                    'urls': ['https://example.com'],
                    'crawl_frequency': 'daily',
                    'alert_thresholds': {
                        'critical': {
                            'title_change': True,
                            'meta_description_change': True,
                            'h1_change': True,
                            'canonical_change': True
                        },
                        'warning': {
                            'h2_change': True,
                            'image_alt_change': True,
                            'internal_link_change': True
                        },
                        'info': {
                            'h3_change': True,
                            'schema_change': True
                        }
                    }
                },
                'notifications': {
                    'email': {
                        'enabled': False,
                        'smtp_server': '',
                        'smtp_port': 587,
                        'sender_email': '',
                        'recipient_emails': []
                    },
                    'slack': {
                        'enabled': False,
                        'webhook_url': ''
                    }
                },
                'performance': {
                    'core_web_vitals': {
                        'lcp_threshold': 2.5,
                        'cls_threshold': 0.1,
                        'fid_threshold': 100
                    }
                },
                'element_weights': {
                    'title': 1.0,
                    'meta_description': 0.9,
                    'h1': 0.8,
                    'canonical': 0.8,
                    'h2': 0.6,
                    'h3': 0.4,
                    'image_alt': 0.5,
                    'internal_links': 0.7,
                    'schema': 0.6
                }
            }, f, default_flow_style=False)
        
        click.echo(f"Configuration file created at {config}")
        
        # Initialize storage
        storage = Storage(config)
        click.echo("Storage initialized")
        
    except Exception as e:
        logger.error(f"Failed to initialize: {e}")
        raise click.ClickException(str(e))

@cli.command()
@click.option('--config', '-c', default='config.yaml', help='Path to configuration file')
@click.option('--url', '-u', help='URL to capture baseline for')
def baseline(config: str, url: Optional[str]):
    """Capture baseline SEO data for specified URLs."""
    try:
        # Load configuration
        with open(config, 'r') as f:
            config_data = yaml.safe_load(f)
        
        # Get URLs to process
        urls = [url] if url else config_data['monitoring']['urls']
        
        # Initialize components
        crawler = SEOCrawler(config)
        storage = Storage(config)
        
        async def process_url(url: str):
            try:
                # Crawl page
                seo_data = await crawler.crawl_page(url)
                
                # Save snapshot
                snapshot_id = storage.save_snapshot(seo_data)
                
                click.echo(f"Baseline captured for {url} (ID: {snapshot_id})")
            except Exception as e:
                logger.error(f"Failed to process {url}: {e}")
        
        # Process URLs
        asyncio.run(crawler.initialize())
        for url in urls:
            asyncio.run(process_url(url))
        asyncio.run(crawler.close())
        
    except Exception as e:
        logger.error(f"Failed to capture baseline: {e}")
        raise click.ClickException(str(e))

@cli.command()
@click.option('--config', '-c', default='config.yaml', help='Path to configuration file')
@click.option('--url', '-u', help='URL to compare')
@click.option('--format', '-f', type=click.Choice(['json', 'html']), default='json', help='Report format')
def compare(config: str, url: Optional[str], format: str):
    """Compare current state against baseline and generate report."""
    try:
        # Load configuration
        with open(config, 'r') as f:
            config_data = yaml.safe_load(f)
        
        # Get URLs to process
        urls = [url] if url else config_data['monitoring']['urls']
        
        # Initialize components
        crawler = SEOCrawler(config)
        storage = Storage(config)
        comparator = SEOComparator(config)
        reporter = SEOReporter(config)
        
        async def process_url(url: str):
            try:
                # Get baseline
                baseline = storage.get_latest_snapshot(url)
                if not baseline:
                    click.echo(f"No baseline found for {url}")
                    return
                
                # Crawl current state
                current = await crawler.crawl_page(url)
                
                # Compare snapshots
                changes = comparator.compare_snapshots(baseline, current)
                
                # Generate report
                report = reporter.generate_report(url, current, changes)
                
                # Print report
                reporter.print_report(report)
                
                # Save report
                report_file = reporter.save_report(report, format)
                click.echo(f"Report saved to {report_file}")
                
                # Send notifications
                await reporter.send_notifications(report)
                
            except Exception as e:
                logger.error(f"Failed to process {url}: {e}")
        
        # Process URLs
        asyncio.run(crawler.initialize())
        for url in urls:
            asyncio.run(process_url(url))
        asyncio.run(crawler.close())
        
    except Exception as e:
        logger.error(f"Failed to compare: {e}")
        raise click.ClickException(str(e))

@cli.command()
@click.option('--config', '-c', default='config.yaml', help='Path to configuration file')
@click.option('--days', '-d', type=int, help='Number of days of history to show')
def history(config: str, days: Optional[int]):
    """View historical changes."""
    try:
        # Initialize storage
        storage = Storage(config)
        
        # Get all snapshots
        session = storage.Session()
        try:
            snapshots = session.query(storage.PageSnapshot)\
                .order_by(storage.PageSnapshot.timestamp.desc())\
                .all()
            
            if days:
                cutoff_date = datetime.utcnow() - timedelta(days=days)
                snapshots = [s for s in snapshots if s.timestamp >= cutoff_date]
            
            # Display history
            for snapshot in snapshots:
                click.echo(f"\nSnapshot for {snapshot.url}")
                click.echo(f"Date: {snapshot.timestamp}")
                click.echo(f"Status Code: {snapshot.status_code}")
                
                # Get changes
                changes = storage.get_changes(snapshot.id)
                if changes:
                    click.echo("\nChanges:")
                    for change in changes:
                        click.echo(f"- {change['element_type']} ({change['change_type']})")
                        click.echo(f"  Old: {change['old_value']}")
                        click.echo(f"  New: {change['new_value']}")
                else:
                    click.echo("No changes detected")
                
                click.echo("-" * 50)
            
        finally:
            session.close()
        
    except Exception as e:
        logger.error(f"Failed to show history: {e}")
        raise click.ClickException(str(e))

@cli.command()
@click.option('--config', '-c', default='config.yaml', help='Path to configuration file')
def cleanup(config: str):
    """Clean up old data based on retention period."""
    try:
        # Initialize storage
        storage = Storage(config)
        
        # Clean up old data
        storage.cleanup_old_data()
        click.echo("Cleanup completed")
        
    except Exception as e:
        logger.error(f"Failed to cleanup: {e}")
        raise click.ClickException(str(e))

if __name__ == '__main__':
    cli() 