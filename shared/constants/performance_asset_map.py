from __future__ import annotations

PORTFOLIO_TO_RETURN_BUCKET: dict[str, str] = {
    # Macro / inflation
    "CPI_US": "tips",

    # Rates / duration
    "DGS10": "duration_intermediate",

    # Optional future mappings
    "TLT": "duration_long",
    "IEF": "duration_intermediate",
    "SHY": "cash_bonds",
    "BIL": "cash",

    "SPY": "equities_broad",
    "QQQ": "quality_equities",
    "IWM": "cyclical_equities",
    "XLE": "energy_equities",
    "XLF": "financials",
    "GLD": "gold",
    "DBC": "commodities",
    "TIP": "tips",
    "UUP": "usd",
    "VTV": "equities_value",
}