# Garmin Data Exporter

This app lets you download health and activity data from your Garmin device and save it into a CSV file.

[![MIT License](https://img.shields.io/badge/License-MIT-green.svg)](https://choosealicense.com/licenses/mit/)

<img width="4167" height="1766" alt="dfd" src="https://github.com/user-attachments/assets/a8872c6e-e7a6-4954-b23a-d0e5590c2bd1" />

## Features
- **Garmin Connect Integration**: Connects to your Garmin account using session caching.
- **Deep Health Metrics**: Daily steps, calories, Body Battery, resting HR, stress levels, sleep stages (Deep, REM, Light), and overnight HRV baselines.
- **Activity Tracking**: Detailed activity metrics, zone times, training load, and automatic time-of-day categorization (Morning, Afternoon, Evening, Night).
- **Fast Concurrent Fetching**: Multi-threaded querying fetches months of daily data in seconds.
- **Interactive Menu & CLI**: Run without arguments for an interactive menu, or use command-line flags.
- **Clean Export**: Saves structured data cleanly into `output/` with support for incremental appending.

## Requirements
- Python 3.8+
- ~~Garmin authentication via [`garth`](https://pypi.org/project/garth/)~~ *(deprecated – see notice above)*

## Usage

> **Note:** The steps below will only work if you already have a valid saved `garth` session. New logins are blocked.

#### 1. Clone this repository

```bash
git clone https://github.com/transientperpetual/garmin-to-csv.git
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

**CLI Flags:**
```bash
# Export all daily metrics merged with primary activities
python main.py --mode all

# Export activities only
python main.py --mode activities

# Export health metrics for the past 30 days
python main.py --mode metrics --days 30

# Incrementally append latest metrics to existing CSV
python main.py --mode metrics --append

# Custom date range and output file
python main.py --mode metrics --start-date 2025-01-01 --end-date 2025-06-30 --output my_data.csv
```

The exported CSV can be fed directly into an LLM or analysis script for descriptive analysis and insight generation.

<br>

## Insights from my data

Analysis of ~13 months of exported Garmin data (390 days, 138 activities) surfaced a few statistically solid patterns:

- **Training load, not activity type, drives next-day recovery.** Sessions above ~90 training load show a clear next-day cost across 6 independent metrics: sleep score (r=-0.30, p=0.003), Body Battery (r=-0.41, p<0.001), and RHR (r=+0.45, p<0.001) all move in the expected direction. Below that load, recovery is flat regardless of how often you train.

- **Evening training load matters more than morning.** High-load sessions after 5pm correlate with worse next-night sleep (r=-0.38, p=0.02); the same load in the morning shows no significant effect (r=-0.17, p=0.19). Clock time alone (morning vs. evening) has no effect,  it's intensity *combined with* timing.

- **Activity type mostly reflects load, not the sport itself.** Cricket and cycling show the worst next-day recovery, but that's because they're your highest-load activities (long matches/rides), not something specific to those sports. Running is the exception - moderate-high load but strong recovery, likely because it's almost always a morning session.

- **Evening table tennis is the one evening activity that doesn't cost sleep, it may even help.** Nearly all table tennis sessions happen 6-7:30pm, and next-day sleep score after those sessions (72.3) beats every other evening activity, including rest-adjacent ones like light strength work. All other evening activities combined average 64.8. Low physiological load plus a genuine mental "switch-off" is the likely explanation.


- **Sleep quantity is the strongest lever in the whole dataset.** 25% of nights are under 6 hours, and short sleep correlates with next-day stress more strongly than anything else tracked (r=-0.45).

