#!/usr/bin/env python3
"""
backtest.py — offline decision accuracy + simple PnL replay.
Callable from main.py or Hermes. No MT5, no Redis, no standalone main.
"""
import json
from pathlib import Path
from typing import List, Dict, Any, Callable

import pandas as pd


def load_ohlc(path: str) -> pd.DataFrame:
    """Validate and load any CSV. Requires datetime index + open/high/low/close."""
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"CSV not found: {path}")
    if p.suffix.lower() not in (".csv", ".txt"):
        raise ValueError(f"Not a CSV: {path}")

    df = pd.read_csv(p, parse_dates=["datetime"], index_col="datetime")
    required = {"open", "high", "low", "close"}
    cols = {c.lower() for c in df.columns}
    if not required.issubset(cols):
        raise ValueError(f"CSV missing columns {required - cols}: {path}")
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
    events_path: str,
    decide_fn: Callable,
    initial_cash: float = 10000,
    lookahead: int = 1,
) -> Dict[str, Any]:
    """One-shot entry used by main.py or Hermes."""
    ohlc = load_ohlc(ohlc_path)
    events = load_events(events_path)
    return {
        "accuracy": score_decisions(events, ohlc, decide_fn, lookahead),
        "pnl": simulate(events, ohlc, decide_fn, initial_cash),
    }