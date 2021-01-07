#!/bin/zsh
if (($#>0)) then
    let "progress_step = 100 / $#"
    let "increment_step = $# / 100"
    ((progress_bar=0))
    ((counter=0))
    for f in "$@"
    do
        export filename="$(basename "${f}")"
        echo "Processing $filename"
        if [[ $f == *"_p.psarc"* ]]; then
            export dir="$(dirname "${f}")/converted_for_mac"
            mkdir -p $dir
            ./convert "$f" "${dir}"
        elif [[ $f == *"_m.psarc"* ]]; then
            export dir="$(dirname "${f}")/converted_for_pc"
            mkdir -p $dir
            ./convert "$f" "${dir}"
        fi
        if [[ $progress_step -eq 0 ]] then
            if [[ $counter -eq $increment_step ]] then
                ((progress_bar=progress_bar+1))
                ((counter=0))
            else
                ((counter=counter+1))
            fi
        else
            ((progress_bar=progress_bar+progress_step))
        fi
        echo "PROGRESS:$progress_bar"
    done
    echo "PROGRESS:100"
    echo "All Done!"
fi