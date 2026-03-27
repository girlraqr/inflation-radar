from __future__ import annotations

from typing import Dict, List


class MappingValidationError(Exception):
    def __init__(self, errors: List[str]):
        self.errors = errors
        super().__init__("Mapping validation failed")


class MappingValidationService:

    def validate_create(self, data: Dict) -> None:
        errors: List[str] = []

        self._validate_required_fields(data, errors)
        self._validate_weights(data, errors)

        if errors:
            raise MappingValidationError(errors)

    def validate_bulk(self, rows: List[Dict]) -> None:
        errors: List[str] = []

        if not rows:
            errors.append("rows must not be empty")
            raise MappingValidationError(errors)

        for row in rows:
            self._validate_required_fields(row, errors)
            self._validate_weights(row, errors)

        self._validate_group_consistency(rows, errors)

        if errors:
            raise MappingValidationError(errors)

    # ---------------------------------------------------
    # FIELD VALIDATION
    # ---------------------------------------------------

    def _validate_required_fields(self, data: Dict, errors: List[str]) -> None:
        required_fields = [
            "signal",
            "regime",
            "theme",
            "theme_weight",
            "asset",
            "asset_weight",
        ]

        for field in required_fields:
            if field not in data or data[field] is None:
                errors.append(f"Missing required field: {field}")

    # ---------------------------------------------------
    # WEIGHT VALIDATION
    # ---------------------------------------------------

    def _validate_weights(self, data: Dict, errors: List[str]) -> None:
        theme_weight = data.get("theme_weight")
        asset_weight = data.get("asset_weight")

        if not self._is_valid_weight(theme_weight):
            errors.append("theme_weight must be between 0 and 1")

        if not self._is_valid_weight(asset_weight):
            errors.append("asset_weight must be between 0 and 1")

    def _is_valid_weight(self, value) -> bool:
        try:
            v = float(value)
            return 0.0 <= v <= 1.0
        except (TypeError, ValueError):
            return False

    # ---------------------------------------------------
    # GROUP VALIDATION
    # ---------------------------------------------------

    def _validate_group_consistency(self, rows: List[Dict], errors: List[str]) -> None:
        theme_weight_reference: Dict[str, float] = {}
        asset_totals_by_theme: Dict[str, float] = {}

        for row in rows:
            theme = str(row.get("theme")).strip()
            signal = str(row.get("signal")).strip()
            regime = str(row.get("regime")).strip()

            if not signal:
                errors.append("signal must not be empty")
            if not regime:
                errors.append("regime must not be empty")
            if not theme:
                errors.append("theme must not be empty")

            try:
                theme_weight = float(row.get("theme_weight", 0))
                asset_weight = float(row.get("asset_weight", 0))
            except (TypeError, ValueError):
                continue

            if theme in theme_weight_reference:
                if not self._approx_equal(theme_weight_reference[theme], theme_weight):
                    errors.append(
                        f"theme_weight must be identical for all rows of theme '{theme}'"
                    )
            else:
                theme_weight_reference[theme] = theme_weight

            asset_totals_by_theme[theme] = asset_totals_by_theme.get(theme, 0.0) + asset_weight

        total_theme_weight = sum(theme_weight_reference.values())
        if not self._approx_equal(total_theme_weight, 1.0):
            errors.append(
                f"sum of distinct theme_weight values must be 1.0 (got {total_theme_weight:.4f})"
            )

        for theme, total_asset_weight in asset_totals_by_theme.items():
            if not self._approx_equal(total_asset_weight, 1.0):
                errors.append(
                    f"asset weights for theme '{theme}' must sum to 1.0 (got {total_asset_weight:.4f})"
                )

    def _approx_equal(self, a: float, b: float, tol: float = 1e-6) -> bool:
        return abs(a - b) <= tol