#!/bin/zsh
if (($#>0)) then
    let "step = 100 / $#"
    ((counter=0))
    for f in "$@"
    do
        export filename="$(basename "${f}")"
        echo "Processing $filename"
        if [[ $f == *"_p.psarc"* ]]; then
            export dir="$(dirname "${f}")"  
            mkdir -p "${dir}/convert" 
            ./convert "$f" "${dir}/convert"
        elif [[ $f == *"_m.psarc"* ]]; then
                export dir="$(dirname "${f}")"  
                mkdir -p "${dir}/convert" 
                cp "$f" "${dir}/convert/"
        fi
        ((counter=counter+step))
        echo "PROGRESS:$counter"
    done
    echo "All Done!"
fi