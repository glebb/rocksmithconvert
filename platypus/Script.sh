#!/bin/sh
export LC_NUMERIC="en_US.UTF-8"
if (($#>0)) 
then
    progress=0
    psarc_files=()
    for f in "$@"; do if [[ $f == *"_m.psarc"* ]] || [[ $f == *"_p.psarc"* ]]; then psarc_files+=("${f}"); fi; done;
    for f in "$@"
    do
        if [[ $f != *"_m.psarc"* ]] && [[ $f != *"_p.psarc"* ]]; then continue; fi;
        filename="$(basename "${f}")"
        echo "Processing $filename"
        convert_dir="$(dirname "${f}")/converted_for"
        if [[ $f == *"_m.psarc"* ]]; then convert_dir+="_pc"; else convert_dir+="_mac"; fi;
        mkdir -p "${convert_dir}"
        ./convert "$f" "${convert_dir}"
        progress="$(bc -l <<<"$progress+(100.0/${#psarc_files[@]})")"
        rounded_progress="$(printf '%.0f' $progress)"
        echo "PROGRESS:$rounded_progress"
    done
    echo "PROGRESS:100"
    echo "All Done!"
fi