import click
from investr.client import api_post, api_get


@click.group()
def portfolio():
    """Manage portfolios and holdings"""
    pass


@portfolio.command("add-holding")
@click.option("--portfolio-id", required=True, help="Portfolio UUID")
@click.option("--stock-id", required=True, help="Stock UUID")
@click.option("--cost-basis", required=True, type=float, help="Cost basis per share")
@click.option("--position-percent", required=True, type=float, help="Position percentage (0-100)")
@click.option("--entry-date", help="Entry date (YYYY-MM-DD)")
@click.option("--notes", help="Optional notes")
def add_holding(portfolio_id, stock_id, cost_basis, position_percent, entry_date, notes):
    """Add a holding to a portfolio"""
    body = {
        "stock_id": stock_id, "cost_basis": cost_basis,
        "position_percent": position_percent,
    }
    if entry_date:
        body["entry_date"] = entry_date
    if notes:
        body["notes"] = notes
    result = api_post(f"/portfolios/{portfolio_id}/holdings", body)
    click.echo(f"Holding added: {result['id']} - {result['ticker']}")
