import csv
import datetime
import os
from typing import Any, Dict, List, Optional, Tuple

class CSVExporter:
    """Exports structured data dictionaries to CSV files safely."""

    def __init__(self, filepath: str):
        self.filepath = filepath

    def export(self, data: List[Dict[str, Any]], append: bool = False) -> int:
        """
        Exports a list of dicts to CSV.
        If append=True and the file exists, rows are added without duplicating the header.
        """
        if not data:
            print(f"No data to export to {self.filepath}.")
            return 0

        directory = os.path.dirname(os.path.abspath(self.filepath))
        if directory:
            os.makedirs(directory, exist_ok=True)

        file_exists = os.path.exists(self.filepath) and os.path.getsize(self.filepath) > 0

        if append and file_exists:
            # Read existing fieldnames to preserve column structure
            with open(self.filepath, "r", newline="", encoding="utf-8") as f:
                reader = csv.reader(f)
                try:
                    fieldnames = next(reader)
                except StopIteration:
                    fieldnames = list(data[0].keys())

            # Append mode: write rows only
            with open(self.filepath, "a", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
                writer.writerows(data)
        else:
            # New file or overwrite: extract all unique keys across rows
            fieldnames = list(data[0].keys())
            with open(self.filepath, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(data)

        print(f"Exported {len(data)} rows to {self.filepath}")
        return len(data)

def get_last_recorded_date(filepath: str) -> Optional[datetime.date]:
    """
    Reads the last date from an existing metrics CSV file.
    Omits the very last recorded row to avoid partial/incomplete day metrics.
    """
    if not os.path.exists(filepath) or os.path.getsize(filepath) == 0:
        return None

    try:
        with open(filepath, "r", newline="", encoding="utf-8") as f:
            reader = list(csv.reader(f))

        # We need at least header + 2 rows to drop the last one and pick the previous
        # If only header + 1 row, take the single data row
        if len(reader) <= 1:
            return None

        # Exclude header
        data_rows = reader[1:]
        if len(data_rows) > 1:
            data_rows = data_rows[:-1]  # drop last row

        last_row = data_rows[-1]
        date_str = last_row[0].strip()
        return datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
    except Exception as e:
        print(f"Warning: Could not read previous date from {filepath}: {e}")
        return None

