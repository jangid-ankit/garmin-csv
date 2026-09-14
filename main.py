import argparse
import datetime
import os
import sys
from typing import Optional

from garmin.auth import authenticate, AuthenticationError
from garmin.client import GarminClient
from garmin.exporters import CSVExporter, get_last_recorded_date
from garmin.transformers import (
    transform_activities,
    merge_metrics_and_activities,
)

def run_export(
    mode: str,
    start_date: Optional[datetime.date] = None,
    end_date: Optional[datetime.date] = None,
    output_path: Optional[str] = None,
    append: bool = False,
    workers: int = 5,
) -> None:
    """Orchestrates authentication, data fetching, transformation, and export."""
    try:
        authenticate()
    except AuthenticationError as e:
        print(f"\nAuthentication Error: {e}")
        sys.exit(1)

    client = GarminClient()
    client.connect_device()

    today = datetime.date.today()
    end_date = end_date or today

    # Determine default output file based on mode
    default_outputs = {
        "all": os.path.join("output", "metrics_activities.csv"),
        "activities": os.path.join("output", "only_activities.csv"),
        "metrics": os.path.join("output", "only_metrics.csv"),
    }
    output_path = output_path or default_outputs.get(mode, os.path.join("output", "garmin_export.csv"))

    if mode == "activities":
        print(f"\n--- Fetching Activities ---")
        raw_activities = client.fetch_raw_activities()
        activities = transform_activities(raw_activities)
        exporter = CSVExporter(output_path)
        exporter.export(activities, append=append)

    elif mode == "metrics":
        print(f"\n--- Fetching Daily Health Metrics ---")
        if append and os.path.exists(output_path):
            last_date = get_last_recorded_date(output_path)
            if last_date:
                start_date = last_date + datetime.timedelta(days=1)
                print(f"Resuming incremental fetch starting from {start_date}...")
            else:
                start_date = start_date or client.registered_date
        else:
            start_date = start_date or client.registered_date

        # Custom start_date is assigned below (to avoid my personal device registration date discrepancy, for normal usage comment out the next line)
        start_date = datetime.date(2024,12,23)
        daily_metrics = client.fetch_metrics_range(start_date, end_date, max_workers=workers)
        exporter = CSVExporter(output_path)
        exporter.export(daily_metrics, append=append)

    elif mode == "all":
        print(f"\n--- Fetching All Data (Metrics + Activities) ---")
        start_date = start_date or client.registered_date

        # Custom start_date is assigned below (to avoid my personal device registration date discrepancy, for normal usage comment out the next line)
        start_date = datetime.date(2024,12,23)
        
        daily_metrics = client.fetch_metrics_range(start_date, end_date, max_workers=workers)
        raw_activities = client.fetch_raw_activities()
        activities = transform_activities(raw_activities)

        merged = merge_metrics_and_activities(daily_metrics, activities)
        exporter = CSVExporter(output_path)
        exporter.export(merged, append=append)
    else:
        print(f"Unknown mode: {mode}")
        sys.exit(1)


def interactive_menu():
    """Provides a friendly interactive CLI menu when no arguments are passed."""
    print("=" * 50)
    print("           Garmin Data Exporter")
    print("=" * 50)
    print("1) All Data (Health metrics merged with primary activities)")
    print("2) Activities Only")
    print("3) Health Metrics Only (All available history)")
    print("4) Health Metrics Only (Recent 30 days)")
    print("5) Append Latest Health Metrics to existing CSV")
    print("q) Exit")
    print("-" * 50)

    choice = input("Select an option [1-5, q]: ").strip().lower()

    if choice == "1":
        run_export(mode="all")
    elif choice == "2":
        run_export(mode="activities")
    elif choice == "3":
        run_export(mode="metrics")
    elif choice == "4":
        start = datetime.date.today() - datetime.timedelta(days=30)
        run_export(mode="metrics", start_date=start)
    elif choice == "5":
        run_export(mode="metrics", append=True)
    elif choice == "q":
        print("Goodbye.")
        sys.exit(0)
    else:
        print("Invalid option selected.")
        sys.exit(1)


def parse_date(date_str: str) -> datetime.date:
    """Parses a YYYY-MM-DD date string."""
    try:
        return datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        raise argparse.ArgumentTypeError(f"Invalid date '{date_str}'. Expected format: YYYY-MM-DD")


def main():
    parser = argparse.ArgumentParser(
        description="Export Garmin health metrics and activities to clean CSV files.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                           # Launch interactive menu
  python main.py --mode all                # Export all metrics merged with activities
  python main.py --mode activities         # Export activities only
  python main.py --mode metrics --days 30  # Export health metrics for the past 30 days
  python main.py --mode metrics --append   # Incrementally append latest metrics
        """,
    )

    parser.add_argument(
        "-m", "--mode",
        choices=["all", "activities", "metrics"],
        help="Data type to export: 'all' (merged), 'activities', or 'metrics'.",
    )
    parser.add_argument(
        "-d", "--days",
        type=int,
        help="Number of past days to fetch (e.g., 30). Overrides --start-date.",
    )
    parser.add_argument(
        "-s", "--start-date",
        type=parse_date,
        help="Start date for metrics fetch (YYYY-MM-DD). Defaults to device registration date.",
    )
    parser.add_argument(
        "-e", "--end-date",
        type=parse_date,
        help="End date for metrics fetch (YYYY-MM-DD). Defaults to today.",
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        help="Custom destination CSV path. Defaults to output/<mode>.csv.",
    )
    parser.add_argument(
        "-a", "--append",
        action="store_true",
        help="Append new metrics to an existing file instead of overwriting.",
    )
    parser.add_argument(
        "-w", "--workers",
        type=int,
        default=5,
        help="Number of concurrent worker threads for fetching daily metrics (default: 5).",
    )

    # If run with no CLI arguments, open interactive menu
    if len(sys.argv) == 1:
        interactive_menu()
        return

    args = parser.parse_args()

    start_date = args.start_date
    if args.days:
        start_date = datetime.date.today() - datetime.timedelta(days=args.days)

    mode = args.mode or "all"
    run_export(
        mode=mode,
        start_date=start_date,
        end_date=args.end_date,
        output_path=args.output,
        append=args.append,
        workers=args.workers,
    )


if __name__ == "__main__":
    main()
