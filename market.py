"""
Live market quotes for the briefing agent (via Yahoo Finance / yfinance).

Claude calls get_market_quotes whenever it wants to say a number out loud,
so prices and yields come from real data instead of possibly stale search
snippets.
"""

import datetime
import math

QUOTE_TOOL = {
    "name": "get_market_quotes",
    "description": (
        "Get the latest market data for one or more Yahoo Finance symbols. Returns, for each "
        "symbol, the latest price, the previous session's close, the change and percent change, "
        "and the date of the latest price, so you can say whether a number is from yesterday's "
        "close or this morning. Use this for EVERY market number you plan to mention.\n"
        "Useful symbols: S&P 500 ^GSPC, Nasdaq Composite ^IXIC, Dow ^DJI, S&P 500 futures ES=F, "
        "Nasdaq 100 futures NQ=F, Dow futures YM=F, 10-year Treasury yield ^TNX (value is the "
        "yield in percent), 5-year yield ^FVX, 30-year yield ^TYX, 13-week T-bill yield ^IRX, "
        "VIX ^VIX, US dollar index DX-Y.NYB, oil CL=F, gold GC=F, bitcoin BTC-USD, "
        "Hang Seng ^HSI, Shanghai Composite 000001.SS, Shenzhen 399001.SZ, CSI 300 000300.SS, "
        "US dollar to Chinese yuan CNY=X, offshore yuan CNH=X. Stocks use their ticker (AAPL, "
        "MSFT, NVDA, GOOGL, AMZN, META, TSLA, BABA, PDD, JD); Hong Kong listings use the .HK "
        "suffix (Tencent 0700.HK, BYD 1211.HK, Alibaba 9988.HK)."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "symbols": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Yahoo Finance symbols, at most 20 per call.",
            }
        },
        "required": ["symbols"],
    },
}


def _num(x):
    try:
        x = float(x)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(x) else round(x, 4)


def get_market_quotes(symbols: list[str]) -> dict:
    import yfinance as yf

    out = {}
    for sym in list(dict.fromkeys(s.strip() for s in symbols if s.strip()))[:20]:
        try:
            hist = yf.Ticker(sym).history(period="7d", interval="1d", auto_adjust=False)
            hist = hist.dropna(subset=["Close"])
            if hist.empty:
                out[sym] = {"error": "no data returned for this symbol"}
                continue
            last = hist.iloc[-1]
            prev = hist.iloc[-2] if len(hist) > 1 else None
            price = _num(last["Close"])
            prev_close = _num(prev["Close"]) if prev is not None else None
            entry = {
                "latest": price,
                "latest_date": hist.index[-1].strftime("%Y-%m-%d"),
                "previous_close": prev_close,
                "previous_date": hist.index[-2].strftime("%Y-%m-%d") if prev is not None else None,
            }
            if price is not None and prev_close:
                entry["change"] = round(price - prev_close, 4)
                entry["change_pct"] = round((price / prev_close - 1) * 100, 2)
            out[sym] = entry
        except Exception as exc:  # report per-symbol failures back to Claude
            out[sym] = {"error": f"{type(exc).__name__}: {exc}"[:200]}
    out["_retrieved_at_utc"] = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M")
    out["_note"] = (
        "latest_date is the trading day of the latest price. If it is today and the market "
        "has not opened yet, the value is a pre-market or futures price; otherwise it is "
        "that day's close."
    )
    return out
