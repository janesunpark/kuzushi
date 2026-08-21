from datetime import date, datetime, time, timedelta
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