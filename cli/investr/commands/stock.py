import click
from investr.client import api_post, api_get


@click.group()
def stock():
    """Manage stocks"""
    pass


@stock.command("register")
@click.option("--ticker", required=True, help="Stock ticker symbol")
@click.option("--name", required=True, help="Company name")
@click.option("--market", required=True, type=click.Choice(["A-share", "US", "HK"]))
@click.option("--sector", help="Sector classification")
@click.option("--industry", help="Industry classification")
def register(ticker, name, market, sector, industry):
    """Register a new stock"""
    try:
        result = api_post("/stocks", {
            "ticker": ticker, "name": name, "market": market,
            "sector": sector, "industry": industry,
        })
        click.echo(f"Stock registered: {result['id']} - {result['ticker']} {result['name']}")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)


@stock.command("search")
@click.argument("query")
@click.option("--market", type=click.Choice(["A-share", "US", "HK"]))
def search(query, market):
    """Search stocks by ticker or name"""
    params = f"q={query}"
    if market:
        params += f"&market={market}"
    result = api_get(f"/stocks?{params}")
    for s in result["items"]:
        click.echo(f"  {s['ticker']:12s} {s['name']:20s} [{s['market']}] {s['id']}")
    click.echo(f"Total: {result['total']}")
