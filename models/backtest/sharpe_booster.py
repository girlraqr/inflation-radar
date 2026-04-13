from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping


@dataclass(slots=True)
class SharpeBoosterConfig:
    enabled: bool = True

    # Continuous scaling auf prob_3m
    min_prob: float = 0.50
    max_prob: float = 0.90

    # Unterhalb min_prob fast raus, oberhalb max_prob volle / erhöhte Exponierung
    min_scale: float = 0.00
    mid_scale: float = 1.00
    max_scale: float = 1.20

    # Form der Kurve
    curve_power: float = 1.35

    # 6m-Bestätigung
    use_prob_6m_confirmation: bool = True
    prob_6m_penalty_threshold: float = 0.50
    prob_6m_penalty_scale: float = 0.85

    # Wenn 3m und 6m stark auseinanderliegen → Risiko runter
    use_horizon_disagreement_penalty: bool = True
    disagreement_threshold: float = 0.20
    disagreement_penalty_scale: float = 0.80

    # Unsicherheitsstrafe auf Basis der max Regime-Wahrscheinlichkeit
    use_uncertainty_penalty: bool = True
    uncertainty_floor: float = 0.35
    uncertainty_ceiling: float = 0.75
    uncertainty_min_scale: float = 0.75
    uncertainty_max_scale: float = 1.05

    # Residualgewicht
    residual_asset: str = "cash"

    # Sicherheitsgrenzen
    min_leverage: float = 0.0
    max_leverage: float = 1.60


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _clip(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _normalize_01(value: float, low: float, high: float) -> float:
    if high <= low:
        return 0.0
    return _clip((value - low) / (high - low), 0.0, 1.0)


def _continuous_confidence_scale(prob_3m: float, cfg: SharpeBoosterConfig) -> float:
    """
    Mappt prob_3m kontinuierlich auf einen Scale-Faktor.
    Unterhalb min_prob -> Richtung min_scale
    Oberhalb max_prob -> Richtung max_scale
    """
    x = _normalize_01(prob_3m, cfg.min_prob, cfg.max_prob)
    curved = x ** cfg.curve_power

    if curved <= 0.5:
        inner = curved / 0.5
        return cfg.min_scale + inner * (cfg.mid_scale - cfg.min_scale)

    inner = (curved - 0.5) / 0.5
    return cfg.mid_scale + inner * (cfg.max_scale - cfg.mid_scale)


def _uncertainty_scale(
    regime_confidence: float,
    cfg: SharpeBoosterConfig,
) -> float:
    """
    regime_confidence = max(adjusted regime probs)
    Flache Verteilungen = unsicher = kleinerer Scale.
    """
    x = _normalize_01(
        regime_confidence,
        cfg.uncertainty_floor,
        cfg.uncertainty_ceiling,
    )
    return cfg.uncertainty_min_scale + x * (
        cfg.uncertainty_max_scale - cfg.uncertainty_min_scale
    )


def compute_confidence_multiplier(
    signal_row: Mapping[str, Any],
    config: SharpeBoosterConfig | None = None,
) -> float:
    cfg = config or SharpeBoosterConfig()

    if not cfg.enabled:
        return 1.0

    prob_3m = _safe_float(signal_row.get("prob_3m"), 0.0)
    prob_6m = _safe_float(signal_row.get("prob_6m"), 0.0)
    regime_confidence = _safe_float(signal_row.get("regime_confidence"), 0.50)

    scale = _continuous_confidence_scale(prob_3m, cfg)

    if cfg.use_prob_6m_confirmation and prob_6m < cfg.prob_6m_penalty_threshold:
        scale *= cfg.prob_6m_penalty_scale

    if cfg.use_horizon_disagreement_penalty:
        disagreement = abs(prob_3m - prob_6m)
        if disagreement > cfg.disagreement_threshold:
            scale *= cfg.disagreement_penalty_scale

    if cfg.use_uncertainty_penalty:
        scale *= _uncertainty_scale(regime_confidence, cfg)

    return _clip(scale, cfg.min_leverage, cfg.max_leverage)


def apply_sharpe_booster(
    weights: Dict[str, float],
    signal_row: Mapping[str, Any],
    config: SharpeBoosterConfig | None = None,
) -> Dict[str, float]:
    """
    Skaliert aktive Gewichte mit einem kontinuierlichen Confidence-Multiplikator.
    Restgewicht fließt in residual_asset.
    """
    cfg = config or SharpeBoosterConfig()

    if not cfg.enabled:
        return dict(weights)

    if not weights:
        return {}

    scaled = dict(weights)
    residual_asset = cfg.residual_asset

    if residual_asset not in scaled:
        scaled[residual_asset] = 0.0

    multiplier = compute_confidence_multiplier(signal_row, cfg)

    active_assets = [asset for asset in scaled.keys() if asset != residual_asset]

    for asset in active_assets:
        scaled[asset] = _safe_float(scaled.get(asset), 0.0) * multiplier

    active_sum = sum(_safe_float(scaled.get(asset), 0.0) for asset in active_assets)
    scaled[residual_asset] = 1.0 - active_sum

    return scaled


def summarize_booster_state(
    signal_row: Mapping[str, Any],
    config: SharpeBoosterConfig | None = None,
) -> Dict[str, float]:
    cfg = config or SharpeBoosterConfig()
    multiplier = compute_confidence_multiplier(signal_row, cfg)

    return {
        "prob_3m": _safe_float(signal_row.get("prob_3m"), 0.0),
        "prob_6m": _safe_float(signal_row.get("prob_6m"), 0.0),
        "regime_confidence": _safe_float(signal_row.get("regime_confidence"), 0.0),
        "multiplier": multiplier,
    }