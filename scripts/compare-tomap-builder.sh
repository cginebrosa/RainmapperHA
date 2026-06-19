#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

# Prefer the project virtualenv, but keep the script usable from a fresh shell.
PYTHON_BIN="${PYTHON_BIN:-.venv/bin/python}"
if [ ! -x "$PYTHON_BIN" ]; then
  PYTHON_BIN="${PYTHON_FALLBACK:-python3}"
fi

# These defaults compare the local Docker data volume against a temporary rebuild.
DATA_DIR="${DATA_DIR:-docker-data/Data}"
CURRENT_TOMAP_DIR="${CURRENT_TOMAP_DIR:-docker-data/Tomap}"
LAST_RAINS_HISTORY="${LAST_RAINS_HISTORY:-${RAINMAPPER_LAST_RAINS_HISTORY:-30}}"
MAX_THREADS="${MAX_THREADS:-${RAINMAPPER_MAX_THREADS:-1}}"

# Rebuild into a temporary directory so the comparison never mutates current Tomap files.
TMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/rainmapper-tomap-compare.XXXXXX")"
trap 'rm -rf "$TMP_DIR"' EXIT

REBUILT_TOMAP_DIR="$TMP_DIR/Tomap"

echo "Rebuilding Tomap into temporary directory:"
echo "$REBUILT_TOMAP_DIR"
"$PYTHON_BIN" tomap_builder.py \
  --data-dir "$DATA_DIR" \
  --maps-dir "$REBUILT_TOMAP_DIR" \
  --last-rains-history "$LAST_RAINS_HISTORY" \
  --max-threads "$MAX_THREADS"

echo ""
echo "Comparing rebuilt Tomap against $CURRENT_TOMAP_DIR..."
"$PYTHON_BIN" - "$CURRENT_TOMAP_DIR" "$REBUILT_TOMAP_DIR" "$LAST_RAINS_HISTORY" <<'PY'
import sys
from pathlib import Path

import pandas as pd

current_dir = Path(sys.argv[1])
rebuilt_dir = Path(sys.argv[2])
last_rains_history = sys.argv[3]

# Compare only the files produced by the current configured history length.
# Older LastXX files may legitimately remain in docker-data/Tomap from previous tests.
expected_files = [
    '01_Tomap_Last_day.csv',
    '02_Tomap_Last_week.csv',
    '03_Tomap_Last_two_weeks.csv',
    '04_Tomap_Last_three_weeks.csv',
    '05_Tomap_Last_month.csv',
    '06_Tomap_Last_two_months.csv',
    '07_Tomap_Last_three_months.csv',
    f'Last{last_rains_history}_rains.csv',
]

differences = []
for file_name in expected_files:
    current_file = current_dir / file_name
    rebuilt_file = rebuilt_dir / file_name
    if not current_file.exists():
        differences.append(f'{file_name}: missing current file')
        continue
    if not rebuilt_file.exists():
        differences.append(f'{file_name}: missing rebuilt file')
        continue

    current_df = pd.read_csv(current_file)
    rebuilt_df = pd.read_csv(rebuilt_file)

    # Start with structural checks; they make later content diffs easier to interpret.
    if list(current_df.columns) != list(rebuilt_df.columns):
        differences.append(f'{file_name}: columns differ')
        continue
    if len(current_df) != len(rebuilt_df):
        differences.append(f'{file_name}: row count differs current={len(current_df)} rebuilt={len(rebuilt_df)}')
        continue

    # String comparison avoids false negatives caused by pandas dtype inference differences.
    current_cmp = current_df.fillna('').astype(str)
    rebuilt_cmp = rebuilt_df.fillna('').astype(str)
    if not current_cmp.equals(rebuilt_cmp):
        differences.append(f'{file_name}: content differs')

if differences:
    print('Tomap comparison failed:')
    for difference in differences:
        print(f'- {difference}')
    raise SystemExit(1)

print('Tomap comparison passed: rebuilt files match current files.')
PY
