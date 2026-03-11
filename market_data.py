"""
market_data.py - Data fetching layer for stocks (yfinance) and crypto (CoinGecko).
"""

import pandas as pd
import yfinance as yf
from pycoingecko import CoinGeckoAPI

cg = CoinGeckoAPI()

# Cache the CoinGecko coin list to avoid repeated API calls
_coin_list_cache = None

TIMEFRAME_STOCK = {
    "1D":  ("1d",  "5m"),
    "5D":  ("5d",  "30m"),
    "1M":  ("1mo", "1d"),
    "3M":  ("3mo", "1d"),
    "6M":  ("6mo", "1d"),
    "1Y":  ("1y",  "1wk"),
}

TIMEFRAME_CRYPTO_DAYS = {
    "1D":  1,
    "5D":  7,
    "1M":  30,
    "3M":  90,
    "6M":  180,
    "1Y":  365,
}

WATCHLIST_TICKERS = ["AAPL", "TSLA", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "SPY"]

# Hardcoded fallback map: common crypto names/symbols -> CoinGecko coin ID
_CRYPTO_FALLBACK = {
    "bitcoin": "bitcoin", "btc": "bitcoin",
    "ethereum": "ethereum", "eth": "ethereum",
    "tether": "tether", "usdt": "tether",
    "binancecoin": "binancecoin", "bnb": "binancecoin",
    "solana": "solana", "sol": "solana",
    "ripple": "ripple", "xrp": "ripple",
    "usd-coin": "usd-coin", "usdc": "usd-coin",
    "dogecoin": "dogecoin", "doge": "dogecoin",
    "cardano": "cardano", "ada": "cardano",
    "tron": "tron", "trx": "tron",
    "avalanche-2": "avalanche-2", "avax": "avalanche-2",
    "chainlink": "chainlink", "link": "chainlink",
    "polkadot": "polkadot", "dot": "polkadot",
    "wrapped-bitcoin": "wrapped-bitcoin", "wbtc": "wrapped-bitcoin",
    "matic-network": "matic-network", "matic": "matic-network", "pol": "matic-network",
    "litecoin": "litecoin", "ltc": "litecoin",
    "shiba-inu": "shiba-inu", "shib": "shiba-inu",
    "internet-computer": "internet-computer", "icp": "internet-computer",
    "uniswap": "uniswap", "uni": "uniswap",
    "stellar": "stellar", "xlm": "stellar",
    "monero": "monero", "xmr": "monero",
    "cosmos": "cosmos", "atom": "cosmos",
    "ethereum-classic": "ethereum-classic", "etc": "ethereum-classic",
    "filecoin": "filecoin", "fil": "filecoin",
    "aptos": "aptos", "apt": "aptos",
    "near": "near", "near-protocol": "near",
    "arbitrum": "arbitrum", "arb": "arbitrum",
    "pepe": "pepe",
    "sui": "sui",
}


def _get_coin_list():
    global _coin_list_cache
    if _coin_list_cache is None:
        try:
            coins = cg.get_coins_list()
            # Build lookup: lowercase id -> id, and lowercase symbol -> id (first match)
            _coin_list_cache = {}
            symbol_map = {}
            for coin in coins:
                _coin_list_cache[coin["id"].lower()] = coin["id"]
                sym = coin["symbol"].lower()
                if sym not in symbol_map:
                    symbol_map[sym] = coin["id"]
            _coin_list_cache.update(symbol_map)
        except Exception:
            # Fall back to hardcoded list when network is unavailable
            _coin_list_cache = dict(_CRYPTO_FALLBACK)
    return _coin_list_cache


def resolve_symbol(query: str) -> tuple[str, str]:
    """
    Given a query string, return (asset_type, identifier).
    asset_type is "stock" or "crypto".
    identifier is the ticker (stock) or coin_id (crypto).
    """
    q = query.strip().lower()
    coin_map = _get_coin_list()
    if q in coin_map:
        return ("crypto", coin_map[q])
    return ("stock", query.strip().upper())


def _add_moving_averages(df: pd.DataFrame) -> pd.DataFrame:
    if "Close" in df.columns and len(df) >= 20:
        df["MA20"] = df["Close"].rolling(window=20).mean()
    if "Close" in df.columns and len(df) >= 50:
        df["MA50"] = df["Close"].rolling(window=50).mean()
    return df


# ── Stock functions ──────────────────────────────────────────────────────────

def fetch_stock_history(ticker: str, timeframe: str = "1M") -> pd.DataFrame:
    period, interval = TIMEFRAME_STOCK.get(timeframe, ("1mo", "1d"))
    try:
        df = yf.download(ticker, period=period, interval=interval, progress=False, auto_adjust=True)
        df.index = pd.to_datetime(df.index)
        df = df[["Open", "High", "Low", "Close", "Volume"]].copy()
        df = _add_moving_averages(df)
        return df
    except Exception:
        return pd.DataFrame()


def fetch_stock_info(ticker: str) -> dict:
    try:
        t = yf.Ticker(ticker)
        info = t.info
        hist = yf.download(ticker, period="2d", interval="1d", progress=False, auto_adjust=True)
        price = float(info.get("currentPrice") or info.get("regularMarketPrice") or 0)
        prev_close = float(info.get("previousClose") or info.get("regularMarketPreviousClose") or price)
        change_pct = ((price - prev_close) / prev_close * 100) if prev_close else 0
        return {
            "name": info.get("longName") or info.get("shortName") or ticker,
            "symbol": ticker.upper(),
            "type": "Stock",
            "price": price,
            "change_pct": round(change_pct, 2),
            "volume": info.get("volume") or info.get("regularMarketVolume") or 0,
            "market_cap": info.get("marketCap") or 0,
            "high_52w": info.get("fiftyTwoWeekHigh") or 0,
            "low_52w": info.get("fiftyTwoWeekLow") or 0,
            "sector": info.get("sector") or "N/A",
        }
    except Exception:
        return {}


def get_watchlist_stocks() -> list[dict]:
    results = []
    for ticker in WATCHLIST_TICKERS:
        try:
            t = yf.Ticker(ticker)
            info = t.info
            price = float(info.get("currentPrice") or info.get("regularMarketPrice") or 0)
            prev = float(info.get("previousClose") or info.get("regularMarketPreviousClose") or price)
            change_pct = round(((price - prev) / prev * 100), 2) if prev else 0
            results.append({
                "symbol": ticker,
                "name": info.get("shortName") or ticker,
                "price": price,
                "change_pct": change_pct,
            })
        except Exception:
            pass
    return results


# ── Crypto functions ─────────────────────────────────────────────────────────

def fetch_crypto_history(coin_id: str, timeframe: str = "1M") -> pd.DataFrame:
    days = TIMEFRAME_CRYPTO_DAYS.get(timeframe, 30)
    try:
        data = cg.get_coin_ohlc_by_id(id=coin_id, vs_currency="usd", days=str(days))
        df = pd.DataFrame(data, columns=["timestamp", "Open", "High", "Low", "Close"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df = df.set_index("timestamp")
        # CoinGecko OHLC doesn't include volume — fetch separately
        market = cg.get_coin_market_chart_by_id(id=coin_id, vs_currency="usd", days=str(days))
        vol_df = pd.DataFrame(market["total_volumes"], columns=["timestamp", "Volume"])
        vol_df["timestamp"] = pd.to_datetime(vol_df["timestamp"], unit="ms")
        vol_df = vol_df.set_index("timestamp")
        df = df.join(vol_df, how="left")
        df["Volume"] = df["Volume"].fillna(0)
        df = _add_moving_averages(df)
        return df
    except Exception:
        return pd.DataFrame()


def fetch_crypto_info(coin_id: str) -> dict:
    try:
        data = cg.get_coin_by_id(
            id=coin_id,
            localization=False,
            tickers=False,
            community_data=False,
            developer_data=False,
        )
        market = data.get("market_data", {})
        price = market.get("current_price", {}).get("usd", 0) or 0
        change_24h = market.get("price_change_percentage_24h") or 0
        return {
            "name": data.get("name", coin_id),
            "symbol": data.get("symbol", "").upper(),
            "type": "Crypto",
            "price": price,
            "change_pct": round(change_24h, 2),
            "volume": market.get("total_volume", {}).get("usd", 0) or 0,
            "market_cap": market.get("market_cap", {}).get("usd", 0) or 0,
            "high_52w": market.get("ath", {}).get("usd", 0) or 0,
            "low_52w": market.get("atl", {}).get("usd", 0) or 0,
            "sector": "Cryptocurrency",
        }
    except Exception:
        return {}


def fetch_trending_crypto() -> list[dict]:
    try:
        trending = cg.get_search_trending()
        results = []
        for item in trending.get("coins", [])[:8]:
            coin = item.get("item", {})
            results.append({
                "name": coin.get("name", ""),
                "symbol": coin.get("symbol", "").upper(),
                "coin_id": coin.get("id", ""),
                "thumb": coin.get("thumb", ""),
                "market_cap_rank": coin.get("market_cap_rank") or "N/A",
            })
        return results
    except Exception:
        return []


def format_number(value, prefix="$") -> str:
    """Format large numbers with K/M/B suffixes."""
    if not value:
        return "N/A"
    try:
        v = float(value)
        if v >= 1e12:
            return f"{prefix}{v/1e12:.2f}T"
        if v >= 1e9:
            return f"{prefix}{v/1e9:.2f}B"
        if v >= 1e6:
            return f"{prefix}{v/1e6:.2f}M"
        if v >= 1e3:
            return f"{prefix}{v/1e3:.2f}K"
        return f"{prefix}{v:,.2f}"
    except Exception:
        return "N/A"
