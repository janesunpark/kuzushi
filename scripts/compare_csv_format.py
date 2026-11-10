import csv
from itertools import zip_longest
import re


REAL_SESSION_PATH = "data/raw/session_observation_log_2025-2026.csv"
SYNTH_SESSION_PATH = "data/synthetic/synthetic_session_log_seed42.csv"
REAL_WEEKLY_PATH = "data/raw/weekly_synthesis_log_2025-2026.csv"
SYNTH_WEEKLY_PATH = "data/synthetic/synthetic_weekly_log_seed42.csv"


def _replace_digit_with_D(value):
  return re.sub(r"\d", "D", value)


def read_rows(path):
  with open(path, newline="", encoding="utf-8") as f:
    return list(csv.reader(f))


def compare_headers(name, real_header, synth_header):

  print(name)
  print(len(real_header), len(synth_header))

  for i, (real_col, synth_col) in enumerate(zip_longest(real_header, synth_header)):
    if real_col != synth_col:
      print("Position: ", repr(i))
      print("real_header value: ", repr(real_col))
      print("synth_header value: ", repr(synth_col))


def compare_value_formats(name, real_rows, synth_rows):

  if real_rows[0] != synth_rows[0]:
    print(f"{name}: headers differ, skipping value comparison")
    return
  
  header = real_rows[0]
  matched = 0

  FREE_TEXT_COLS = [
    "Notes",
    "Snapshot",
    "Notable Shifts or Confirmations",
    "Learning Mechanisms Observed",
    "Optional: Data Flags (If Relevant)",
  ]
  for i, col_name in enumerate(header):
    if col_name in FREE_TEXT_COLS:
      continue

    real_formats = {_replace_digit_with_D(row[i]) for row in real_rows[1:]}
    synth_formats = {_replace_digit_with_D(row[i]) for row in synth_rows[1:]}

    if real_formats == synth_formats:
      matched += 1
    else:
      print(i, col_name)

      real_only = sorted(real_formats - synth_formats)
      synth_only = sorted(synth_formats - real_formats)

      if len(real_only) > 10 or len(synth_only) > 10:
        print("only in real:", len(real_only), "| only in synthetic:", len(synth_only))

      else:
        print("only in real:", real_only)
        print("only in synthetic", synth_only)

  print(f"{matched} columns matched")


if __name__ == "__main__":
  
  PAIRS = [
    ("session", REAL_SESSION_PATH, SYNTH_SESSION_PATH),
    ("weekly", REAL_WEEKLY_PATH, SYNTH_WEEKLY_PATH),
  ]
  
  for name, real_path, synth_path in PAIRS:
    real_rows = read_rows(real_path)
    synth_rows = read_rows(synth_path)

    if name == "session":
      real_rows = [real_rows[0]] + [row for row in real_rows[1:] if row[2] in ("S01", "S02")]

    compare_headers(name, real_rows[0], synth_rows[0])
    compare_value_formats(name, real_rows, synth_rows)
