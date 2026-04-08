from __future__ import annotations

import pandas as pd
import yfinance as yf
from datetime import datetime, timezone
import time


ASSETS = {
    "SPY": "equities_broad",
    "TLT": "duration_long",
    "IEF": "duration_intermediate",
    "SHY": "cash_bonds",
    "TIP": "tips",
    "DBC": "commodities",
    "GLD": "gold",
    "UUP": "usd",
    "XLE": "energy_equities",
    "XLF": "financials",
}


# ---------------------------------------------------
# DOWNLOAD
# ---------------------------------------------------

def download_prices(
    start: str = "2005-01-01",
    end: str | None = None,
    max_retries: int = 3,
) -> pd.DataFrame:

    if end is None:
        end = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    prices = pd.DataFrame()

    for ticker in ASSETS.keys():
        print(f"[INFO] Downloading {ticker}...")

        attempt = 0
        df = pd.DataFrame()

        while attempt < max_retries:
            try:
                df = yf.download(
                    ticker,
                    start=start,
                    end=end,
                    auto_adjust=True,
                    progress=False,
                )

                if not df.empty:
                    break

            except Exception as e:
                print(f"[WARN] {ticker} failed attempt {attempt+1}: {e}")

            attempt += 1
            time.sleep(1)

        if df.empty:
            print(f"[WARN] No data for {ticker}, skipping...")
            continue

        # robust close extraction
        if "Close" in df.columns:
            series = df["Close"]
        else:
            series = df.iloc[:, 0]

        series.name = ticker
        prices = pd.concat([prices, series], axis=1)

    if prices.empty:
        raise ValueError("❌ No price data downloaded!")

    prices.index = pd.to_datetime(prices.index)
    prices = prices.sort_index()

    # 🔥 wichtig: Lücken schließen
    prices = prices.ffill()

    return prices


# ---------------------------------------------------
# RETURNS
# ---------------------------------------------------

def build_returns(prices: pd.DataFrame) -> pd.DataFrame:

    # Monatsende (engine kompatibel!)
    monthly_prices = prices.resample("M").last()

    returns = monthly_prices.pct_change()

    # 🔥 wichtig: drop erste Zeile
    returns = returns.dropna(how="all")

    # Mapping
    returns = returns.rename(columns=ASSETS)

    # ---------------------------------------------------
    # DERIVED FEATURES (kompatibel mit deiner Engine)
    # ---------------------------------------------------

    if "financials" in returns.columns:
        returns["equities_value"] = returns["financials"]

    if "energy_equities" in returns.columns:
        returns["cyclical_equities"] = returns["energy_equities"]

    if "duration_intermediate" in returns.columns:
        returns["quality_equities"] = returns["duration_intermediate"]

    # Cash fallback
    if "cash" not in returns.columns:
        if "cash_bonds" in returns.columns:
            returns["cash"] = returns["cash_bonds"]
        else:
            returns["cash"] = 0.0

    # ---------------------------------------------------
    # VALIDATION (🔥 NEU)
    # ---------------------------------------------------

    returns = returns.replace([float("inf"), float("-inf")], pd.NA)

    # komplette leere Zeilen entfernen
    returns = returns.dropna(how="all")

    # Datum sauber setzen
    returns = returns.reset_index()
    returns = returns.rename(columns={"Date": "date"})

    returns["date"] = pd.to_datetime(returns["date"], utc=True)

    # ---------------------------------------------------
    # DEBUG OUTPUT
    # ---------------------------------------------------

    print("\n[DEBUG] Returns range:")
    print(returns["date"].min(), "→", returns["date"].max())

    print("\n[DEBUG] Last rows:")
    print(returns.tail())

    return returns


# ---------------------------------------------------
# MAIN
# ---------------------------------------------------

def main() -> None:
    print("📊 Building ETF-based asset returns (V2)...")

    prices = download_prices()

    print("\n[INFO] Price sample:")
    print(prices.tail())

    returns = build_returns(prices)

    out_path = "storage/cache/asset_returns.csv"
    returns.to_csv(out_path, index=False)

    print(f"\n✅ Saved to {out_path}")
    print(returns.tail())


if __name__ == "__main__":
    main()