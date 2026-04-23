#!/bin/bash
# run_daily.sh — Wrapper script for cron/launchd scheduling
# Activates the virtual environment and runs the main pipeline.

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

cd "$SCRIPT_DIR"

# Activate venv
source "$SCRIPT_DIR/venv/bin/activate"

# Run the pipeline
python "$SCRIPT_DIR/app/main.py"

# Log completion timestamp
echo "$(date): Daily run completed" >> "$SCRIPT_DIR/logs/cron.log"
