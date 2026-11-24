#!/usr/bin/env python3
"""
backtest.py — offline decision accuracy + simple PnL replay.
Callable from main.py or Hermes. No MT5, no Redis, no standalone main.
"""
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from typing import List, Dict, Any, Callable
import yfinance as yf
import pandas as pd

def _yahoo_url_to_df(url: str) -> pd.DataFrame:
    """Download OHLC from Yahoo history URL into a DataFrame (no file)."""
    parsed = urlparse(url)
    parts = [p for p in parsed.path.strip("/").split("/") if p]
    try:
        ticker = parts[parts.index("quote") + 1]
    except (ValueError, IndexError):
        raise ValueError("Could not find ticker in Yahoo URL")

    params = parse_qs(parsed.query)
    try:
        start = datetime.fromtimestamp(int(params["period1"][0]), tz=timezone.utc).date().isoformat()
        end = datetime.fromtimestamp(int(params["period2"][0]), tz=timezone.utc).date().isoformat()
    except (KeyError, ValueError, IndexError):
        raise ValueError("URL must contain valid period1 and period2")

    data = yf.download(ticker, start=start, end=end, interval="1d",
                       auto_adjust=False, progress=False)
    if data.empty:
        raise ValueError(f"No data for {ticker}")

    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)
    data.columns = [str(c).lower() for c in data.columns]
    data.index.name = "datetime"

    required = {"open", "high", "low", "close"}
    if not required.issubset(data.columns):
        raise ValueError(f"Yahoo data missing {required - set(data.columns)}")
    return data[list(required)].sort_index()



def load_ohlc(path_or_url: str) -> pd.DataFrame:
    """
    Accepts:
      - local CSV path
      - Yahoo Finance history URL (downloaded in memory)
    """
    if path_or_url.startswith(("http://", "https://")) and "yahoo" in path_or_url.lower():
        return _yahoo_url_to_df(path_or_url)

    # local file
    p = Path(path_or_url)
    if not p.is_file():
        raise FileNotFoundError(f"CSV not found: {path_or_url}")
    if p.suffix.lower() not in (".csv", ".txt"):
        raise ValueError(f"Not a CSV: {path_or_url}")

    df = pd.read_csv(p, parse_dates=["datetime"], index_col="datetime")
    df.columns = [str(c).lower() for c in df.columns]
    required = {"open", "high", "low", "close"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"CSV missing columns: {missing}")
    return df.sort_index()


def load_events(path: str) -> List[Dict]:
    """Load JSONL of events. Each line: {"ts": "...", "text": "..."}."""
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"Events file not found: {path}")
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]


def score_decisions(
    events: List[Dict],
    ohlc: pd.DataFrame,
    decide_fn: Callable,
    lookahead: int = 1,
) -> Dict[str, Any]:
    """
    Compare each buy/sell decision to the real price move `lookahead` bars later.
    Hold calls are ignored. Returns accuracy % and per-event detail.
    """
    results = []
    hits = 0
    total = 0

    for ev in events:
        ts = pd.to_datetime(ev["ts"])
        try:
            loc = ohlc.index.get_indexer([ts], method="ffill")[0]
            if loc < 0 or loc + lookahead >= len(ohlc):
                continue
            price_now = float(ohlc.iloc[loc]["close"])
            price_later = float(ohlc.iloc[loc + lookahead]["close"])
        except Exception:
            continue

        decision = decide_fn(ev, price_now)
        side = decision.get("side", "hold")
        if side == "hold":
            continue

        total += 1
        moved_up = price_later > price_now
        correct = (side == "buy" and moved_up) or (side == "sell" and not moved_up)
        if correct:
            hits += 1

        results.append({
            "ts": str(ts),
            "side": side,
            "price_now": price_now,
            "price_later": price_later,
            "correct": correct,
        })

    accuracy = (hits / total * 100) if total else 0.0
    return {
        "accuracy_pct": accuracy,
        "hits": hits,
        "total_decisions": total,
        "details": results,
    }


def simulate(
    events: List[Dict],
    ohlc: pd.DataFrame,
    decide_fn: Callable,
    initial_cash: float = 10000,
) -> Dict[str, Any]:
    """Simple cash/position replay. Returns equity curve and trade list."""
    cash = initial_cash
    position = 0.0
    equity = []
    trades = []

    for ev in events:
        ts = pd.to_datetime(ev["ts"])
        try:
            loc = ohlc.index.get_indexer([ts], method="ffill")[0]
            if loc < 0:
                continue
            price = float(ohlc.iloc[loc]["close"])
        except Exception:
            continue

        decision = decide_fn(ev, price)
        side = decision.get("side", "hold")
        lots = float(decision.get("lots", 0.0))

        if side == "buy" and cash >= price * lots:
            cash -= price * lots
            position += lots
            trades.append({"ts": str(ts), "side": "buy", "price": price, "lots": lots})
        elif side == "sell" and position >= lots:
            cash += price * lots
            position -= lots
            trades.append({"ts": str(ts), "side": "sell", "price": price, "lots": lots})

        equity.append({"ts": str(ts), "equity": cash + position * price})

    final = cash + position * float(ohlc.iloc[-1]["close"])
    return {
        "initial": initial_cash,
        "final": final,
        "return_pct": (final / initial_cash - 1) * 100,
        "trades": trades,
        "equity": equity,
    }


def run(
    ohlc_path: str,
    events_path: str = None,
    events: List[Dict] = None,
    decide_fn: Callable = None,
    initial_cash: float = 10000,
    lookahead: int = 1,
) -> Dict[str, Any]:
    """
    One-shot entry.
    Provide either events_path or events.
    decide_fn is required.
    """
    if decide_fn is None:
        raise ValueError("decide_fn is required")

    ohlc = load_ohlc(ohlc_path)

    if events is not None:
        loaded_events = events
    elif events_path:
        loaded_events = load_events(events_path)
    else:
        raise ValueError("Provide either events_path or events")

    return {
        "accuracy": score_decisions(loaded_events, ohlc, decide_fn, lookahead),
        "pnl": simulate(loaded_events, ohlc, decide_fn, initial_cash),
    }
