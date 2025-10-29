#!/bin/bash
startTime=$(date +%s)

# Define the parent directory for input_file_templates
template_dir="$ASTRA_GUI_DIR/input_file_templates"

# Get the current .INP files in the current directory
currentInputs=($(ls *.INP 2>/dev/null))

# Get the input file templates from the template directory
neededInputs=($(ls "$template_dir"/*.INP 2>/dev/null | xargs -n 1 basename))

# Find the missing inputs
missingInputs=($(comm -23 <(printf "%s\n" "${neededInputs[@]}" | sort) <(printf "%s\n" "${currentInputs[@]}" | sort)))

# Copy missing files to the current directory
for f in "${missingInputs[@]}"; do
   cp "$template_dir/$f" ./
done

# Run astra
taskset -c ###(cpu) astraSetup -run ###(run_astra_command) &
sleep 0.1 # Makes sure the code runs before deleting the unnecessary input files

# Remove newly created input files
for f in "${missingInputs[@]}"; do
   rm "$f"
done

rm run_astra_setup.sh # Removes this file so the user is not bothered by it
wait $! #Waits for astraSetup to be over

endTime=$(date +%s)
elapsed=$((endTime - startTime))

hours=$((elapsed / 3600))
minutes=$(((elapsed % 3600) / 60))
###(notification)

touch .completed
