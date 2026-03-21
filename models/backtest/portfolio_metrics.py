from __future__ import annotations

import numpy as np
import pandas as pd


def compute_drawdown(equity_curve: pd.Series) -> pd.Series:
    running_max = equity_curve.cummax()
    return equity_curve / running_max - 1.0


def annualized_return(returns: pd.Series, periods_per_year: int = 12) -> float:
    returns = returns.dropna()
    if returns.empty:
        return 0.0
    total_return = (1.0 + returns).prod()
    n_periods = len(returns)
    return total_return ** (periods_per_year / n_periods) - 1.0


def annualized_volatility(returns: pd.Series, periods_per_year: int = 12) -> float:
    returns = returns.dropna()
    if returns.empty:
        return 0.0
    return returns.std(ddof=0) * np.sqrt(periods_per_year)


def sharpe_ratio(
    returns: pd.Series,
    risk_free_rate: float = 0.0,
    periods_per_year: int = 12,
) -> float:
    returns = returns.dropna()
    if returns.empty:
        return 0.0

    rf_per_period = (1.0 + risk_free_rate) ** (1.0 / periods_per_year) - 1.0
    excess = returns - rf_per_period
    vol = excess.std(ddof=0)
    if vol == 0 or np.isnan(vol):
        return 0.0
    return excess.mean() / vol * np.sqrt(periods_per_year)


def max_drawdown(returns: pd.Series) -> float:
    returns = returns.dropna()
    if returns.empty:
        return 0.0
    equity = (1.0 + returns).cumprod()
    dd = compute_drawdown(equity)
    return float(dd.min())


def hit_rate(returns: pd.Series) -> float:
    returns = returns.dropna()
    if returns.empty:
        return 0.0
    return float((returns > 0).mean())


def summarize_performance(
    returns: pd.Series,
    turnover: pd.Series | None = None,
    periods_per_year: int = 12,
    risk_free_rate: float = 0.0,
) -> dict:
    returns = returns.dropna()

    equity = (1.0 + returns).cumprod() if not returns.empty else pd.Series(dtype=float)

    out = {
        "total_return": float(equity.iloc[-1] - 1.0) if not equity.empty else 0.0,
        "annual_return": float(annualized_return(returns, periods_per_year)),
        "annual_volatility": float(annualized_volatility(returns, periods_per_year)),
        "sharpe": float(sharpe_ratio(returns, risk_free_rate, periods_per_year)),
        "max_drawdown": float(max_drawdown(returns)),
        "hit_rate": float(hit_rate(returns)),
        "observations": int(len(returns)),
    }

    if turnover is not None and not turnover.dropna().empty:
        out["avg_turnover"] = float(turnover.dropna().mean())
        out["annual_turnover"] = float(turnover.dropna().mean() * periods_per_year)
    else:
        out["avg_turnover"] = 0.0
        out["annual_turnover"] = 0.0

    return out