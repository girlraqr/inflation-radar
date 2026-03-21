from dotenv import load_dotenv
import os

# Load environment variables from .env
load_dotenv()

# FRED API Key
FRED_API_KEY = "e8f4311537ce3912928fcea4d0a27e66"


# --------------------------------------------------
# FRED Series Mapping
# --------------------------------------------------

FRED_SERIES = {

    "cpi": "CPIAUCSL",
    "core_cpi": "CPILFESL",
    "ppi": "PPIACO",

    "m2": "M2SL",

    "fed_rate": "FEDFUNDS",

    "10y_treasury": "DGS10",
    "2y_treasury": "DGS2",

    "unemployment": "UNRATE",

    "oil_price": "DCOILWTICO",

    "sp500": "SP500"
}