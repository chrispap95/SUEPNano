#!/bin/bash

total=$(ls -d crab_NANO_UL16APV/* | wc -l)
current=0
for dir in crab_NANO_UL16APV/*; do
    ((current++))
    echo "[${current}/${total}] killing ${dir}"
    crab kill -d ${dir}
    echo "----------------------------------------"
done
echo "Finished killing ${total} tasks"
