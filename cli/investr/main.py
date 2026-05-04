import os
import sys
from pathlib import Path

import click

from investr.commands import research, stock, portfolio, report

CONFIG_DIR = Path.home() / ".investr"
CONFIG_FILE = CONFIG_DIR / "config"


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """Investr - Investment Manager CLI"""
    pass


# Setup command
@cli.command()
@click.option("--api-url", default="http://localhost:8000/api/v1", help="API base URL")
@click.option("--api-key", prompt=True, hide_input=True, help="Your API key from the web UI")
def setup(api_url, api_key):
    """Configure API URL and key"""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        f.write(f"api_url={api_url}\n")
        f.write(f"api_key={api_key}\n")
    click.echo(f"Configuration saved to {CONFIG_FILE}")


# Register subcommand groups
cli.add_command(stock.stock)
cli.add_command(portfolio.portfolio)
cli.add_command(research.research)
cli.add_command(report.report)


if __name__ == "__main__":
    cli()
