#!/bin/bash

# Customize this value: how much to increase memory (in MB)
MEMORY_INCREMENT=2000  # e.g., increase by 2 GB
VERBOSE=0 # Set to 1 for verbose output
DRY_RUN=0 # Set to 1 for dry run (no actual changes)

while getopts 'm:vd' flag; do
  case "${flag}" in
    m) MEMORY_INCREMENT="${OPTARG}" ;;
    v) VERBOSE=1 ;;
    d) DRY_RUN=1 ;;
    *) echo "Unexpected option ${flag}" ;;
  esac
done

# LPC schedulers 
schedulers=("lpcschedd4.fnal.gov" "lpcschedd5.fnal.gov" "lpcschedd6.fnal.gov")

# Loop through each scheduler
for scheduler in "${schedulers[@]}"; do
    echo "Processing scheduler: $scheduler"

    # Get list of held job IDs
    held_jobs=$(condor_q -hold -name $scheduler -autoformat ClusterId ProcId)

    if [ -z "$held_jobs" ]; then
        echo "No held jobs found."
        continue
    fi

    n_held_jobs=$(echo "$held_jobs" | wc -l)
    echo "Found ${n_held_jobs} held jobs."
    if [ $VERBOSE -eq 1 ]; then
        echo "Held jobs:"
        echo "$held_jobs"
    fi

    for job in $held_jobs; do
        # condor_q returns ClusterId and ProcId separately, we need to pair them
        if [ -z "$prev" ]; then
            prev=$job
            continue
        fi

        cluster=$prev
        proc=$job
        job_id="${cluster}.${proc}"

        # Get current request_memory
        current_mem=$(condor_q "$job_id" -name "$scheduler" -autoformat RequestMemory)

        # Fallback if memory is not defined
        if [ -z "$current_mem" ]; then
            current_mem=2000  # Default to 2GB if undefined
        fi

        # Calculate new memory
        new_mem=$((current_mem + MEMORY_INCREMENT))

        if [ $VERBOSE -eq 1 ]; then
            echo "Updating $job_id: Memory $current_mem MB -> $new_mem MB"
        fi

        # Update memory request
        if [ $DRY_RUN -eq 1 ]; then
            echo "[DRY RUN]: condor_qedit $job_id -name $scheduler RequestMemory $new_mem"
        else
            condor_qedit "$job_id" -name "$scheduler" RequestMemory "$new_mem"
        fi

        # Release job
        if [ $DRY_RUN -eq 1 ]; then
            echo "[DRY RUN]: condor_release $job_id -name $scheduler"
        else
            condor_release "$job_id" -name "$scheduler"
        fi

        # Reset temp var
        prev=""
    done
done

echo "Done processing held jobs."
