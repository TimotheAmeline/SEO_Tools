"""
Reporter module for SEO Auto QA tool.
Handles report generation and notifications.
"""

import json
from typing import Dict, List, Optional
import yaml
import logging
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import aiohttp
import asyncio

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SEOReporter:
    def __init__(self, config_path: str = "config.yaml"):
        """Initialize the reporter with configuration."""
        self.config = self._load_config(config_path)
        self.console = Console()

    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from YAML file."""
        try:
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            raise

    def generate_report(self, url: str, snapshot: Dict, changes: List[Dict]) -> Dict:
        """
        Generate a comprehensive report of changes.
        
        Args:
            url: The URL being analyzed
            snapshot: Current snapshot data
            changes: List of detected changes
            
        Returns:
            Dictionary containing the report data
        """
        report = {
            'url': url,
            'timestamp': datetime.utcnow().isoformat(),
            'snapshot_timestamp': snapshot['timestamp'],
            'status_code': snapshot['status_code'],
            'changes': changes,
            'summary': self._generate_summary(changes),
            'performance': snapshot['performance']
        }
        
        return report

    def _generate_summary(self, changes: List[Dict]) -> Dict:
        """Generate a summary of changes by type."""
        summary = {
            'critical': 0,
            'warning': 0,
            'info': 0,
            'total': len(changes)
        }
        
        for change in changes:
            summary[change['change_type']] += 1
        
        return summary

    def print_report(self, report: Dict) -> None:
        """Print a formatted report to the console."""
        self.console.print(Panel.fit(
            f"[bold]SEO Change Report: {report['url']}[/bold]\n"
            f"Date: {report['timestamp']}\n"
            f"Baseline: {report['snapshot_timestamp']}"
        ))

        # Print summary
        summary = report['summary']
        self.console.print("\n[bold]Summary:[/bold]")
        self.console.print(f"Total Changes: {summary['total']}")
        self.console.print(f"Critical: {summary['critical']}")
        self.console.print(f"Warnings: {summary['warning']}")
        self.console.print(f"Info: {summary['info']}")

        # Print changes
        if report['changes']:
            self.console.print("\n[bold]Changes:[/bold]")
            for change in report['changes']:
                self._print_change(change)

        # Print performance metrics
        if report['performance']:
            self.console.print("\n[bold]Performance Metrics:[/bold]")
            self._print_performance(report['performance'])

    def _print_change(self, change: Dict) -> None:
        """Print a single change in a formatted way."""
        change_type = change['change_type']
        color = {
            'critical': 'red',
            'warning': 'yellow',
            'info': 'blue'
        }.get(change_type, 'white')

        self.console.print(f"\n[{color}][{change_type.upper()}] {change['element_type']}[/{color}]")
        
        if change['old_value'] is not None:
            self.console.print(f"Old: {change['old_value']}")
        if change['new_value'] is not None:
            self.console.print(f"New: {change['new_value']}")
        
        self.console.print(f"Impact Score: {change['impact_score']:.2f}")

    def _print_performance(self, performance: Dict) -> None:
        """Print performance metrics in a formatted way."""
        table = Table(show_header=True, header_style="bold")
        table.add_column("Metric")
        table.add_column("Value")
        table.add_column("Status")

        for metric, value in performance.items():
            status = self._get_performance_status(metric, value)
            table.add_row(
                metric.upper(),
                f"{value:.2f}",
                status
            )

        self.console.print(table)

    def _get_performance_status(self, metric: str, value: float) -> str:
        """Get the status of a performance metric."""
        thresholds = self.config['performance']['core_web_vitals']
        
        if metric == 'lcp':
            if value <= thresholds['lcp_threshold']:
                return "[green]Good[/green]"
            return "[red]Poor[/red]"
        elif metric == 'cls':
            if value <= thresholds['cls_threshold']:
                return "[green]Good[/green]"
            return "[red]Poor[/red]"
        elif metric == 'fid':
            if value <= thresholds['fid_threshold']:
                return "[green]Good[/green]"
            return "[red]Poor[/red]"
        
        return "[yellow]Unknown[/yellow]"

    def save_report(self, report: Dict, format: str = 'json') -> str:
        """
        Save the report to a file.
        
        Args:
            report: The report data
            format: Output format ('json' or 'html')
            
        Returns:
            Path to the saved report file
        """
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        filename = f"seo_report_{timestamp}.{format}"
        
        if format == 'json':
            with open(filename, 'w') as f:
                json.dump(report, f, indent=2)
        elif format == 'html':
            self._save_html_report(report, filename)
        else:
            raise ValueError(f"Unsupported format: {format}")
        
        return filename

    def _save_html_report(self, report: Dict, filename: str) -> None:
        """Save the report in HTML format."""
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>SEO Change Report - {report['url']}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .critical {{ color: red; }}
                .warning {{ color: orange; }}
                .info {{ color: blue; }}
                .summary {{ margin: 20px 0; }}
                .change {{ margin: 10px 0; padding: 10px; border: 1px solid #ddd; }}
                .performance {{ margin: 20px 0; }}
                table {{ border-collapse: collapse; width: 100%; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
            </style>
        </head>
        <body>
            <h1>SEO Change Report</h1>
            <p>URL: {report['url']}</p>
            <p>Date: {report['timestamp']}</p>
            <p>Baseline: {report['snapshot_timestamp']}</p>
            
            <div class="summary">
                <h2>Summary</h2>
                <p>Total Changes: {report['summary']['total']}</p>
                <p>Critical: {report['summary']['critical']}</p>
                <p>Warnings: {report['summary']['warning']}</p>
                <p>Info: {report['summary']['info']}</p>
            </div>
            
            <div class="changes">
                <h2>Changes</h2>
        """
        
        for change in report['changes']:
            html += f"""
                <div class="change">
                    <h3 class="{change['change_type']}">{change['element_type']}</h3>
                    <p>Type: {change['change_type']}</p>
                    <p>Old Value: {change['old_value']}</p>
                    <p>New Value: {change['new_value']}</p>
                    <p>Impact Score: {change['impact_score']:.2f}</p>
                </div>
            """
        
        if report['performance']:
            html += """
                <div class="performance">
                    <h2>Performance Metrics</h2>
                    <table>
                        <tr>
                            <th>Metric</th>
                            <th>Value</th>
                            <th>Status</th>
                        </tr>
            """
            
            for metric, value in report['performance'].items():
                status = self._get_performance_status(metric, value)
                html += f"""
                        <tr>
                            <td>{metric.upper()}</td>
                            <td>{value:.2f}</td>
                            <td>{status}</td>
                        </tr>
                """
            
            html += """
                    </table>
                </div>
            """
        
        html += """
            </div>
        </body>
        </html>
        """
        
        with open(filename, 'w') as f:
            f.write(html)

    async def send_notifications(self, report: Dict) -> None:
        """Send notifications based on the report."""
        if self.config['notifications']['email']['enabled']:
            await self._send_email_notification(report)
        
        if self.config['notifications']['slack']['enabled']:
            await self._send_slack_notification(report)

    async def _send_email_notification(self, report: Dict) -> None:
        """Send email notification."""
        email_config = self.config['notifications']['email']
        
        msg = MIMEMultipart()
        msg['Subject'] = f"SEO Change Alert: {report['url']}"
        msg['From'] = email_config['sender_email']
        msg['To'] = ', '.join(email_config['recipient_emails'])
        
        # Create email body
        body = f"""
        SEO Change Report for {report['url']}
        
        Date: {report['timestamp']}
        Baseline: {report['snapshot_timestamp']}
        
        Summary:
        - Total Changes: {report['summary']['total']}
        - Critical: {report['summary']['critical']}
        - Warnings: {report['summary']['warning']}
        - Info: {report['summary']['info']}
        
        Critical Changes:
        """
        
        for change in report['changes']:
            if change['change_type'] == 'critical':
                body += f"""
                - {change['element_type']}
                  Old: {change['old_value']}
                  New: {change['new_value']}
                """
        
        msg.attach(MIMEText(body, 'plain'))
        
        try:
            with smtplib.SMTP(email_config['smtp_server'], email_config['smtp_port']) as server:
                server.starttls()
                server.send_message(msg)
        except Exception as e:
            logger.error(f"Failed to send email notification: {e}")

    async def _send_slack_notification(self, report: Dict) -> None:
        """Send Slack notification."""
        webhook_url = self.config['notifications']['slack']['webhook_url']
        
        # Create Slack message
        message = {
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"SEO Change Alert: {report['url']}"
                    }
                },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*Total Changes:*\n{report['summary']['total']}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Critical:*\n{report['summary']['critical']}"
                        }
                    ]
                }
            ]
        }
        
        # Add critical changes
        for change in report['changes']:
            if change['change_type'] == 'critical':
                message["blocks"].append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*{change['element_type']}*\nOld: {change['old_value']}\nNew: {change['new_value']}"
                    }
                })
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(webhook_url, json=message) as response:
                    if response.status != 200:
                        logger.error(f"Failed to send Slack notification: {response.status}")
        except Exception as e:
            logger.error(f"Failed to send Slack notification: {e}") 