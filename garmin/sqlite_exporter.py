import contextlib
import datetime
import os
import sqlite3
from typing import Any, Dict, Generator, List, Optional, Tuple


class SQLiteExporter:
    """Exports and incrementally updates Garmin data across 3 tables in a SQLite database."""

    def __init__(self, db_path: str = "output/garmin_data.db"):
        self.db_path = db_path
        self._ensure_directory()

    def _ensure_directory(self) -> None:
        """Ensure the parent directory of the database file exists."""
        dir_name = os.path.dirname(os.path.abspath(self.db_path))
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)

    @contextlib.contextmanager
    def connect(self) -> Generator[sqlite3.Connection, None, None]:
        """Context manager that opens and cleanly closes a SQLite connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def db_exists(self) -> bool:
        """Check if the SQLite database file exists and is not empty."""
        return os.path.exists(self.db_path) and os.path.getsize(self.db_path) > 0

    def table_exists(self, table_name: str) -> bool:
        """Check if a table exists in the SQLite database."""
        if not os.path.exists(self.db_path):
            return False
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
                (table_name,),
            )
            return cursor.fetchone() is not None

    def get_existing_columns(self, conn: sqlite3.Connection, table_name: str) -> List[str]:
        """Fetch list of column names for an existing table."""
        cursor = conn.cursor()
        cursor.execute(f'PRAGMA table_info("{table_name}")')
        return [row["name"] for row in cursor.fetchall()]

    @staticmethod
    def infer_sql_type(values: List[Any]) -> str:
        """Infer SQLite data type (INTEGER, REAL, TEXT) from sample values."""
        has_float = False
        has_int = False
        for val in values:
            if val is None or val == "":
                continue
            if isinstance(val, bool):
                return "INTEGER"
            elif isinstance(val, int):
                has_int = True
            elif isinstance(val, float):
                has_float = True
            elif isinstance(val, (datetime.date, datetime.datetime)):
                return "TEXT"
            else:
                return "TEXT"
        if has_float:
            return "REAL"
        if has_int:
            return "INTEGER"
        return "TEXT"

    def ensure_table_schema(
        self,
        conn: sqlite3.Connection,
        table_name: str,
        records: List[Dict[str, Any]],
        primary_key: str,
    ) -> List[str]:
        """
        Ensures the table exists with the specified primary key,
        and dynamically adds any new columns from records via ALTER TABLE if needed.
        Returns the ordered list of all columns for insertion.
        """
        if not records:
            if self.table_exists(table_name):
                return self.get_existing_columns(conn, table_name)
            return []

        # Collect all unique keys in records, ensuring primary_key is first
        all_keys: Dict[str, None] = {primary_key: None}
        for r in records:
            for k in r.keys():
                all_keys[k] = None
        columns = list(all_keys.keys())

        existing_cols = self.get_existing_columns(conn, table_name)
        cursor = conn.cursor()

        if not existing_cols:
            # Create new table
            col_defs = []
            for col in columns:
                sample_vals = [r.get(col) for r in records[:100]]
                sql_type = self.infer_sql_type(sample_vals)
                if col == primary_key:
                    col_defs.append(f'"{col}" {sql_type} PRIMARY KEY')
                else:
                    col_defs.append(f'"{col}" {sql_type}')

            create_sql = f'CREATE TABLE IF NOT EXISTS "{table_name}" ({", ".join(col_defs)})'
            cursor.execute(create_sql)
            existing_cols = columns
        else:
            # Table already exists; check if we need to add any missing columns
            existing_set = set(existing_cols)
            for col in columns:
                if col not in existing_set:
                    sample_vals = [r.get(col) for r in records[:100]]
                    sql_type = self.infer_sql_type(sample_vals)
                    cursor.execute(f'ALTER TABLE "{table_name}" ADD COLUMN "{col}" {sql_type}')
                    existing_cols.append(col)

        return existing_cols

    def upsert_records(
        self,
        conn: sqlite3.Connection,
        table_name: str,
        records: List[Dict[str, Any]],
        primary_key: str,
    ) -> int:
        """
        Upserts (INSERT OR REPLACE) a list of dictionaries into a table.
        Returns the number of rows upserted.
        """
        if not records:
            return 0

        target_columns = self.ensure_table_schema(conn, table_name, records, primary_key)

        quoted_cols = ", ".join([f'"{c}"' for c in target_columns])
        placeholders = ", ".join(["?"] * len(target_columns))
        sql = f'INSERT OR REPLACE INTO "{table_name}" ({quoted_cols}) VALUES ({placeholders})'

        # Prepare rows
        rows_to_insert = []
        for r in records:
            row = []
            for col in target_columns:
                val = r.get(col)
                if isinstance(val, (datetime.date, datetime.datetime)):
                    val = str(val)
                row.append(val)
            rows_to_insert.append(row)

        cursor = conn.cursor()
        cursor.executemany(sql, rows_to_insert)
        return len(rows_to_insert)

    def get_latest_metric_date(self) -> Optional[datetime.date]:
        """
        Queries the latest recorded date from the 'metrics' table.
        Returns datetime.date or None if no valid dates exist.
        """
        if not self.table_exists("metrics"):
            return None

        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT MAX("Date") FROM "metrics" WHERE "Date" IS NOT NULL AND "Date" != ""')
            row = cursor.fetchone()
            if row and row[0]:
                try:
                    return datetime.datetime.strptime(str(row[0]).strip(), "%Y-%m-%d").date()
                except ValueError:
                    return None
        return None

    def get_latest_activity_timestamp(self) -> Optional[datetime.datetime]:
        """
        Queries the latest Start Time from the 'activities' table.
        Returns datetime.datetime or None.
        """
        if not self.table_exists("activities"):
            return None

        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT MAX("Start Time") FROM "activities" WHERE "Start Time" IS NOT NULL')
            row = cursor.fetchone()
            if row and row[0]:
                try:
                    return datetime.datetime.strptime(str(row[0]).strip(), "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    return None
        return None

    def get_table_counts(self) -> Dict[str, int]:
        """Returns row counts for the 3 tables."""
        counts = {}
        for tbl in ["activities", "metrics", "all_data"]:
            if self.table_exists(tbl):
                with self.connect() as conn:
                    cursor = conn.cursor()
                    cursor.execute(f'SELECT COUNT(*) FROM "{tbl}"')
                    counts[tbl] = cursor.fetchone()[0]
            else:
                counts[tbl] = 0
        return counts

    def export_all(
        self,
        activities: List[Dict[str, Any]],
        metrics: List[Dict[str, Any]],
        all_data: List[Dict[str, Any]],
    ) -> Dict[str, int]:
        """
        Exports all 3 datasets into SQLite inside a single atomic transaction.
        """
        results = {}
        with self.connect() as conn:
            with conn:  # Context manager automatically handles COMMIT / ROLLBACK
                results["activities"] = self.upsert_records(
                    conn=conn,
                    table_name="activities",
                    records=activities,
                    primary_key="activityId",
                )
                results["metrics"] = self.upsert_records(
                    conn=conn,
                    table_name="metrics",
                    records=metrics,
                    primary_key="Date",
                )
                results["all_data"] = self.upsert_records(
                    conn=conn,
                    table_name="all_data",
                    records=all_data,
                    primary_key="Date",
                )
        return results
