#!/usr/bin/env bash
set -euo pipefail

exec python -u agents/run_task.py "$@"
