#!/usr/bin/env python2
from __future__ import division, print_function
from CRABAPI.RawCommand import crabCommand
import argparse
import json
import glob
import time
import os
import sys
from datetime import datetime
import logging
from contextlib import contextmanager


def get_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="CRAB Job Monitor")
    parser.add_argument(
        "-d",
        "--datasets",
        required=True,
        help="JSON file with list of datasets to monitor",
    )
    parser.add_argument(
        "--refresh",
        type=int,
        default=900,
        help="Refresh rate in seconds (default: 900)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output CSV file name (default: [datasets filename].csv)",
    )
    return parser.parse_args()


def get_primary_name(dataset):
    """Extract primary dataset name from full dataset path"""
    # Split by '/' and take the first part (index 1, as dataset starts with '/')
    return dataset.split("/")[1]


def find_latest_task_dir(crab_base_dir, primary_name):
    """Find the most recent task directory for a given primary dataset name"""
    # List all directories that match the pattern
    pattern = os.path.join(crab_base_dir, "crab_" + primary_name + "*")
    matching_dirs = glob.glob(pattern)

    if not matching_dirs:
        return None

    # Sort by modification time (most recent last)
    latest_dir = max(matching_dirs, key=os.path.getmtime)
    return latest_dir


def get_task_directories(json_file, crab_base_dir="crab_NANO_UL18"):
    """
    Parse JSON file containing datasets and find corresponding task directories

    Args:
        json_file (str): Path to JSON file containing dataset list
        crab_base_dir (str): Base directory containing CRAB task directories

    Returns:
        list: List of task directories
        dict: Mapping of task directories to dataset names for reference
    """
    if not os.path.exists(json_file):
        raise ValueError("JSON file not found: " + json_file)

    if not os.path.exists(crab_base_dir):
        raise ValueError("CRAB base directory not found: " + crab_base_dir)

    # Read and parse JSON file
    with open(json_file, "r") as f:
        datasets = json.load(f)

    task_dirs = []
    task_to_dataset = {}
    missing_tasks = []

    print("Finding task directories for {} datasets...".format(len(datasets)))
    sys.stdout.flush()

    for dataset in datasets:
        primary_name = get_primary_name(dataset)
        task_dir = find_latest_task_dir(crab_base_dir, primary_name)

        if task_dir:
            task_dirs.append(task_dir)
            task_to_dataset[task_dir] = dataset
        else:
            missing_tasks.append(dataset)

    if missing_tasks:
        print(
            "\nWarning: Could not find task directories for {} datasets:".format(
                len(missing_tasks)
            )
        )
        for dataset in missing_tasks:
            print("  - {}".format(dataset))

    print("\nFound {} task directories".format(len(task_dirs)))
    return task_dirs, task_to_dataset


@contextmanager
def suppress_crab_output():
    """Temporarily redirect stdout and stderr"""
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    with open(os.devnull, "w") as devnull:
        sys.stdout = devnull
        sys.stderr = devnull
        try:
            yield
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr


class CRABMonitor(object):
    def __init__(
        self,
        task_directories,
        task_to_dataset=None,
        refresh_rate=300,
        output_file="crab_monitor_status.csv",
    ):
        self.task_dirs = task_directories
        self.task_to_dataset = task_to_dataset or {}
        self.refresh_rate = refresh_rate
        self.output_file = output_file
        self.status_history = {}
        logging.getLogger("CRAB3").setLevel(logging.ERROR)

        # Initialize CSV file with headers
        self._initialize_csv()

    def format_table(self, headers, rows):
        """Create ASCII table for status display"""
        widths = [
            max(len(str(row[i])) for row in rows + [headers])
            for i in range(len(headers))
        ]
        row_format = (
            "| " + " | ".join("{:<" + str(width) + "}" for width in widths) + " |"
        )
        separator = "+" + "+".join("-" * (width + 2) for width in widths) + "+"

        table = []
        table.append(separator)
        table.append(row_format.format(*headers))
        table.append(separator)
        for row in rows:
            table.append(row_format.format(*[str(item) for item in row]))
        table.append(separator)

        return "\n".join(table)

    def _initialize_csv(self):
        """Initialize CSV file with headers"""
        import csv

        fieldnames = [
            "status",
            "timestamp",
            "idle",
            "finished",
            "dataset",
            "running",
            "total",
            "completion",
            "transferred",
            "failed",
            "transferring",
            "task_name",
        ]

        with open(self.output_file, "wb") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

    def _append_to_csv(self, status_entry):
        """Append a single status entry to the CSV file"""
        import csv

        with open(self.output_file, "ab") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=status_entry.keys())
            writer.writerow(status_entry)

    def get_task_status(self, task_dir):
        """Get status for a single CRAB task"""
        try:
            with suppress_crab_output():
                res = crabCommand("status", dir=task_dir)

            jobs_per_status = res.get("jobsPerStatus", {})
            total_jobs = (
                sum(jobs_per_status.values())
                if jobs_per_status
                else res.get("totalJobs", 0)
            )

            status_dict = {
                "status": res.get("status", "unknown"),
                "total": total_jobs,
                "running": jobs_per_status.get("running", 0),
                "finished": jobs_per_status.get("finished", 0),
                "failed": jobs_per_status.get("failed", 0),
                "transferring": jobs_per_status.get("transferring", 0),
                "idle": jobs_per_status.get("idle", 0),
                "transferred": jobs_per_status.get("transferred", 0),
            }

            completed_jobs = status_dict["finished"] + status_dict["transferred"]
            status_dict["completion"] = (
                completed_jobs / float(status_dict["total"]) * 100
                if status_dict["total"] > 0
                else 0
            )

            return status_dict
        except Exception as e:
            print("Error getting status for {0}: {1}".format(task_dir, str(e)))
            sys.stdout.flush()
            return None

    def monitor(self):
        """Main monitoring loop"""
        try:
            while True:
                os.system("clear" if os.name == "posix" else "cls")
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                print("CRAB Job Monitor - Last Updated: {0}".format(current_time))
                print("-" * 80)

                status_data = []
                total_jobs = 0
                completed_jobs = 0

                total_tasks = len(self.task_dirs)
                tasks_retrieved = 0
                print("\nRetrieving task statuses...")
                sys.stdout.flush()

                headers = [
                    "Task",
                    "Status",
                    "Progress",
                    "Running",
                    "Completed",
                    "Failed",
                    "Idle",
                    "Total",
                ]

                for task_dir in self.task_dirs:
                    status = self.get_task_status(task_dir)
                    tasks_retrieved += 1
                    sys.stdout.write(
                        "\rRetrieved {0} / {1} tasks".format(
                            tasks_retrieved, total_tasks
                        )
                    )
                    sys.stdout.flush()

                    if status:
                        task_name = os.path.basename(task_dir)
                        dataset = self.task_to_dataset.get(task_dir, "")
                        task_completed = status["finished"] + status["transferred"]

                        # Create status entry for CSV
                        status_entry = {
                            "timestamp": current_time,
                            "task_name": task_name,
                            "dataset": dataset,
                            "status": status["status"],
                            "completion": status["completion"],
                            "total": status["total"],
                            "running": status["running"],
                            "finished": status["finished"],
                            "transferred": status["transferred"],
                            "failed": status["failed"],
                            "idle": status["idle"],
                            "transferring": status["transferring"],
                        }

                        # Append to CSV file immediately
                        self._append_to_csv(status_entry)

                        # Create row data in same order as headers
                        row_data = [
                            task_name,  # Task
                            status["status"],  # Status
                            "{0:.1f}%".format(status["completion"]),  # Progress
                            status["running"],  # Running
                            task_completed,  # Completed
                            status["failed"],  # Failed
                            status["idle"],  # Idle
                            status["total"],  # Total
                        ]
                        status_data.append(row_data)

                        total_jobs += status["total"]
                        completed_jobs += task_completed

                print("\n\nCurrent Status:\n")

                if status_data:
                    print(self.format_table(headers, status_data))

                    overall_progress = (
                        (completed_jobs / float(total_jobs) * 100)
                        if total_jobs > 0
                        else 0
                    )
                    print(
                        "\nOverall Progress: {0:.1f}% ({1}/{2} jobs completed)".format(
                            overall_progress, completed_jobs, total_jobs
                        )
                    )
                else:
                    print("No status data available for any tasks.")

                print("\nStatus data saved to: {}".format(self.output_file))
                print("\nNext update in {0} seconds...".format(self.refresh_rate))
                sys.stdout.flush()
                time.sleep(self.refresh_rate)

        except KeyboardInterrupt:
            print("\nMonitoring stopped by user")
            print("Final status data saved to: {}".format(self.output_file))


def main():
    args = get_args()

    # Need to convert dataset names to CRAB task directories
    task_dirs, task_to_dataset = get_task_directories(args.datasets)

    if not task_dirs:
        print("No task directories found. Exiting.")
        return

    output_file = args.output
    if not args.output:
        if not os.path.isdir("crab_monitor_history"):
            os.makedirs("crab_monitor_history")
        output_file = os.path.splitext(args.datasets)[0] + ".csv"
        output_file = os.path.basename(output_file)
        output_file = "crab_monitor_history/" + output_file

    monitor = CRABMonitor(
        task_dirs, task_to_dataset, refresh_rate=args.refresh, output_file=output_file
    )
    monitor.monitor()


if __name__ == "__main__":
    main()
