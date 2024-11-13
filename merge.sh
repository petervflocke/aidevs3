#!/bin/bash


# Check if two arguments are provided
if [ "$#" -ne 2 ]; then
    echo "Usage: $0 <file_pattern> <output_file>"
    exit 1
fi

file_pattern="$1"
output_file="$2"

# Create an empty output file
> $output_file

# Loop through files matching the pattern and sort numerically
for file in $(ls $file_pattern | sort -t'-' -k3); do
    echo "File: $file" >> $output_file
    cat "$file" >> $output_file
    echo "" >> $output_file  # Add a blank line after each file
done