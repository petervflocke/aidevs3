#!/bin/bash

# Check if at least one argument is provided
if [ "$#" -lt 1 ]; then
    echo "Usage: $0 <file_pattern>"
    exit 1
fi

echo "Processing files: $@"

for file in "$@"; do
    echo "Processing file: $file"
    python S02E01.py --file "$file"
done
