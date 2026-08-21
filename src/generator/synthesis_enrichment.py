from datetime import date, datetime
from collections import Counter, defaultdict
import numpy as np


def assign_synthesis_static_fields(
    synthesis_rows: list[dict],
) -> list[dict]:

  finalized_rows = []

  for row in synthesis_rows:
    new_row = row.copy()
    new_row["Observer ID"] = "T01"
    new_row["Student ID"] = "S01, S02"
    new_row["Are participants siblings?"] = "Yes"
    new_row["Dyad ID"] = "A"
    new_row["Column 10"] = None
    new_row["Column 11"] = None
    new_row["Column 12"] = None

    finalized_rows.append(new_row)

  return finalized_rows


def assign_jj_synthesis_fields(
    synthesis_rows: list[dict],
    rng: np.random.Generator,
    cutoff_week: date,
) -> list[dict]:

  finalized_rows = []

  for row in synthesis_rows:
    new_row = row.copy()

    new_row["JJ Observed"] = None
    new_row["Private Lessons"] = None

    if new_row["week_ending"] >= cutoff_week:
      new_row["Private Lessons"] = rng.choice(
        ["S02", None],
        p=[0.875, 0.125],
      )

      if new_row["Private Lessons"] != None:
        new_row["JJ Observed"] = rng.choice(
          [None, "S01, S02", "S02"],
          p=[9/14, 3/14, 2/14],
        )

    finalized_rows.append(new_row)

  return finalized_rows


def summarize_weekly_notes_themes(
    session_rows: list[dict],
) -> tuple[dict[date, dict[str, Counter]], dict[date, dict[str, set]]]:

  weekly_counts = defaultdict(lambda: defaultdict(Counter))
  weekly_jj_themes = defaultdict(lambda: defaultdict(set))

  for row in session_rows:
    week = row["_true_week_ending"]
    student = row["student_id"]
    themes = row["_selected_notes_themes"]

    if row["_session_category"] == "Enrichment":
      weekly_counts[week][student].update(themes)

    elif row["_session_category"] == "Jiu-Jitsu":
      weekly_jj_themes[week][student].update(themes)

    else:
      raise ValueError(f"Unexpected _session_category: {row['_session_category']!r}")

  weekly_counts = {
    week: dict(students)
    for week, students in weekly_counts.items()
  }

  weekly_jj_themes = {
    week: dict(students)
    for week, students in weekly_jj_themes.items()
  }

  return weekly_counts, weekly_jj_themes