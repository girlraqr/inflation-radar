from dotenv import load_dotenv
import os
from dataclasses import dataclass

# --------------------------------------------------
# LOAD ENV
# --------------------------------------------------

load_dotenv()


# --------------------------------------------------
# FRED API
# --------------------------------------------------

FRED_API_KEY = os.getenv(
    "FRED_API_KEY",
    "e8f4311537ce3912928fcea4d0a27e66"
)


# --------------------------------------------------
# FRED SERIES
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


# --------------------------------------------------
# SETTINGS (WICHTIG!)
# --------------------------------------------------

@dataclass(slots=True)
class Settings:
    # App
    app_name: str = os.getenv("APP_NAME", "Inflation Radar API")
    app_env: str = os.getenv("APP_ENV", "development")
    debug: bool = os.getenv("DEBUG", "true").lower() == "true"

    # Database
    database_path: str = os.getenv("DATABASE_PATH", "storage/app.db")

    # JWT
    jwt_secret_key: str = os.getenv(
        "JWT_SECRET_KEY",
        "CHANGE_THIS_IN_PRODUCTION_TO_A_LONG_RANDOM_SECRET"
    )
    jwt_algorithm: str = os.getenv("JWT_ALGORITHM", "HS256")
    access_token_expire_minutes: int = int(
        os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440")
    )

    # CORS
    cors_origins_raw: str = os.getenv(
        "CORS_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000"
    )

    @property
    def cors_origins(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.cors_origins_raw.split(",")
            if origin.strip()
        ]


# 👉 DAS HAT DIR GEFEHLT
settings = Settings()