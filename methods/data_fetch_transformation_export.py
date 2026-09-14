"""
Backward compatibility module for data_fetch_transformation_export.
Delegates to modular implementations in the garmin package.
"""
import datetime
from types import SimpleNamespace
from typing import Any, List, Optional

from garmin.client import GarminClient
from garmin.exporters import CSVExporter as NewCSVExporter, get_last_recorded_date
from garmin.transformers import (
    safe_get,
    transform_activities,
    merge_metrics_and_activities,
)

class GarminDataFetcher:
    """Compatibility wrapper preserving the legacy GarminDataFetcher interface."""

    def __init__(self):
        self._client = GarminClient()
        self.device = SimpleNamespace(
            device_name=self._client.device_name,
            registered_date=self._client.registered_date,
            display_name=self._client.display_name,
        )
        self.data: List[dict] = []
        self.rows_list: List[Any] = []
        self.today = datetime.date.today()

    def connect_device(self):
        self._client.connect_device()
        self.device.device_name = self._client.device_name
        self.device.registered_date = self._client.registered_date
        self.device.display_name = self._client.display_name

    def activity_metrics(self, file_name: str = "only_activities.csv"):
        raw = self._client.fetch_raw_activities()
        activities = transform_activities(raw)
        exporter = NewCSVExporter(file_name)
        exporter.export(activities)
        return activities

    def fetch_metrics(self, append_existing: bool = False, filename: str = "only_metrics.csv"):
        start_date = self.device.registered_date
        if append_existing:
            last_date = get_last_recorded_date(filename)
            if last_date:
                start_date = last_date + datetime.timedelta(days=1)

        self.data = self._client.fetch_metrics_range(start_date, self.today)
        exporter = NewCSVExporter(filename)
        exporter.export(self.data, append=append_existing)
        return self.data

    def all_data(self, file_name: str = "all_metrics.csv"):
        # Fetch metrics without saving to side files prematurely
        start_date = self.device.registered_date
        daily_metrics = self._client.fetch_metrics_range(start_date, self.today)
        raw_activities = self._client.fetch_raw_activities()
        activities = transform_activities(raw_activities)

        merged = merge_metrics_and_activities(daily_metrics, activities)
        exporter = NewCSVExporter(file_name)
        exporter.export(merged)
        return merged

    def existing_metrics(self, filename: str):
        last_date = get_last_recorded_date(filename)
        if last_date:
            return last_date, []
        return self.device.registered_date, []

    def _safe_get(self, data, *keys, default=None):
        return safe_get(data, *keys, default=default)


class CSVExporter:
    """Compatibility wrapper preserving the legacy CSVExporter interface."""

    def __init__(self, filename: str):
        self._exporter = NewCSVExporter(filename)
        self.filename = filename

    def export(self, data: List[dict], rows_list: Optional[List[Any]] = None):
        append = bool(rows_list)
        return self._exporter.export(data, append=append)