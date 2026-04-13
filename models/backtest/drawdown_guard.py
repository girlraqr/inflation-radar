from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class DrawdownGuardConfig:
    enabled: bool = True

    # Schwellen auf Equity-Drawdown-Basis
    mild_drawdown_threshold: float = -0.05
    severe_drawdown_threshold: float = -0.10

    # Exponierungsreduktion
    mild_exposure_scale: float = 0.70
    severe_exposure_scale: float = 0.40

    # Erholung: sobald aktueller Drawdown besser als dieser Wert ist,
    # darf wieder auf volle Exponierung gegangen werden.
    recovery_drawdown_threshold: float = -0.03


class DrawdownGuardState:
    """
    Hält Peak/aktuellen Drawdown und liefert den aktuellen Risiko-Multiplikator.
    """

    def __init__(self, config: DrawdownGuardConfig | None = None) -> None:
        self.config = config or DrawdownGuardConfig()
        self.peak_equity = 1.0
        self.current_drawdown = 0.0
        self.current_scale = 1.0

    def update(self, equity_curve: float) -> float:
        """
        Aktualisiert Peak und Drawdown auf Basis der bereits realisierten Equity.
        Gibt den Scale zurück, der für die NÄCHSTE Periode verwendet werden soll.
        """
        if not self.config.enabled:
            self.current_scale = 1.0
            return self.current_scale

        if equity_curve > self.peak_equity:
            self.peak_equity = equity_curve

        if self.peak_equity <= 0:
            self.current_drawdown = 0.0
        else:
            self.current_drawdown = equity_curve / self.peak_equity - 1.0

        # Recovery zuerst prüfen
        if self.current_drawdown >= self.config.recovery_drawdown_threshold:
            self.current_scale = 1.0
            return self.current_scale

        # Dann abgestufte Risikoreduktion
        if self.current_drawdown <= self.config.severe_drawdown_threshold:
            self.current_scale = self.config.severe_exposure_scale
        elif self.current_drawdown <= self.config.mild_drawdown_threshold:
            self.current_scale = self.config.mild_exposure_scale
        else:
            self.current_scale = 1.0

        return self.current_scale

    def get_scale(self) -> float:
        return self.current_scale

    def get_drawdown(self) -> float:
        return self.current_drawdown


def apply_drawdown_scale_to_weights(
    weight_map: dict[str, float],
    scale: float,
    residual_asset: str = "cash",
) -> dict[str, float]:
    """
    Skaliert aktive Gewichte und schiebt das Restgewicht in residual_asset.
    """
    if not weight_map:
        return {}

    scaled = dict(weight_map)

    if residual_asset not in scaled:
        scaled[residual_asset] = 0.0

    active_assets = [asset for asset in scaled.keys() if asset != residual_asset]

    for asset in active_assets:
        scaled[asset] = float(scaled.get(asset, 0.0)) * float(scale)

    active_sum = sum(float(scaled.get(asset, 0.0)) for asset in active_assets)
    scaled[residual_asset] = 1.0 - active_sum

    return scaled