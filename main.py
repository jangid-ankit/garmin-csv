import argparse
import datetime
import os
import sys
from typing import Optional

from garmin.auth import authenticate, AuthenticationError
from garmin.client import GarminClient
from garmin.exporters import CSVExporter, get_last_recorded_date
from garmin.sqlite_exporter import SQLiteExporter
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
        # or better have the user select what device he wants the data to be picked from.
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


def run_sqlite_export(
    db_path: str = "output/garmin_data.db",
    start_date: Optional[datetime.date] = None,
    end_date: Optional[datetime.date] = None,
    workers: int = 5,
) -> None:
    """Exports 3 tables (activities, metrics, all_data) to a SQLite database."""
    try:
        authenticate()
    except AuthenticationError as e:
        print(f"\nAuthentication Error: {e}")
        sys.exit(1)

    client = GarminClient()
    client.connect_device()

    today = datetime.date.today()
    end_date = end_date or today
    if start_date is None:
        start_date = datetime.date(2024, 12, 23)

    print(f"\nTarget SQLite Database: {db_path}")
    print(f"--- Fetching Data for SQLite Export ({start_date} to {end_date}) ---")

    daily_metrics = client.fetch_metrics_range(start_date, end_date, max_workers=workers)
    raw_activities = client.fetch_raw_activities()
    activities = transform_activities(raw_activities)
    merged = merge_metrics_and_activities(daily_metrics, activities)

    print(f"\n--- Exporting to SQLite Database ({db_path}) ---")
    exporter = SQLiteExporter(db_path)
    results = exporter.export_all(activities=activities, metrics=daily_metrics, all_data=merged)

    print(f"✓ Table 'activities': {results.get('activities', 0)} records inserted.")
    print(f"✓ Table 'metrics':    {results.get('metrics', 0)} records inserted.")
    print(f"✓ Table 'all_data':   {results.get('all_data', 0)} records inserted.")
    print(f"\nExport complete! Database saved to: {os.path.abspath(db_path)}")


def run_sqlite_update(
    db_path: str = "output/garmin_data.db",
    workers: int = 5,
) -> None:
    """
    Checks an existing SQLite database, determines missing date range,
    and fetches & upserts only the delta into all 3 tables.
    """
    exporter = SQLiteExporter(db_path)
    if not exporter.db_exists():
        print(f"\nNotice: SQLite database not found at '{db_path}'.")
        choice = input("Would you like to perform a full initial export? [y/N]: ").strip().lower()
        if choice == "y":
            run_sqlite_export(db_path=db_path, workers=workers)
        return

    latest_date = exporter.get_latest_metric_date()
    today = datetime.date.today()

    if latest_date is None:
        print(f"\nNotice: No health metric records found in '{db_path}'. Performing full export...")
        run_sqlite_export(db_path=db_path, workers=workers)
        return

    days_delta = (today - latest_date).days
    print(f"\n--- Checking SQLite Database: {db_path} ---")
    print(f"Latest metric recorded: {latest_date}")
    print(f"Current date:           {today}")

    if days_delta <= 0:
        print(f"✓ Database is already up to date through {latest_date}! No new health metrics to fetch.")
        choice = input("Check for recent activities anyway? [y/N]: ").strip().lower()
        if choice != "y":
            return
        fetch_start = latest_date
    else:
        # Re-fetch starting from latest_date to refresh potentially incomplete day metrics
        fetch_start = latest_date
        days_to_fetch = (today - fetch_start).days + 1
        print(f"Fetching {days_to_fetch} day(s) of data ({fetch_start} to {today}) to update database...")

    try:
        authenticate()
    except AuthenticationError as e:
        print(f"\nAuthentication Error: {e}")
        sys.exit(1)

    client = GarminClient()
    client.connect_device()

    daily_metrics = client.fetch_metrics_range(fetch_start, today, max_workers=workers)
    raw_activities = client.fetch_raw_activities()
    activities = transform_activities(raw_activities)
    merged = merge_metrics_and_activities(daily_metrics, activities)

    print(f"\n--- Updating SQLite Database ({db_path}) ---")
    results = exporter.export_all(activities=activities, metrics=daily_metrics, all_data=merged)

    print(f"✓ Table 'activities': {results.get('activities', 0)} records upserted.")
    print(f"✓ Table 'metrics':    {results.get('metrics', 0)} records upserted.")
    print(f"✓ Table 'all_data':   {results.get('all_data', 0)} records upserted.")
    print(f"\nUpdate complete! Database {db_path} is now up to date through {today}.")


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
    print("6) Export all data to SQLite database")
    print("7) Update existing SQLite database")
    print("q) Exit")
    print("-" * 50)

    choice = input("Select an option [1-7, q]: ").strip().lower()

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
    elif choice == "6":
        db_input = input("Enter SQLite DB path [default: output/garmin_data.db]: ").strip()
        run_sqlite_export(db_path=db_input or "output/garmin_data.db")
    elif choice == "7":
        db_input = input("Enter SQLite DB path [default: output/garmin_data.db]: ").strip()
        run_sqlite_update(db_path=db_input or "output/garmin_data.db")
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
        description="Export Garmin health metrics and activities to clean CSV or SQLite files.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                           # Launch interactive menu
  python main.py --mode all                # Export all metrics merged with activities to CSV
  python main.py --mode activities         # Export activities only to CSV
  python main.py --mode metrics --days 30  # Export health metrics for the past 30 days to CSV
  python main.py --mode metrics --append   # Incrementally append latest metrics to existing CSV
  python main.py --sqlite-export           # Export 3 tables to SQLite database
  python main.py --sqlite-update           # Check & incrementally update SQLite database
        """,
    )

    parser.add_argument(
        "-m", "--mode",
        choices=["all", "activities", "metrics", "sqlite-export", "sqlite-update"],
        help="Data type to export: 'all' (merged), 'activities', 'metrics', 'sqlite-export', or 'sqlite-update'.",
    )
    parser.add_argument(
        "--sqlite-export",
        action="store_true",
        help="Export activities, metrics, and all_data into SQLite database.",
    )
    parser.add_argument(
        "--sqlite-update",
        action="store_true",
        help="Check and incrementally update an existing SQLite database.",
    )
    parser.add_argument(
        "--db-path",
        type=str,
        default="output/garmin_data.db",
        help="Custom SQLite database path (default: output/garmin_data.db).",
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
        help="Custom destination file path. Defaults to output/<mode>.csv or output/garmin_data.db.",
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

    # Route SQLite commands
    target_db = args.db_path or args.output or "output/garmin_data.db"
    if args.sqlite_export or args.mode == "sqlite-export":
        run_sqlite_export(
            db_path=target_db,
            start_date=start_date,
            end_date=args.end_date,
            workers=args.workers,
        )
        return

    if args.sqlite_update or args.mode == "sqlite-update":
        run_sqlite_update(
            db_path=target_db,
            workers=args.workers,
        )
        return

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
