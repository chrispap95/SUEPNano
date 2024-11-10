#!/bin/bash

total=$(ls -d crab_NANO_UL18/* | wc -l)
current=0
for dir in crab_NANO_UL18/*; do
    ((current++))
    echo "[${current}/${total}] Resubmitting ${dir}"
    crab resubmit -d ${dir} --maxmemory 4000 --maxjobruntime 500
    echo "----------------------------------------"
done
echo "Completed resubmission of ${total} tasks"
