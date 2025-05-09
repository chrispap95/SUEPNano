#!/bin/bash
# This script moves the merged files from the split directories to a new directory in the merged directory.
# Usage: ./mv_files.sh
base_dir="/store/group/lpcsuep/Muon_counting_search/SUEPNano_2023BPix_Apr2025"
for primary_dataset in $(eosls ${base_dir} | grep GluGluToSUEP.*split); do
    eosmkdir ${base_dir}_merged/${primary_dataset}
    for scan_point in $(eosls ${base_dir}/${primary_dataset}); do
        suep_model=${primary_dataset}/${scan_point}
        eosmkdir ${base_dir}_merged/${suep_model}
        files_in=$(eosls ${base_dir}/${suep_model} | grep merged)
        for file_in in ${files_in}; do
            eosmv ${base_dir}/${suep_model}/${file_in} ${base_dir}_merged/${suep_model}/${file_in}; 
        done
    done
done
