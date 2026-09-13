# Garmin Data Exporter

Garmin gives you a lot of data, but the useful insights are often hidden across different metrics and time periods. This app lets you download health and activity data from your Garmin device and save it into a CSV file enabling a consolidated data analysis via LLMs.

[![MIT License](https://img.shields.io/badge/License-MIT-green.svg)](https://choosealicense.com/licenses/mit/)

> **⚠️ Important Notice (March 2026)**  
> Garmin changed their authentication system and added Cloudflare TLS fingerprinting.  
> The library this project depends on — [`garth`](https://github.com/matin/garth) — is now **officially deprecated** and no longer works for new logins.  
>  
> **This project currently does not work** for fresh authentication.  
>  
> For a working alternative that bypasses the TLS fingerprinting restriction, see:  
> → [**etweisberg/garmin-connect-mcp**](https://github.com/etweisberg/garmin-connect-mcp)  
> (routes API calls through a headless Playwright browser)

<img width="4167" height="1766" alt="dfd" src="https://github.com/user-attachments/assets/a8872c6e-e7a6-4954-b23a-d0e5590c2bd1" />

## Features
- Connects to your Garmin account.
- Fetches daily metrics including steps, calories, sleep, HRV, stress, and more.
- Exports the data into a CSV file (`garmin_data.csv`).
- Option to append new metrics to an existing file or start fresh.

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

```bash
python main.py
```

The exported CSV can be fed directly into an LLM for descriptive analysis and insight generation.

<br>

## Insights from my data

<img width="1904" height="826" alt="garmin_insights (1)" src="https://github.com/user-attachments/assets/bcccee3b-6b0b-43be-b2ce-461d720e5624" />
