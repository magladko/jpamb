#!/usr/bin/env bash

for file in solutions/*.py; do
  filename=$(basename "$file" .py)
  echo "Handling ${file} to ${filename}..."
  uvx jpamb test python "$file" >"test/${filename}.txt"
done
