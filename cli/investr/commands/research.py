from pathlib import Path

import click
from investr.client import api_post, api_get


@click.group()
def research():
    """Manage research reports and citations"""
    pass


@research.command("upload-report")
@click.option("--stock-id", required=True, help="Stock UUID")
@click.option("--phase", required=True, help="Report phase (0-9, synthesis)")
@click.option("--title", required=True, help="Report title")
@click.option("--file", "filepath", type=click.Path(exists=True), required=True, help="Markdown file path")
@click.option("--signal-rating", help="Signal rating (e.g. 🟢🟢🟢)")
@click.option("--confidence", type=click.Choice(["H", "M", "L"]), help="Confidence level")
@click.option("--intensity", type=click.IntRange(1, 10), help="Signal intensity 1-10")
@click.option("--core-thesis", help="Core investment thesis")
def upload_report(stock_id, phase, title, filepath, signal_rating, confidence, intensity, core_thesis):
    """Upload a research report from a markdown file"""
    content = Path(filepath).read_text(encoding="utf-8")
    body = {"stock_id": stock_id, "phase": phase, "title": title, "content": content}
    if signal_rating:
        body["signal_rating"] = signal_rating
    if confidence:
        body["confidence"] = confidence
    if intensity:
        body["intensity"] = intensity
    if core_thesis:
        body["core_thesis"] = core_thesis

    result = api_post("/research/reports", body)
    click.echo(f"Report uploaded: {result['id']}")
    click.echo(f"  Stock: {result.get('stock', {}).get('ticker', 'N/A')}")
    click.echo(f"  Phase: {result['phase']} | Title: {result['title']}")


@research.command("upload-citations")
@click.option("--report-id", required=True, help="Research report UUID")
@click.option("--file", "filepath", type=click.Path(exists=True), required=True, help="Citations file (one per line: author | date | title | url | quality)")
def upload_citations(report_id, filepath):
    """Batch upload citations for a report"""
    citations = []
    for line in Path(filepath).read_text(encoding="utf-8").strip().split("\n"):
        parts = [p.strip() for p in line.split("|")]
        if len(parts) >= 4:
            citations.append({
                "author_org": parts[0],
                "publication_date": parts[1] if parts[1] else None,
                "source_title": parts[2],
                "url": parts[3] if len(parts) > 3 and parts[3] else None,
                "quality_rating": parts[4] if len(parts) > 4 else "C",
            })

    if not citations:
        click.echo("No citations found in file")
        return

    result = api_post(f"/research/reports/{report_id}/citations/batch", citations)
    click.echo(f"Uploaded {len(result)} citations to report {report_id}")


@research.command("list-reports")
@click.option("--stock-id", help="Filter by stock UUID")
@click.option("--phase", help="Filter by phase")
def list_reports(stock_id, phase):
    """List research reports"""
    params = []
    if stock_id:
        params.append(f"stock_id={stock_id}")
    if phase:
        params.append(f"phase={phase}")
    qs = "?" + "&".join(params) if params else ""
    result = api_get(f"/research/reports{qs}")
    for r in result["items"]:
        click.echo(f"  [{r['phase']:10s}] {r['title']:40s} {r.get('stock', {}).get('ticker', '')}  {r['id']}")
    click.echo(f"Total: {result['total']}")
