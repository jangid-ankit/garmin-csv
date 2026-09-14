import datetime
from collections import OrderedDict
from datetime import time
from typing import Any, Dict, List, Optional

def safe_get(data: Any, *keys: str, default: Any = None) -> Any:
    """Traverse nested dictionaries safely."""
    for key in keys:
        if not isinstance(data, dict):
            return default
        data = data.get(key, default)
    return data

def categorize_activity_time(activity_time: time) -> str:
    """Categorize time of day into Morning, Afternoon, Evening, or Night."""
    if time(4, 30) < activity_time <= time(10, 30):
        return "Morning"
    elif time(10, 30) < activity_time <= time(16, 30):
        return "Afternoon"
    elif time(16, 30) < activity_time <= time(19, 30):
        return "Evening"
    return "Night"

def transform_activity(activity: Dict[str, Any]) -> Dict[str, Any]:
    """Transform a single raw Garmin activity record into a clean dictionary."""
    start_time_str = activity.get("startTimeLocal", "")
    activity_when = ""
    if start_time_str:
        try:
            parsed_time = datetime.datetime.strptime(start_time_str, "%Y-%m-%d %H:%M:%S").time()
            activity_when = categorize_activity_time(parsed_time)
        except ValueError:
            pass

    activity_type = activity.get("activityType")
    type_key = activity_type.get("typeKey") if isinstance(activity_type, dict) else ""

    duration = activity.get("duration")
    elapsed_duration = activity.get("elapsedDuration")

    return {
        "activityId": activity.get("activityId"),
        "Name": activity.get("activityName"),
        "Start Time": start_time_str,
        "Activity When": activity_when,
        "Type": type_key,
        "Distance": activity.get("distance"),
        "Duration": round(duration) if duration is not None else None,
        "Elapsed Duration": round(elapsed_duration) if elapsed_duration is not None else None,
        "Moving Duration": activity.get("movingDuration"),
        "Average Speed": activity.get("averageSpeed"),
        "Mean Cadence": activity.get("averageRunningCadenceInStepsPerMinute", 0),
        "Calories": activity.get("calories"),
        "Mean HR": activity.get("averageHR"),
        "Max HR": activity.get("maxHR"),
        "Steps": activity.get("steps"),
        "Aerobic TE": activity.get("aerobicTrainingEffect"),
        "Anaerobic TE": activity.get("anaerobicTrainingEffect"),
        "Water Loss": activity.get("waterEstimated"),
        "Training Load": activity.get("activityTrainingLoad"),
        "Zone 1 Time": activity.get("hrTimeInZone_1"),
        "Zone 2 Time": activity.get("hrTimeInZone_2"),
        "Zone 3 Time": activity.get("hrTimeInZone_3"),
        "Zone 4 Time": activity.get("hrTimeInZone_4"),
        "Zone 5 Time": activity.get("hrTimeInZone_5"),
    }

def transform_activities(detailed_activities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Transform and sort all raw Garmin activities by Start Time ascending."""
    if not detailed_activities:
        return []

    activities = [transform_activity(act) for act in detailed_activities]

    # Sort ONCE after transforming, avoiding O(N^2 log N) performance degradation
    def parse_sort_key(item: Dict[str, Any]):
        val = item.get("Start Time")
        if val:
            try:
                return datetime.datetime.strptime(val, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                pass
        return datetime.datetime.min

    activities.sort(key=parse_sort_key)
    return activities

def transform_daily_metrics(
    date_val: datetime.date,
    daily_summary: Optional[Dict[str, Any]],
    sleep: Optional[Dict[str, Any]],
    hrv: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """Transform raw daily summary, sleep, and HRV payloads into a clean metric record."""
    daily_summary = daily_summary or {}
    sleep = sleep or {}
    hrv = hrv or {}

    return {
        "Date": str(date_val),
        "Steps": daily_summary.get("totalSteps"),
        "Calories": daily_summary.get("totalKilocalories"),
        "Body Battery": daily_summary.get("bodyBatteryHighestValue"),
        "Sleep Duration": daily_summary.get("sleepingSeconds"),
        "Sleep Score": safe_get(sleep, "dailySleepDTO", "sleepScores", "overall", "value"),
        "Sleep HRV": sleep.get("avgOvernightHrv"),
        "Sleep Deep": safe_get(sleep, "dailySleepDTO", "deepSleepSeconds"),
        "Sleep REM": safe_get(sleep, "dailySleepDTO", "remSleepSeconds"),
        "Sleep Light": safe_get(sleep, "dailySleepDTO", "lightSleepSeconds"),
        "Sleep Stress": safe_get(sleep, "dailySleepDTO", "avgSleepStress"),
        "RHR": sleep.get("restingHeartRate"),
        "Weekly avg. HRV": safe_get(hrv, "hrvSummary", "weeklyAvg"),
        "HRV Baseline Low": safe_get(hrv, "hrvSummary", "baseline", "balancedLow"),
        "HRV Baseline High": safe_get(hrv, "hrvSummary", "baseline", "balancedUpper"),
        "HRV Status": safe_get(hrv, "hrvSummary", "status"),
        "Moderate Intensity Minutes": daily_summary.get("moderateIntensityMinutes"),
        "Vigorous Intensity Minutes": daily_summary.get("vigorousIntensityMinutes"),
        "Stress": daily_summary.get("averageStressLevel"),
        "Resting Stress": daily_summary.get("restStressDuration"),
        "Low Stress": daily_summary.get("lowStressDuration"),
        "Med Stress": daily_summary.get("mediumStressDuration"),
        "High Stress": daily_summary.get("highStressDuration"),
        "Stress Status": daily_summary.get("stressQualifier"),
    }

def deduplicate_activities_by_day(activities: List[Dict[str, Any]]) -> Dict[datetime.date, Dict[str, Any]]:
    """
    Filters activities down to one primary activity per day based on highest calories.
    Returns a dictionary mapping date -> activity record.
    """
    filtered: Dict[datetime.date, Dict[str, Any]] = {}
    for activity in activities:
        start_time_str = activity.get("Start Time")
        if not start_time_str:
            continue
        try:
            current_date = datetime.datetime.strptime(start_time_str, "%Y-%m-%d %H:%M:%S").date()
        except ValueError:
            continue

        cal = activity.get("Calories") or 0
        existing = filtered.get(current_date)
        if existing is None or cal > (existing.get("Calories") or 0):
            filtered[current_date] = activity

    return filtered

def merge_metrics_and_activities(
    daily_metrics: List[Dict[str, Any]],
    activities: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Merge daily health metrics with daily primary activities matching on Date."""
    if not daily_metrics:
        return []

    activity_by_date = deduplicate_activities_by_day(activities)

    merged_data: List[Dict[str, Any]] = []
    all_fieldnames: OrderedDict = OrderedDict()

    for d in daily_metrics:
        raw_date = d.get("Date")
        if isinstance(raw_date, str):
            try:
                date_obj = datetime.datetime.strptime(raw_date, "%Y-%m-%d").date()
            except ValueError:
                date_obj = None
        else:
            date_obj = raw_date

        merged = OrderedDict(d)
        for k in d.keys():
            all_fieldnames[k] = None

        if date_obj and date_obj in activity_by_date:
            act = activity_by_date[date_obj]
            for k, v in act.items():
                if k not in merged:
                    merged[k] = v
                all_fieldnames[k] = None

        merged_data.append(merged)

    # Ensure all rows have all discovered field names for CSV consistency
    fields_list = list(all_fieldnames.keys())
    for row in merged_data:
        for fn in fields_list:
            row.setdefault(fn, "")

    return merged_data
