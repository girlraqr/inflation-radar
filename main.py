import sys
import argparse
from datetime import datetime, timezone

from data.data_fetcher import run_pipeline
from models.signals import gold_signal, inflation_regime


def print_header():

    now = datetime.now(timezone.utc)

    print("\n")
    print("=" * 60)
    print(" REAL INFLATION RADAR")
    print("=" * 60)
    print(f"Generated: {now.strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print("=" * 60)
    print("\n")


def print_report(result):

    real_inflation = result["real_inflation_estimate"]
    official_cpi = result["official_cpi"]
    hidden = result["hidden_inflation"]

    consumer = result["consumer_score"]
    monetary = result["monetary_score"]
    asset = result["asset_score"]

    regime = inflation_regime(real_inflation)

    # Gold reagiert eher auf monetären Druck
    signal = gold_signal(real_inflation, monetary)

    print("Inflation Scores")
    print("-" * 30)

    print(f"Consumer Inflation Score : {consumer:.2f}")
    print(f"Monetary Pressure Score : {monetary:.2f}")
    print(f"Asset Inflation Score   : {asset:.2f}")

    print("\nOfficial vs Real Inflation")
    print("-" * 30)

    print(f"Official CPI            : {official_cpi:.2f} %")
    print(f"Real Inflation Estimate : {real_inflation:.2f} %")
    print(f"Hidden Inflation        : {hidden:.2f} %")

    print("\nMarket Signals")
    print("-" * 30)

    print(f"Inflation Regime        : {regime}")
    print(f"Gold Hedge Signal       : {signal}")

    print("\n")


def run_cli():

    parser = argparse.ArgumentParser(
        description="Real Inflation Radar"
    )

    parser.add_argument(
        "--json",
        action="store_true",
        help="Return result as JSON"
    )

    args = parser.parse_args()

    try:

        result = run_pipeline()

    except Exception as e:

        print("Pipeline failed")
        print(e)

        sys.exit(1)

    if args.json:

        import json

        print(json.dumps(result, indent=2))

    else:

        print_header()
        print_report(result)


def main():
    run_cli()


if __name__ == "__main__":
    main()