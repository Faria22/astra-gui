#!/bin/bash
startTime=$(date +%s)

# Run Commands
###(commands)

endTime=$(date +%s)
elapsed=$((endTime - startTime))

hours=$((elapsed / 3600))
minutes=$(((elapsed % 3600) / 60))
###(notification)

touch .completed
