from pathlib import Path

import click
from investr.client import api_post, api_get


@click.group()
def report():
    """Manage morning and synthesis reports"""
    pass


@report.command("morning")
@click.option("--date", "report_date", required=True, help="Report date (YYYY-MM-DD)")
@click.option("--html-file", "filepath", type=click.Path(exists=True), required=True, help="HTML file path")
@click.option("--headline", help="Report headline")
def morning(report_date, filepath, headline):
    """Upload a morning report from an HTML file"""
    html_content = Path(filepath).read_text(encoding="utf-8")
    body = {"report_date": report_date, "html_content": html_content}
    if headline:
        body["headline"] = headline

    result = api_post("/reports/morning", body)
    click.echo(f"Morning report uploaded: {result['id']} for {result['report_date']}")


@report.command("synthesis")
@click.option("--title", required=True, help="Report title")
@click.option("--file", "filepath", type=click.Path(exists=True), required=True, help="Markdown file path")
@click.option("--signal-rating", help="Signal rating")
@click.option("--confidence", type=click.Choice(["H", "M", "L"]), help="Confidence level")
def synthesis(title, filepath, signal_rating, confidence):
    """Upload a synthesis report from a markdown file"""
    content = Path(filepath).read_text(encoding="utf-8")
    body = {"title": title, "content": content}
    if signal_rating:
        body["signal_rating"] = signal_rating
    if confidence:
        body["confidence"] = confidence

    result = api_post("/reports/synthesis", body)
    click.echo(f"Synthesis report uploaded: {result['id']}")
