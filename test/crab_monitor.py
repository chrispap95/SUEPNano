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
    def __init__(self, task_directories, task_to_dataset=None, refresh_rate=300):
        self.task_dirs = task_directories
        self.task_to_dataset = task_to_dataset or {}
        self.refresh_rate = refresh_rate
        self.status_history = {}
        logging.getLogger("CRAB3").setLevel(logging.ERROR)

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
                        task_completed = status["finished"] + status["transferred"]

                        row_data = [
                            task_name,
                            status["status"],
                            "{0:.1f}%".format(status["completion"]),
                            status["running"],
                            task_completed,
                            status["failed"],
                            status["idle"],
                            status["total"],
                        ]
                        status_data.append(row_data)

                        total_jobs += status["total"]
                        completed_jobs += task_completed

                        if task_name not in self.status_history:
                            self.status_history[task_name] = []
                        self.status_history[task_name].append(
                            dict(
                                timestamp=current_time,
                                dataset=self.task_to_dataset.get(task_dir, ""),
                                **status
                            )
                        )

                print("\n\nCurrent Status:\n")

                if status_data:
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

                print("\nNext update in {0} seconds...".format(self.refresh_rate))
                sys.stdout.flush()
                time.sleep(self.refresh_rate)

        except KeyboardInterrupt:
            print("\nMonitoring stopped by user")
            self.save_history()

    def save_history(self):
        """Save monitoring history to CSV files"""
        if not os.path.exists("crab_monitor_history"):
            os.makedirs("crab_monitor_history")

        for task_name, history in self.status_history.items():
            filename = "crab_monitor_history/crab_monitor_{0}_{1}.csv".format(
                task_name, datetime.now().strftime("%Y%m%d_%H%M%S")
            )

            with open(filename, "wb") as csvfile:
                if history:
                    import csv

                    fieldnames = history[0].keys()
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(history)
                    print("Monitoring history saved to {0}".format(filename))


def main():
    args = get_args()

    # Need to convert dataset names to CRAB task directories
    task_dirs, task_to_dataset = get_task_directories(args.datasets)

    if not task_dirs:
        print("No task directories found. Exiting.")
        return

    monitor = CRABMonitor(task_dirs, task_to_dataset, refresh_rate=args.refresh)
    monitor.monitor()


if __name__ == "__main__":
    main()
