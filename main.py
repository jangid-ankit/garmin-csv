import garth
from methods.auth import authenticate
from methods.data_fetch_transformation_export import GarminDataFetcher, CSVExporter
import csv
import os
import json

def main():
    ## Authenticate user
    authenticate()

    fetcher = GarminDataFetcher()
    fetcher.connect_device()

    ## SELECT ONLY ONE OF THE OPTIONS BELOW:

    ## 1. FETCH ALL
    fetcher.all_data("metrics_activities.csv")

    # ## 2. FETCH ACTIVITIES ONLY
    # fetcher.activity_metrics("only_activities.csv")

    # ## 3. FETCH METRICS ONLY (with option to append existing CSV data)
    # append_existing = input("Append existing CSV data? (y/n): ").strip().lower() == "y"
    # fetcher.fetch_metrics(append_existing=append_existing)


if __name__ == "__main__":
    main()





