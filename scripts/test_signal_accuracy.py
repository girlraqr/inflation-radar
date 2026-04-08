from services.signal_accuracy_service import SignalAccuracyService


def run():
    print("=== TEST: SIGNAL ACCURACY ===")

    service = SignalAccuracyService()

    result = service.build_signal_accuracy(user_id=1)

    print("\n--- OVERALL ---")
    print(result["overall"])

    print("\n--- BY REGIME ---")
    for k, v in result["by_regime"].items():
        print(k, v)


if __name__ == "__main__":
    run()