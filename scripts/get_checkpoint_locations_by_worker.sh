#!/bin/bash

# Meant to be run in the instance/VM where the script was logging/running when it terminated

# Find all files matching the pattern and loop through them
find /tmp/ray/session_latest/logs -type f -name "worker-*.err" -size +0 | while read -r file; do
  # Get the 11th line from the end of the file
  tail -n 11 "$file" | head -n 1
done