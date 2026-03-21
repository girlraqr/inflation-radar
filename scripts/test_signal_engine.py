from models.signals.inflation_signal_engine import InflationSignalEngine


def run_tests():

    engine = InflationSignalEngine()

    test_cases = [
        {"prob_3m": 0.75, "prob_6m": 0.80},
        {"prob_3m": 0.65, "prob_6m": 0.70},
        {"prob_3m": 0.55, "prob_6m": 0.55},
        {"prob_3m": 0.40, "prob_6m": 0.35},
        {"prob_3m": 0.25, "prob_6m": 0.20},
    ]

    print("\n🔥 SIGNAL ENGINE TEST\n")

    for i, case in enumerate(test_cases):

        prob_3m = case["prob_3m"]
        prob_6m = case["prob_6m"]

        signals = engine.generate_signals(prob_3m, prob_6m)

        print(f"Test Case {i+1}")
        print(f"Input: 3M={prob_3m:.2f}, 6M={prob_6m:.2f}")
        print(f"Output: {signals}")
        print("-" * 50)


if __name__ == "__main__":
    run_tests()