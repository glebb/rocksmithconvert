#!/bin/sh
export LC_NUMERIC="en_US.UTF-8"
if (($#>0)); then
    progress=0
    psarc_files_count=0
    for f in "$@"; do if [[ $f == *"_m.psarc"* ]] || [[ $f == *"_p.psarc"* ]]; then ((psarc_files_count+=1)); fi; done;
    if ((psarc_files_count > 0)); then
        user_choice=$(osascript -e 'button returned of (display dialog "What do you want to do?" buttons {"Convert", "Convert using short names", "Rename to short names"})')
        command=""
        case $user_choice in
            "Convert") 
                command="--convert";;
            "Convert using short names")
                command="--convertshort";;
            "Rename to short names")
                command="--rename";
        esac
        for f in "$@"
        do
            if [[ $f != *"_m.psarc"* ]] && [[ $f != *"_p.psarc"* ]]; then continue; fi;
            filename="$(basename "${f}")"
            echo "Processing $filename"
            output_dir="$(dirname "${f}")"
            if [[ $command == "--rename" ]]; then output_dir+="/renamed"; elif [[ $f == *"_m.psarc"* ]]; then output_dir+="/converted_for_pc"; else output_dir+="/converted_for_mac"; fi;
            mkdir -p "${output_dir}"
            ./convert "${f}" "${output_dir}" "${command}"
            progress="$(bc -l <<<"$progress+(100.0/$psarc_files_count)")"
            rounded_progress="$(printf '%.0f' $progress)"
            echo "PROGRESS:$rounded_progress"
        done
    fi
    echo "PROGRESS:100"
    echo "All Done!"
fi