#!/bin/sh
export LC_NUMERIC="en_US.UTF-8"

function choose_function() {
    command="--convert"
    user_choice=$(osascript -e 'button returned of (display dialog "What do you want to do?" buttons {"Convert", "Convert using short names", "Rename to short names"})')
    case $user_choice in
        "Convert") 
            command="--convert";;
        "Convert using short names")
            command="--convertshort";;
        "Rename to short names")
            command="--rename";
    esac
    echo "$command"
}

function choose_folder() {
    user_choice=$(osascript -e 'button returned of (display dialog "Choose output folder?" buttons {"Yes", "User source folder"})')
    if [[ $user_choice == "Yes" ]]; then
        default_dlc="${HOME}/Library/Application Support/Steam/steamapps/common/Rocksmith2014/dlc"
        if [[ -d $default_dlc ]]; then default_dlc=" default location \"$default_dlc\""; else default_dlc="";fi;
        script="osascript -e 'set folderName to POSIX path of (choose folder $default_dlc)'"
        temp=$(eval $script)
        echo "$temp"
    fi
}


if (($#>0)); then
    progress=0
    psarc_files_count=0
    for f in "$@"; do if [[ $f == *"_m.psarc"* ]] || [[ $f == *"_p.psarc"* ]]; then ((psarc_files_count+=1)); fi; done;
    if ((psarc_files_count > 0)); then
        command=$(choose_function)
        selected_output_dir=$(choose_folder)
        for f in "$@"
        do
            if [[ $f != *"_m.psarc"* ]] && [[ $f != *"_p.psarc"* ]]; then continue; fi;
            if [[ $selected_output_dir == "" ]]; then 
                output_dir="$(dirname "${f}")"
                if [[ $command == "--rename" ]]; then 
                    output_dir+="/renamed"
                elif [[ $f == *"_m.psarc"* ]]; then 
                    output_dir+="/converted_for_pc" 
                else 
                    output_dir+="/converted_for_mac"
                fi
                mkdir -p "${output_dir}"
            else
                output_dir=$selected_output_dir
            fi            
            filename="$(basename "${f}")"
            echo "Processing $filename"
            ./convert "${f}" "${output_dir}" "${command}"
            progress="$(bc -l <<<"$progress+(100.0/$psarc_files_count)")"
            rounded_progress="$(printf '%.0f' $progress)"
            echo "PROGRESS:$rounded_progress"
        done
    fi
    echo "PROGRESS:100"
    echo "All Done!"
fi