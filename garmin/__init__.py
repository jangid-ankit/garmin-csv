from garmin.auth import authenticate, AuthenticationError
from garmin.client import GarminClient
from garmin.exporters import CSVExporter, get_last_recorded_date
from garmin.transformers import (
    transform_activity,
    transform_activities,
    transform_daily_metrics,
    deduplicate_activities_by_day,
    merge_metrics_and_activities,
)

__all__ = [
    "authenticate",
    "AuthenticationError",
    "GarminClient",
    "CSVExporter",
    "get_last_recorded_date",
    "transform_activity",
    "transform_activities",
    "transform_daily_metrics",
    "deduplicate_activities_by_day",
    "merge_metrics_and_activities",
]

