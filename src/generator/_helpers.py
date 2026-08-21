from datetime import date, datetime, time, timedelta
from collections import Counter
import numpy as np

# =================================================================================
# Configuration
# =================================================================================

START = date(2025, 8, 17)
END = date(2026, 6, 14)

# =================================================================================
# Shared helper functions
# =================================================================================

def _generate_rng(seed: int) -> np.random.Generator:

  if not isinstance(seed, int):
    raise TypeError(
        "Seed must be an integer."
    )

  rng = np.random.default_rng(seed)

  return rng


def _week_ending_for(d: date) -> date:
  monday = d - timedelta(days=d.weekday())
  return monday + timedelta(days=6)


def _remove_random_off_weeks(
    schedule: list[dict],
    rng: np.random.Generator,
    n_random_off_weeks: int=2,
) -> list[dict]:
  
  if n_random_off_weeks >= len(schedule):
    raise ValueError(
      "Number of off-weeks must be less than number of weeks in the observation cycle."
      )
  
  eligible_indices = list(range(len(schedule)))
  rng.shuffle(eligible_indices)

  off_indices = set(
    eligible_indices[:n_random_off_weeks]
  )

  new_schedule = [
    week
    for i, week in enumerate(schedule)
    if i not in off_indices
  ]

  return new_schedule


def _generate_break_periods(
    start: date,
    end: date,
) -> list[tuple[date, date]]:
  
  break_periods: list[tuple[date, date]] = []

  for year in range(start.year, end.year + 1):
    break_start = date(year, 12, 24)
    break_end = date(year + 1, 1, 1)

    if break_start <= end and break_end >= start:
      break_periods.append(
        ( break_start, break_end )
      )

  return break_periods


def _find_phase(phases, _true_week_ending):
  selected_weights = None

  for start_date, weights in phases:
    if start_date <= _true_week_ending:
      selected_weights = weights
    else:
      break

  return selected_weights


def _level_of(item_name):
  return item_name.split()[-2]


def _level_weights(weights):
  level_totals = {}

  for item, count in weights.items():
    level = _level_of(item)
    level_totals[level] = level_totals.get(level, 0) + count

  return level_totals


def _select_weekly_narrative_themes(
    week_enrichment_counts: dict[str, Counter],
    week_jj_themes: dict[str, set],
) -> dict:

  cross_learner_raw = []
  s01_individual_raw = []
  s02_individual_raw = []

  s01_counter = week_enrichment_counts["S01"]
  s02_counter = week_enrichment_counts["S02"]
  s01_jj = week_jj_themes.get("S01", set())
  s02_jj = week_jj_themes.get("S02", set())

  all_theme_names = set(s01_counter) | set(s02_counter)

  for theme in all_theme_names:
    in_s01 = theme in s01_counter
    in_s02 = theme in s02_counter

    if in_s01 and in_s02:
      score = min(s01_counter[theme], s02_counter[theme])
      has_jj = theme in s01_jj or theme in s02_jj
      cross_learner_raw.append((theme, score, has_jj))

    elif in_s01:
      s01_individual_raw.append((theme, s01_counter[theme], theme in s01_jj))
    else:
      s02_individual_raw.append((theme, s02_counter[theme], theme in s02_jj))

  def _rank(bucket):
    return sorted(bucket, key=lambda entry: (entry[1], entry[2]), reverse=True)

  all_themes = {
    "cross_learner": _rank(cross_learner_raw),
    "S01_individual": _rank(s01_individual_raw),
    "S02_individual": _rank(s02_individual_raw),
  }

  top_themes = {
    bucket: entries[:2]
    for bucket, entries in all_themes.items()
  }

  return {"all_themes": all_themes, "top_themes": top_themes}