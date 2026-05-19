"""HTML report parser for us-stock-report skill output.

Converts a daily portfolio report HTML into structured ParsedReport data
ready to be persisted via snapshot_writer. Defensive: a malformed row
emits a logger warning but does not abort the parse.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional

from bs4 import BeautifulSoup, Tag

logger = logging.getLogger(__name__)


# ── TR display-name → ticker map ─────────────────────────────────────────────
# Trade Republic shows full names; we keep a small mapping for common holdings.
# Unmapped names fall through to display_name as ticker (callers can warn).
TR_NAME_TO_TICKER: dict[str, str] = {
    "nvidia": "NVDA",
    "alphabet (a)": "GOOGL",
    "alphabet (c)": "GOOG",
    "micron technology": "MU",
    "amd": "AMD",
    "broadcom": "AVGO",
    "goldman sachs": "GS",
    "tesla": "TSLA",
    "microsoft": "MSFT",
    "tsmc (adr)": "TSM",
    "amazon.com": "AMZN",
    "amazon": "AMZN",
    "meta platforms (a)": "META",
    "meta platforms": "META",
    "apple": "AAPL",
    "western digital": "WDC",
    "s&p 500 info tech (iuit)": "IUIT",
    "netflix": "NFLX",
    "advanced micro devices": "AMD",
}


# ── Parsed types ─────────────────────────────────────────────────────────────

@dataclass
class ParsedAccountSummary:
    combined_total_usd: Optional[float] = None
    combined_cash_usd: Optional[float] = None
    cash_ratio_pct: Optional[float] = None
    eur_usd_rate: Optional[float] = None
    etoro_total_usd: Optional[float] = None
    etoro_cash_usd: Optional[float] = None
    etoro_invested_usd: Optional[float] = None
    etoro_pnl_day_usd: Optional[float] = None
    tr_total_eur: Optional[float] = None
    tr_cash_eur: Optional[float] = None
    tr_invested_eur: Optional[float] = None
    tr_pnl_day_eur: Optional[float] = None


@dataclass
class ParsedHolding:
    account: str  # 'etoro' | 'tr'
    ticker: str
    display_name: str
    currency: str  # 'USD' | 'EUR'
    shares: Optional[float] = None
    avg_cost: Optional[float] = None
    current_price: Optional[float] = None
    market_value: Optional[float] = None
    pnl_total_pct: Optional[float] = None
    pnl_day_pct: Optional[float] = None


@dataclass
class ParsedRecommendation:
    priority_raw: str  # raw cell text, e.g. '① 5/18（周一开盘前）'
    priority_tier: Optional[int]  # 1/2/3/4 extracted from leading ①②③④
    ticker_or_label: str
    direction: str
    account: str  # 'etoro' | 'tr' | 'both' | 'unknown'
    quantity_text: str
    trigger_text: str
    rationale: str
    reference_price: Optional[float] = None  # extracted from trigger_text when possible


@dataclass
class ParsedReport:
    report_date: Optional[date]
    summary: ParsedAccountSummary
    holdings: list[ParsedHolding] = field(default_factory=list)
    recommendations: list[ParsedRecommendation] = field(default_factory=list)


# ── String → number helpers ──────────────────────────────────────────────────

_PRIORITY_TIER = {"①": 1, "②": 2, "③": 3, "④": 4}
_ACCOUNT_KEYWORDS = {
    "etoro": "etoro",
    "tr": "tr",
    "trade republic": "tr",
    "双账户": "both",
    "both": "both",
}


_NUMBER_RE = re.compile(r"(-?)\s*[\$€£¥]?\s*(\d+(?:\.\d+)?)")


def _parse_number(text: Optional[str]) -> Optional[float]:
    """Extract first signed number from a string. Strips $/€/% and commas.
    Recognizes a leading '-' (or unicode '−') even when separated from the
    digit by whitespace or a currency symbol (e.g. '-€3,591' → -3591).
    Returns None if no match.
    """
    if not text:
        return None
    cleaned = text.replace(",", "").replace("−", "-")
    m = _NUMBER_RE.search(cleaned)
    if not m:
        return None
    try:
        val = float(m.group(2))
        return -val if m.group(1) == "-" else val
    except ValueError:
        return None


def _parse_pct(text: Optional[str]) -> Optional[float]:
    """Parse a percentage string like '+38.43%' / '-2.50%' / '8.92%' → float."""
    return _parse_number(text)


def _classify_account(text: str) -> str:
    """Map free-text account label to 'etoro' | 'tr' | 'both' | 'unknown'."""
    if not text:
        return "unknown"
    lo = text.lower()
    for kw, code in _ACCOUNT_KEYWORDS.items():
        if kw in lo:
            return code
    return "unknown"


def _map_tr_ticker(name: str) -> str:
    """Map a TR display name to a ticker. Falls back to the raw name."""
    key = name.strip().lower()
    if key in TR_NAME_TO_TICKER:
        return TR_NAME_TO_TICKER[key]
    logger.warning("TR name not mapped to ticker, using raw: %r", name)
    return name.strip()


# ── Section parsers ──────────────────────────────────────────────────────────

def _parse_combined_total(soup: BeautifulSoup, summary: ParsedAccountSummary) -> None:
    block = soup.select_one(".combined-total")
    if not block:
        logger.warning("No .combined-total block found")
        return

    # Total: latest uses .big, mid-format (2026-05-06..10) uses .big-num
    big = block.select_one(".big") or block.select_one(".big-num")
    if big:
        summary.combined_total_usd = _parse_number(big.get_text())

    text = block.get_text(" ", strip=True)
    # "1 EUR = 1.1624 USD" or "EUR/USD ≈ 1.1624" or "(EUR/USD 1.1790)"
    eur_match = re.search(r"1\s*EUR\s*=\s*([\d.]+)\s*USD", text)
    if not eur_match:
        eur_match = re.search(r"EUR/USD[^\d]*([\d.]+)", text)
    if eur_match:
        try:
            summary.eur_usd_rate = float(eur_match.group(1))
        except ValueError:
            pass

    # Cash: latest "现金 $24,420 (8.92% ...)" has ratio in parens.
    # Mid-format "现金 $18,454 <span class="cash-ratio-badge">6.70% 偏低</span>"
    # puts the ratio in a sibling span. Try inline first, then DOM-based.
    cash_match = re.search(r"现金\s*\$?([\d,]+(?:\.\d+)?)\s*\(\s*(\d+(?:\.\d+)?)\s*%", text)
    if cash_match:
        summary.combined_cash_usd = _parse_number(cash_match.group(1))
        try:
            summary.cash_ratio_pct = float(cash_match.group(2))
        except ValueError:
            pass
    else:
        if (cash_only := re.search(r"现金\s*\$?([\d,]+(?:\.\d+)?)", text)):
            summary.combined_cash_usd = _parse_number(cash_only.group(1))
        # Standalone cash-ratio-badge span (mid-format)
        if summary.cash_ratio_pct is None:
            badge = block.select_one(".cash-ratio-badge")
            if badge:
                pct = _parse_number(badge.get_text())
                if pct is not None:
                    summary.cash_ratio_pct = pct


def _parse_account_box(box: Tag) -> tuple[str, dict[str, Optional[float]], list[ParsedHolding]]:
    """Parse one .account-box → (account_code, totals_dict, holdings).
    account_code: 'etoro' | 'tr' | 'unknown'.
    """
    h3 = box.find("h3")
    header = h3.get_text(strip=True) if h3 else ""
    if "etoro" in header.lower():
        account = "etoro"
        currency = "USD"
    elif "trade republic" in header.lower() or "tr" in header.lower():
        account = "tr"
        currency = "EUR"
    else:
        account = "unknown"
        currency = "USD"

    totals: dict[str, Optional[float]] = {}

    # Total: latest uses .account-total div; mid-format uses .kpi-row with
    # an item labelled "总净值".
    total_el = box.select_one(".account-total")
    if total_el:
        totals["total"] = _parse_number(total_el.get_text())

    # KPI row (mid-format): items with .label "总净值"/"今日 P&L"/"累计盈亏"/...
    for kpi in box.select(".kpi"):
        label_el = kpi.find(class_="label")
        value_el = kpi.find(class_="value")
        if not label_el or not value_el:
            continue
        label = label_el.get_text(strip=True)
        value = _parse_number(value_el.get_text())
        if "总净值" in label and totals.get("total") is None:
            totals["total"] = value
        elif "今日 P&L" in label or "今日 P&amp;L" in label or "今日变化" in label:
            totals["pnl_day"] = value

    # cash-row > cash-item: label + value (both formats)
    for item in box.select(".cash-item"):
        label_el = item.find(class_="label")
        value_el = item.find(class_="value")
        if not label_el or not value_el:
            continue
        label = label_el.get_text(strip=True)
        value = _parse_number(value_el.get_text())
        if "现金" in label:
            totals["cash"] = value
        elif "已投资" in label:
            totals["invested"] = value
        elif "今日变化" in label:
            totals["pnl_day"] = value
        # "累计 P&L" / "累计盈亏" are cumulative — not in snapshot schema, ignore

    holdings = _parse_holdings_table(box, account, currency)
    return account, totals, holdings


def _parse_holdings_table(box: Tag, account: str, currency: str) -> list[ParsedHolding]:
    """Parse the <table> inside an account-box. Schema differs between
    eToro (7 cols: ticker/price/day%/shares/avg/pnl%/value) and
    TR (4 cols: name/shares/value/since_buy_pct).
    """
    table = box.find("table")
    if not table:
        logger.warning("No holdings table in %s account-box", account)
        return []

    rows = table.find_all("tr")
    if len(rows) < 2:
        return []

    # Skip header row
    holdings: list[ParsedHolding] = []
    for tr in rows[1:]:
        cells = tr.find_all("td")
        try:
            if account == "etoro":
                holding = _parse_etoro_row(cells, currency)
            elif account == "tr":
                holding = _parse_tr_row(cells, currency)
            else:
                continue
        except Exception as exc:
            logger.warning("Skip malformed %s holding row: %s", account, exc)
            continue
        if holding:
            holdings.append(holding)
    return holdings


def _cell_ticker(cell: Tag) -> str:
    """Pull a ticker symbol from a cell. Prefer a leading <b>/<strong> child
    (mid-format puts "<strong>NVDA</strong> NVIDIA" — full text would
    concatenate to "NVDANVIDIA"). Falls back to the cell's full text.
    """
    bold = cell.find(["b", "strong"])
    if bold:
        t = bold.get_text(strip=True)
        if t:
            return t
    return cell.get_text(strip=True)


def _parse_etoro_row(cells: list[Tag], currency: str) -> Optional[ParsedHolding]:
    if len(cells) < 7:
        # e.g. JEPQ "已清仓" row has colspan=6 → only 2 cells
        return None
    ticker = _cell_ticker(cells[0])
    if not ticker or ticker in {"—", "-"}:
        return None

    # Two column schemas seen in the wild:
    #   Latest (7 cols): ticker | price | day% | shares | avg | pnl% | mv
    #   Mid    (8 cols): ticker | price | day% | shares | avg | pnl$ | pnl% | mv
    # Detect by column count.
    if len(cells) >= 8:
        current_price = _parse_number(cells[1].get_text())
        pnl_day_pct = _parse_pct(cells[2].get_text())
        shares = _parse_number(cells[3].get_text())
        avg_cost = _parse_number(cells[4].get_text())
        # cells[5] is pnl_usd — skip
        pnl_total_pct = _parse_pct(cells[6].get_text())
        market_value = _parse_number(cells[7].get_text())
    else:
        current_price = _parse_number(cells[1].get_text())
        pnl_day_pct = _parse_pct(cells[2].get_text())
        shares = _parse_number(cells[3].get_text())
        avg_cost = _parse_number(cells[4].get_text())
        pnl_total_pct = _parse_pct(cells[5].get_text())
        market_value = _parse_number(cells[6].get_text())
    return ParsedHolding(
        account="etoro",
        ticker=ticker.upper(),
        display_name=ticker,
        currency=currency,
        shares=shares,
        avg_cost=avg_cost,
        current_price=current_price,
        market_value=market_value,
        pnl_total_pct=pnl_total_pct,
        pnl_day_pct=pnl_day_pct,
    )


def _parse_tr_row(cells: list[Tag], currency: str) -> Optional[ParsedHolding]:
    if len(cells) < 4:
        return None
    name_cell = cells[0]
    name_text = name_cell.get_text(" ", strip=True)
    if not name_text:
        return None
    # Mid-format wraps the ticker in <strong>/<b>, then the display name follows.
    # When present, use the ticker directly; otherwise fall back to the TR name map.
    bold = name_cell.find(["b", "strong"])
    bold_ticker = bold.get_text(strip=True) if bold else ""
    if bold_ticker and bold_ticker.isalpha() and bold_ticker.isupper():
        ticker = bold_ticker
    else:
        ticker = _map_tr_ticker(name_text)
    shares = _parse_number(cells[1].get_text())
    market_value = _parse_number(cells[2].get_text())
    # The 4th column is sometimes a percent ("+91.01%", new + 5/10 mid-format)
    # and sometimes an absolute pnl amount in the account currency ("+6,814",
    # seen in 5/06–5/08). Detect by presence of "%".
    pnl_cell_text = cells[3].get_text()
    pnl_total_pct: Optional[float]
    if "%" in pnl_cell_text:
        pnl_total_pct = _parse_pct(pnl_cell_text)
    else:
        pnl_abs = _parse_number(pnl_cell_text)
        if pnl_abs is not None and market_value is not None and market_value != pnl_abs:
            cost = market_value - pnl_abs
            pnl_total_pct = (pnl_abs / cost * 100) if cost > 0 else None
        else:
            pnl_total_pct = None
    # Back-derive avg_cost from market_value / shares / (1 + pnl_pct/100)
    avg_cost: Optional[float] = None
    if market_value and shares and pnl_total_pct is not None and shares > 0:
        growth = 1 + pnl_total_pct / 100
        if growth > 0:
            current_per_share = market_value / shares
            avg_cost = current_per_share / growth
    return ParsedHolding(
        account="tr",
        ticker=ticker,
        display_name=name_text,
        currency=currency,
        shares=shares,
        avg_cost=avg_cost,
        current_price=(market_value / shares) if (market_value and shares) else None,
        market_value=market_value,
        pnl_total_pct=pnl_total_pct,
        pnl_day_pct=None,
    )


def _find_operations_table(soup: BeautifulSoup) -> Optional[Tag]:
    """Locate the operations table by header content: must contain
    '优先级' + '股票' + '方向' in the first row.
    """
    for table in soup.find_all("table"):
        first_row = table.find("tr")
        if not first_row:
            continue
        headers = {th.get_text(strip=True) for th in first_row.find_all(["th", "td"])}
        if "优先级" in headers and "股票" in headers and "方向" in headers:
            return table
    return None


def _parse_recommendations(soup: BeautifulSoup) -> list[ParsedRecommendation]:
    table = _find_operations_table(soup)
    if not table:
        logger.warning("No operations table found")
        return []

    recs: list[ParsedRecommendation] = []
    rows = table.find_all("tr")
    for tr in rows[1:]:
        cells = tr.find_all("td")
        if len(cells) < 7:
            continue
        try:
            priority_raw = cells[0].get_text(strip=True)
            tier = next(
                (v for k, v in _PRIORITY_TIER.items() if priority_raw.startswith(k)),
                None,
            )
            ticker_label = cells[1].get_text(strip=True)
            direction = cells[2].get_text(strip=True)
            account = _classify_account(cells[3].get_text(strip=True))
            qty_text = cells[4].get_text(strip=True)
            trigger_text = cells[5].get_text(strip=True)
            rationale = cells[6].get_text(strip=True)

            # Try to pull a numeric reference price from trigger or quantity text
            ref_price = _parse_number(trigger_text) or _parse_number(qty_text)

            recs.append(ParsedRecommendation(
                priority_raw=priority_raw,
                priority_tier=tier,
                ticker_or_label=ticker_label,
                direction=direction,
                account=account,
                quantity_text=qty_text,
                trigger_text=trigger_text,
                rationale=rationale,
                reference_price=ref_price,
            ))
        except Exception as exc:
            logger.warning("Skip malformed recommendation row: %s", exc)
    return recs


# ── Date extraction ──────────────────────────────────────────────────────────

_DATE_PATTERNS = [
    re.compile(r"对比基准[：:]\s*(\d{4}-\d{2}-\d{2})"),
    re.compile(r"(\d{4}-\d{2}-\d{2})"),
    re.compile(r"(\d{4})/(\d{1,2})/(\d{1,2})"),
]


def _extract_report_date(soup: BeautifulSoup, fallback_filename: Optional[str] = None) -> Optional[date]:
    """Try to find report date from HTML title/subtitle, then filename."""
    text = soup.get_text(" ", strip=True)[:2000]  # only scan top of doc
    for pat in _DATE_PATTERNS:
        m = pat.search(text)
        if m:
            try:
                if len(m.groups()) == 1:
                    return datetime.strptime(m.group(1), "%Y-%m-%d").date()
                else:
                    y, mo, d = (int(g) for g in m.groups())
                    return date(y, mo, d)
            except (ValueError, IndexError):
                continue
    if fallback_filename:
        for pat in _DATE_PATTERNS:
            m = pat.search(fallback_filename)
            if m and len(m.groups()) == 1:
                try:
                    return datetime.strptime(m.group(1), "%Y-%m-%d").date()
                except ValueError:
                    continue
    return None


# ── Public entry point ──────────────────────────────────────────────────────

def parse_report(html: str, *, report_date: Optional[date] = None,
                 fallback_filename: Optional[str] = None) -> ParsedReport:
    """Parse a us-stock-report HTML into structured form.

    report_date: explicit override; if omitted, attempts extraction from HTML
    then from fallback_filename.
    """
    soup = BeautifulSoup(html, "lxml")
    summary = ParsedAccountSummary()
    _parse_combined_total(soup, summary)

    holdings: list[ParsedHolding] = []
    for box in soup.select(".account-box"):
        account, totals, box_holdings = _parse_account_box(box)
        if account == "etoro":
            summary.etoro_total_usd = totals.get("total")
            summary.etoro_cash_usd = totals.get("cash")
            summary.etoro_invested_usd = totals.get("invested")
            summary.etoro_pnl_day_usd = totals.get("pnl_day")
        elif account == "tr":
            summary.tr_total_eur = totals.get("total")
            summary.tr_cash_eur = totals.get("cash")
            summary.tr_invested_eur = totals.get("invested")
            summary.tr_pnl_day_eur = totals.get("pnl_day")
        holdings.extend(box_holdings)

    recommendations = _parse_recommendations(soup)

    final_date = report_date or _extract_report_date(soup, fallback_filename)
    if final_date is None:
        logger.warning("Could not determine report_date; caller must supply it")

    return ParsedReport(
        report_date=final_date,
        summary=summary,
        holdings=holdings,
        recommendations=recommendations,
    )
