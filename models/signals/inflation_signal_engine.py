class InflationSignalEngine:

    def __init__(self):
        pass

    def generate_signals(self, prob_3m, prob_6m):

        # --------------------------------------------------
        # REGIME DETECTION (6M = STRUCTURAL)
        # --------------------------------------------------

        if prob_6m > 0.65:
            base_regime = "inflation_up"

        elif prob_6m < 0.35:
            base_regime = "disinflation"

        else:
            base_regime = "neutral"

        # --------------------------------------------------
        # SHORT-TERM OVERLAY (3M)
        # --------------------------------------------------

        if prob_3m > 0.7:
            short_term = "up_strong"
        elif prob_3m > 0.6:
            short_term = "up"
        elif prob_3m < 0.3:
            short_term = "down_strong"
        elif prob_3m < 0.4:
            short_term = "down"
        else:
            short_term = "neutral"

        # --------------------------------------------------
        # FINAL REGIME (kombiniert)
        # --------------------------------------------------

        if base_regime == "inflation_up":

            if short_term.startswith("up"):
                regime = "inflation_up_strong"
            elif short_term.startswith("down"):
                regime = "inflation_peak"
            else:
                regime = "inflation_up"

        elif base_regime == "disinflation":

            if short_term.startswith("down"):
                regime = "disinflation_strong"
            elif short_term.startswith("up"):
                regime = "inflation_bottoming"
            else:
                regime = "disinflation"

        else:
            # 🔥 WICHTIG: hier kommt dein Fall rein
            if short_term.startswith("up"):
                regime = "short_term_reflation"
            elif short_term.startswith("down"):
                regime = "short_term_disinflation"
            else:
                regime = "neutral"

        # --------------------------------------------------
        # ASSET SIGNALS
        # --------------------------------------------------

        if regime == "inflation_up_strong":
            return {
                "regime": regime,
                "bonds": "short_duration",
                "equity": "value_over_growth",
                "usd": "bullish",
                "gold": "neutral"
            }

        elif regime == "disinflation_strong":
            return {
                "regime": regime,
                "bonds": "long_duration",
                "equity": "growth_bullish",
                "usd": "bearish",
                "gold": "bullish"
            }

        elif regime == "inflation_peak":
            return {
                "regime": regime,
                "bonds": "neutral",
                "equity": "defensive",
                "usd": "neutral",
                "gold": "positive"
            }

        elif regime == "inflation_bottoming":
            return {
                "regime": regime,
                "bonds": "neutral",
                "equity": "cyclical_bullish",
                "usd": "weakening",
                "gold": "neutral"
            }

        elif regime == "short_term_reflation":
            return {
                "regime": regime,
                "bonds": "short_duration_light",
                "equity": "cyclical",
                "usd": "slightly_bullish",
                "gold": "neutral"
            }

        elif regime == "short_term_disinflation":
            return {
                "regime": regime,
                "bonds": "long_duration_light",
                "equity": "slightly_bullish",
                "usd": "slightly_bearish",
                "gold": "positive"
            }

        else:
            return {
                "regime": regime,
                "bonds": "neutral",
                "equity": "neutral",
                "usd": "neutral",
                "gold": "neutral"
            }