import concurrent.futures
import datetime
from typing import Any, Callable, Dict, List, Optional

import garth
from tqdm import tqdm

from garmin.transformers import transform_daily_metrics

class GarminClient:
    """Handles direct communication with Garmin Connect APIs."""

    def __init__(self):
        self.device_name: str = "Unknown Device"
        self.registered_date: datetime.date = datetime.date.today() - datetime.timedelta(days=365)
        self.display_name: str = ""

    def connect_device(self) -> None:
        """Fetch primary training device metadata and profile information."""
        try:
            user_profile = garth.UserProfile.get()
            self.display_name = getattr(user_profile, "display_name", "") or ""
        except Exception:
            self.display_name = garth.client.username or ""

        url = "/web-gateway/device-info/primary-training-device"
        try:
            device_data = garth.connectapi(url)
            reg_devices = device_data.get("RegisteredDevices", [])
            if reg_devices:
                reg = reg_devices[0]
                self.device_name = reg.get("displayName", "Garmin Device")
                reg_date_ts = reg.get("registeredDate")
                if reg_date_ts:
                    self.registered_date = datetime.datetime.fromtimestamp(reg_date_ts / 1000).date()
            print(f"Connected to device: {self.device_name} (Registered: {self.registered_date})")
        except Exception as e:
            print(f"Notice: Could not query primary training device ({e}). Using default profile settings.")

    def fetch_raw_activities(self, start: int = 0, limit: int = 999) -> List[Dict[str, Any]]:
        """Fetch raw activity records from Garmin Connect."""
        url = "/activitylist-service/activities/search/activities"
        params = {"start": str(start), "limit": str(limit)}
        try:
            print(f"Fetching activities (limit: {limit})...")
            data = garth.connectapi(url, params=params)
            return data if isinstance(data, list) else []
        except Exception as e:
            print(f"Error fetching activities: {e}")
            return []

    def _fetch_single_day(self, target_date: datetime.date) -> Optional[Dict[str, Any]]:
        """Fetch daily summary, sleep, and HRV for one date and transform into a clean record."""
        display = self.display_name or garth.client.username
        summary_url = f"/usersummary-service/usersummary/daily/{display}"
        sleep_url = f"/wellness-service/wellness/dailySleepData/{display}"
        hrv_url = f"/hrv-service/hrv/{target_date}"

        try:
            daily_summary = garth.connectapi(summary_url, params={"calendarDate": str(target_date)})
        except Exception:
            daily_summary = None

        try:
            sleep = garth.connectapi(sleep_url, params={"date": str(target_date), "nonSleepBufferMinutes": 60})
        except Exception:
            sleep = None

        try:
            hrv = garth.connectapi(hrv_url)
        except Exception:
            hrv = None

        return transform_daily_metrics(target_date, daily_summary, sleep, hrv)

    def fetch_metrics_range(
        self,
        start_date: datetime.date,
        end_date: datetime.date,
        max_workers: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Fetch metrics across a date range concurrently using ThreadPoolExecutor.
        Displays an in-place progress bar (tqdm) and returns sorted daily metrics.
        """
        if start_date > end_date:
            print(f"Start date {start_date} is after end date {end_date}.")
            return []

        days_count = (end_date - start_date).days + 1
        date_list = [start_date + datetime.timedelta(days=i) for i in range(days_count)]

        print(f"Fetching {days_count} days of metrics ({start_date} to {end_date}) using {max_workers} threads...")

        results: Dict[datetime.date, Dict[str, Any]] = {}

        with tqdm(total=days_count, desc="Fetching metrics", unit="day", dynamic_ncols=True) as pbar:
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_date = {executor.submit(self._fetch_single_day, d): d for d in date_list}
                for future in concurrent.futures.as_completed(future_to_date):
                    d = future_to_date[future]
                    try:
                        record = future.result()
                        if record:
                            results[d] = record
                    except Exception as e:
                        tqdm.write(f"Warning: Failed fetching data for {d}: {e}")
                    pbar.update(1)

        # Return in ascending chronological order
        return [results[d] for d in date_list if d in results]

