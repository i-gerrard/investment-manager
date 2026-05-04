#!/usr/bin/env python3
"""
sync_brokers.py — reads eToro and Trade Republic positions via Playwright
and POSTs them to the investment-manager backend.

Usage:
  python scripts/sync_brokers.py [--broker etoro|tr|all] [--api http://localhost:8000/api/v1] [--token <jwt>]

Browser sessions are persisted in ~/.investment-manager/browser-sessions/
so you only need to log in once per broker.
"""

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Optional

import httpx
from playwright.async_api import Page, async_playwright

# ── Config ────────────────────────────────────────────────────────────────────

SESSION_DIR = Path.home() / ".investment-manager" / "browser-sessions"
SESSION_DIR.mkdir(parents=True, exist_ok=True)

ETORO_URL = "https://www.etoro.com/portfolio"
TR_URL = "https://app.traderepublic.com/portfolio?timeframe=1d"

API_BASE = os.environ.get("INVESTMENT_MANAGER_API", "http://localhost:8000/api/v1")
API_TOKEN = os.environ.get("INVESTMENT_MANAGER_TOKEN", "")


# ── eToro reader ──────────────────────────────────────────────────────────────

async def read_etoro(page: Page) -> list[dict]:
    print("[eToro] Navigating...")
    await page.goto(ETORO_URL, wait_until="networkidle", timeout=30_000)

    # Detect login wall
    if "/login" in page.url or "login" in page.url:
        print("[eToro] ⚠️  Not logged in. Please log in to eToro in the browser window, then press Enter.")
        input()
        await page.goto(ETORO_URL, wait_until="networkidle", timeout=30_000)
        if "/login" in page.url:
            print("[eToro] Still not logged in — skipping.")
            return []

    await page.wait_for_timeout(2000)

    positions = {}

    async def _snapshot_and_extract():
        """Extract visible positions from the accessibility tree."""
        # Try to grab position rows via evaluate — more reliable than snapshot parsing
        data = await page.evaluate("""() => {
            const rows = [];
            // eToro renders each holding as a data-etoro-automation-id="portfolio-overview-item"
            const items = document.querySelectorAll('[data-etoro-automation-id="portfolio-overview-item"]');
            items.forEach(item => {
                const ticker = item.querySelector('[data-etoro-automation-id="portfolio-overview-instrument-symbol"]')?.innerText?.trim();
                const name = item.querySelector('[data-etoro-automation-id="portfolio-overview-instrument-name"]')?.innerText?.trim();
                const invested = item.querySelector('[data-etoro-automation-id="portfolio-overview-total-invested"]')?.innerText?.trim();
                const value = item.querySelector('[data-etoro-automation-id="portfolio-overview-value"]')?.innerText?.trim();
                const pnl = item.querySelector('[data-etoro-automation-id="portfolio-overview-profit"]')?.innerText?.trim();
                const units = item.querySelector('[data-etoro-automation-id="portfolio-overview-units"]')?.innerText?.trim();
                if (ticker) rows.push({ ticker, name, invested, value, pnl, units });
            });
            return rows;
        }""")
        return data

    # Scroll loop inside eToro's internal scroll container
    prev_count = 0
    for _ in range(20):
        raw = await _snapshot_and_extract()
        for r in raw:
            if r.get("ticker"):
                positions[r["ticker"]] = r

        if len(positions) == prev_count and prev_count > 0:
            break
        prev_count = len(positions)

        reached_bottom = await page.evaluate("""() => {
            const el = document.querySelector('.et-layout-scrollable-page');
            if (!el) return true;
            el.scrollBy(0, 600);
            return el.scrollTop + el.clientHeight >= el.scrollHeight - 10;
        }""")
        await page.wait_for_timeout(600)
        if reached_bottom:
            break

    print(f"[eToro] Read {len(positions)} positions.")

    result = []
    for ticker, r in positions.items():
        def _parse_number(s: Optional[str]) -> Optional[float]:
            if not s:
                return None
            import re
            m = re.search(r"[-\d,.]+", s.replace(",", ""))
            return float(m.group()) if m else None

        market_value = _parse_number(r.get("value")) or 0.0
        invested = _parse_number(r.get("invested"))
        units_str = r.get("units", "")
        quantity = _parse_number(units_str) or 1.0
        pnl_str = r.get("pnl", "")
        pnl_pct: Optional[float] = None
        if "%" in (pnl_str or ""):
            pnl_pct = _parse_number(pnl_str)

        result.append({
            "ticker": ticker,
            "name": r.get("name") or ticker,
            "quantity": quantity,
            "current_price": round(market_value / quantity, 4) if quantity else 0.0,
            "avg_cost": round(invested / quantity, 4) if (invested and quantity) else None,
            "market_value": market_value,
            "pnl_pct": pnl_pct,
            "currency": "USD",
        })

    return result


# ── Trade Republic reader ─────────────────────────────────────────────────────

async def read_tr(page: Page) -> list[dict]:
    print("[TR] Navigating...")
    await page.goto(TR_URL, wait_until="networkidle", timeout=30_000)

    if "signin" in page.url or "login" in page.url:
        print("[TR] ⚠️  Not logged in. Please log in to Trade Republic in the browser window, then press Enter.")
        input()
        await page.goto(TR_URL, wait_until="networkidle", timeout=30_000)
        if "signin" in page.url or "login" in page.url:
            print("[TR] Still not logged in — skipping.")
            return []

    await page.wait_for_timeout(2000)

    # Switch to "Since buy (€)" view using JS (avoids brittle click targeting)
    await page.evaluate("""() => {
        const btn = Array.from(document.querySelectorAll('button'))
            .find(b => b.innerText.trim().startsWith('Daily trend') || b.innerText.trim().startsWith('Tagesveränderung'));
        if (btn) btn.click();
    }""")
    await page.wait_for_timeout(500)

    await page.evaluate("""() => {
        const items = Array.from(document.querySelectorAll('li, [role="option"], [role="menuitem"]'));
        const target = items.find(el => el.innerText && (
            el.innerText.trim() === 'Since buy (\\u20ac)' ||
            el.innerText.trim() === 'Seit Kauf (\\u20ac)'
        ));
        if (target) target.click();
    }""")
    await page.wait_for_timeout(800)

    positions = {}

    async def _extract():
        return await page.evaluate("""() => {
            const rows = [];
            // Each TR position is rendered as a portfolio-instrument-row or similar
            const items = document.querySelectorAll('[data-testid="portfolio-instrument-row"], .portfolioInstrumentRow, .instrument-row');
            if (items.length === 0) {
                // Fallback: parse the visible text using structure heuristics
                // TR renders name + ticker + value + change in a predictable grid
                const cards = document.querySelectorAll('[class*="instrumentName"], [class*="InstrumentName"]');
                cards.forEach(el => {
                    const parent = el.closest('[class*="instrument"], [class*="Instrument"]');
                    if (!parent) return;
                    const name = el.innerText.trim();
                    const tickerEl = parent.querySelector('[class*="isin"], [class*="ticker"], [class*="Ticker"]');
                    const ticker = tickerEl?.innerText?.trim() || '';
                    const valueEl = parent.querySelector('[class*="amount"], [class*="Amount"], [class*="value"], [class*="Value"]');
                    const value = valueEl?.innerText?.trim() || '';
                    rows.push({ name, ticker, value });
                });
            } else {
                items.forEach(item => {
                    const name = item.querySelector('[class*="name"], [class*="Name"]')?.innerText?.trim();
                    const ticker = item.querySelector('[class*="ticker"], [class*="symbol"]')?.innerText?.trim();
                    const value = item.querySelector('[class*="amount"], [class*="value"]')?.innerText?.trim();
                    const pnl = item.querySelector('[class*="return"], [class*="profit"], [class*="sinceReturn"]')?.innerText?.trim();
                    if (name) rows.push({ name, ticker, value, pnl });
                });
            }
            return rows;
        }""")

    prev_count = 0
    for _ in range(20):
        raw = await _extract()
        for r in raw:
            key = r.get("ticker") or r.get("name")
            if key:
                positions[key] = r

        if len(positions) == prev_count and prev_count > 0:
            break
        prev_count = len(positions)

        reached = await page.evaluate("""() => {
            window.scrollBy(0, 600);
            return window.scrollY + window.innerHeight >= document.body.scrollHeight - 50;
        }""")
        await page.wait_for_timeout(600)
        if reached:
            break

    print(f"[TR] Read {len(positions)} positions.")

    import re

    def _num(s: Optional[str]) -> Optional[float]:
        if not s:
            return None
        m = re.search(r"[-\d.,]+", s.replace(",", "").replace(" ", ""))
        return float(m.group()) if m else None

    result = []
    for key, r in positions.items():
        market_value = _num(r.get("value")) or 0.0
        pnl_str = r.get("pnl", "")
        pnl_pct = _num(pnl_str) if pnl_str else None
        ticker = (r.get("ticker") or key or "").upper()
        result.append({
            "ticker": ticker,
            "name": r.get("name") or ticker,
            "quantity": 1.0,        # TR doesn't surface share count directly on this view
            "current_price": market_value,
            "avg_cost": None,
            "market_value": market_value,
            "pnl_pct": pnl_pct,
            "currency": "EUR",
        })

    return result


# ── API poster ────────────────────────────────────────────────────────────────

async def post_positions(broker: str, positions: list[dict], token: str) -> None:
    if not positions:
        print(f"[{broker}] No positions to post — skipping.")
        return
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    payload = {"broker": broker, "positions": positions}
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(f"{API_BASE}/broker-sync/ingest", json=payload, headers=headers)
        if resp.status_code in (200, 201):
            data = resp.json()
            print(f"[{broker}] ✅ Synced {data.get('positions_synced', '?')} positions → portfolio {data.get('portfolio_id', '?')}")
        else:
            print(f"[{broker}] ❌ Ingest failed {resp.status_code}: {resp.text[:200]}")


# ── Main ──────────────────────────────────────────────────────────────────────

async def main(broker: str, token: str) -> None:
    async with async_playwright() as pw:
        context = await pw.chromium.launch_persistent_context(
            user_data_dir=str(SESSION_DIR),
            headless=False,
            args=["--no-sandbox"],
            viewport={"width": 1280, "height": 900},
        )
        page = await context.new_page()

        if broker in ("etoro", "all"):
            etoro_positions = await read_etoro(page)
            await post_positions("etoro", etoro_positions, token)

        if broker in ("tr", "all"):
            tr_positions = await read_tr(page)
            await post_positions("tr", tr_positions, token)

        await context.close()
    print("Sync complete.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sync eToro/TR positions to investment-manager")
    parser.add_argument("--broker", default="all", choices=["etoro", "tr", "all"])
    parser.add_argument("--api", default=API_BASE)
    parser.add_argument("--token", default=API_TOKEN)
    args = parser.parse_args()

    if not args.token:
        print("⚠️  No API token. Set INVESTMENT_MANAGER_TOKEN env var or pass --token <jwt>")
        sys.exit(1)

    API_BASE = args.api
    asyncio.run(main(args.broker, args.token))
