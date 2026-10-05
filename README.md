# Garmin Data Exporter

Garmin gives you a lot of data, but the useful insights are often hidden across different metrics and time periods. This app lets you download health and activity data from your Garmin device and save it into a CSV file enabling a consolidated data analysis via LLMs.

[![MIT License](https://img.shields.io/badge/License-MIT-green.svg)](https://choosealicense.com/licenses/mit/)

<img width="4167" height="1766" alt="dfd" src="https://github.com/user-attachments/assets/a8872c6e-e7a6-4954-b23a-d0e5590c2bd1" />

## Features
- **Garmin Connect Integration**: Connects to your Garmin account using session caching.
- **Deep Health Metrics**: Daily steps, calories, Body Battery, resting HR, stress levels, sleep stages (Deep, REM, Light), and overnight HRV baselines.
- **Activity Tracking**: Detailed activity metrics, zone times, training load, and automatic time-of-day categorization (Morning, Afternoon, Evening, Night).
- **Fast Concurrent Fetching**: Multi-threaded querying fetches months of daily data in seconds.
- **Interactive Menu & CLI**: Run without arguments for an interactive menu, or use command-line flags.
- **Clean Export**: Saves structured data cleanly into `output/` with support for CSV and SQLite formats.
- **SQLite Database Support**: Export all 3 datasets (`activities`, `metrics`, `all_data`) to SQLite with primary keys, and perform incremental updates with automatic delta detection.

## Requirements
- Python 3.8+
- ~~Garmin authentication via [`garth`](https://pypi.org/project/garth/)~~ *(deprecated – see notice above)*

## Usage

> **Note:** The steps below will only work if you already have a valid saved `garth` session. New logins are blocked.

#### 1. Clone this repository

```bash
git clone https://github.com/jangid-ankit/garmin-csv.git
cd garmin-to-csv
``` 

#### 2. Create and activate a virtual environment

```bash
python -m venv venv
source venv/bin/activate        # macOS / Linux
# venv\Scripts\activate         # Windows
```

#### 3. Install dependencies

```bash
pip install -r requirements.txt
```

#### 4. Run the exporter

**Interactive Mode:**
Simply run without arguments to get an interactive menu:
```bash
python main.py
```
Options include:
- `1` to `5`: Export or append CSV data (All data, Activities, or Health metrics).
- `6`: **Export all data to SQLite database** (`activities`, `metrics`, and `all_data` tables).
- `7`: **Update existing SQLite database** (detects latest recorded date, fetches only missing delta, and upserts).

**CLI Flags:**
```bash
# Export all daily metrics merged with primary activities to CSV
python main.py --mode all

# Export activities only to CSV
python main.py --mode activities

# Export health metrics for the past 30 days to CSV
python main.py --mode metrics --days 30

# Incrementally append latest metrics to existing CSV
python main.py --mode metrics --append

# Export 3 tables to SQLite database (default: output/garmin_data.db)
python main.py --sqlite-export

# Check & incrementally update existing SQLite database
python main.py --sqlite-update

# Custom SQLite database path
python main.py --sqlite-update --db-path my_database.db

# Custom date range and output file
python main.py --mode metrics --start-date 2025-01-01 --end-date 2025-06-30 --output my_data.csv
```

The exported CSV or SQLite database can be queried directly with SQL, fed into an LLM, or used in analysis dashboards.

<br>

## Insights from my data

<img width="1904" height="826" alt="garmin_insights (1)" src="https://github.com/user-attachments/assets/bcccee3b-6b0b-43be-b2ce-461d720e5624" />
