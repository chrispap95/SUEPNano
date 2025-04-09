#!/usr/bin/env python2
from __future__ import print_function, division
import pandas as pd  # type: ignore[import]
import json
import glob
import argparse
import sys


def get_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="List incomplete CRAB datasets")
    parser.add_argument(
        "-i",
        "--input",
        required=True,
        help="Input pattern for CSV files (e.g., 'crab_monitor_*.csv' or folder path)",
    )
    parser.add_argument(
        "-o",
        "--output",
        help="Output JSON file name (default: crab_monitor_history/[input filename]_incomplete.json)",
    )
    return parser.parse_args()


def main():
    args = get_args()

    try:
        # Load and combine all CSV files
        files = glob.glob(args.input)
        if not files:
            raise ValueError(
                "No CSV files found matching pattern: {}".format(args.input)
            )

        dfs = [pd.read_csv(f) for f in files]
        df = pd.concat(dfs, ignore_index=True)

        # Get the latest status for each dataset
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        latest_status = df.sort_values("timestamp").groupby("dataset").last()

        # Get list of incomplete datasets
        incomplete_datasets = [
            dataset
            for dataset, row in latest_status.iterrows()
            if dataset and row["failed"] > 0
        ]

        # Write to JSON file
        output_filename = args.output
        if output_filename is None:
            output_filename = args.input.replace("*", "").replace(".csv", "_incomplete.json")
        with open(output_filename, "w") as f:
            json.dump(incomplete_datasets, f, indent=2)

        print("Found {} incomplete datasets".format(len(incomplete_datasets)))
        print("Results saved to: {}".format(output_filename))

    except Exception as e:
        print("Error: {}".format(str(e)), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
