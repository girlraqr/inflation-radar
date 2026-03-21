from __future__ import annotations

import pandas as pd
import yfinance as yf


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


def download_prices(start: str = "2005-01-01") -> pd.DataFrame:
    prices = pd.DataFrame()

    for ticker in ASSETS.keys():
        print(f"[INFO] Downloading {ticker}...")

        df = yf.download(
            ticker,
            start=start,
            auto_adjust=True,
            progress=False,
        )

        if df.empty:
            print(f"[WARN] No data for {ticker}, skipping...")
            continue

        if "Close" in df.columns:
            series = df["Close"]
        else:
            series = df.iloc[:, 0]

        series.name = ticker
        prices = pd.concat([prices, series], axis=1)

    if prices.empty:
        raise ValueError("No price data downloaded!")

    prices = prices.dropna(how="all")
    prices.index = pd.to_datetime(prices.index)
    prices = prices.sort_index()

    return prices


def build_returns(prices: pd.DataFrame) -> pd.DataFrame:
    monthly_prices = prices.resample("ME").last()
    returns = monthly_prices.pct_change().dropna(how="all")

    returns = returns.rename(columns=ASSETS)

    # Zusätzliche Spalten für Kompatibilität mit bestehender Allocation
    if "equities_broad" in returns.columns:
        returns["equities_value"] = returns["financials"]
        returns["cyclical_equities"] = returns["energy_equities"]
        returns["quality_equities"] = returns["duration_intermediate"]

    # Cash-Spalte für Fallback
    if "cash" not in returns.columns:
        # SHY als cash-naher Proxy; falls nicht da, dann 0
        if "cash_bonds" in returns.columns:
            returns["cash"] = returns["cash_bonds"]
        else:
            returns["cash"] = 0.0

    returns = returns.reset_index().rename(columns={"Date": "date"})

    return returns


def main() -> None:
    print("📊 Building expanded ETF-based asset returns...")

    prices = download_prices()
    print("[INFO] Price sample:")
    print(prices.tail())

    returns = build_returns(prices)

    out_path = "storage/cache/asset_returns.csv"
    returns.to_csv(out_path, index=False)

    print(f"✅ Saved to {out_path}")
    print(returns.tail())


if __name__ == "__main__":
    main()