from datetime import date, datetime, time, timedelta

import numpy as np


START = date(2025, 8, 17)
END = date(2026, 6, 14)


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
    raise ValueError("Number of off-weeks must be less than number of weeks in the observation cycle.")
  
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


def generate_academic_schedule(
    start: date,
    end: date,
    rng: np.random.Generator,
    n_random_off_weeks: int=2,
) -> list[dict]:

  if start > end:
    raise ValueError("Start date must be before end date.")
  
  schedule = []

  spring_start = date(start.year + 1, 1, 1)
  spring_start_monday = spring_start - timedelta(days=spring_start.weekday())
  
  break_periods = _generate_break_periods(start, end)

  current_week = start - timedelta(days=start.weekday())

  fall_offsets = [3, 4]
  spring_offsets = [0, 2]

  fall_times = [
    time(15, 30),
  ]

  spring_times = [
    time(17, 0),
  ]

  while current_week <= end:
    week_ending = _week_ending_for(current_week)

    if current_week < spring_start_monday:
      weekday_offsets = fall_offsets
      meeting_times = fall_times
    else:
      weekday_offsets = spring_offsets
      meeting_times = spring_times
  
    candidate_dates = [
      current_week + timedelta(days=offset)
      for offset in weekday_offsets
    ]

    candidate_dates = [
      candidate_date
      for candidate_date in candidate_dates
      if (
        start <= candidate_date <= end
        and not any(
          break_start <= candidate_date <= break_end
          for break_start, break_end in break_periods
        )
      )
    ]
    
    if not candidate_dates:
      current_week += timedelta(days=7)
      continue
    
    num_sessions = int(
      rng.choice(
        [1, 2],
        p=[0.15, 0.85],
      )
    )

    num_sessions = min(num_sessions, len(candidate_dates))
    
    if num_sessions == 1:
     
      selected_index = int(rng.integers(0, len(candidate_dates)))
      selected_dates = [
        candidate_dates[selected_index]
      ]
    else:
      selected_dates = candidate_dates

    meeting_dates = []

    for meeting_date in selected_dates:
      meeting_time_index = int(
        rng.integers(0, len(meeting_times))
      )
      meeting_time = meeting_times[meeting_time_index]
      
      meeting_dates.append(
        datetime.combine(meeting_date, meeting_time)
      )

    schedule.append(
      {
        "week_ending": week_ending,
        "num_sessions": len(meeting_dates),
        "meeting_dates": meeting_dates, 
      }
    )

    current_week += timedelta(days=7)

  schedule = _remove_random_off_weeks(
    schedule,
    rng,
    n_random_off_weeks,
  )

  return schedule


def generate_jiu_jitsu_observations(
    start: date,
    end: date,
    rng: np.random.Generator,
) -> list[dict]:
  
  if start > end:
    raise ValueError("Start date must not be after end date.")

  observations = []

  observation_times = [
    time(15, 30),
    time(14, 30),
    time(17, 30),
  ]

  student_cadence = {
    "S01": {
      "initial_offset_max": 35,
      "interval_min": 33,
      "interval_max": 45,
    },
    "S02": {
      "initial_offset_max": 20,
      "interval_min": 15,
      "interval_max": 32,
    },
  }

  break_periods = _generate_break_periods(start, end)

  for student_id, cadence in student_cadence.items():
    initial_offset = int(
      rng.integers(
        0,
        cadence["initial_offset_max"],
      )
    )

    observation_date = (
      start + timedelta(days=initial_offset)
    )

    while observation_date <= end:

      is_break = any(
        break_start <= observation_date <= break_end
        for break_start, break_end in break_periods
      )

      if not is_break:

        observation_time_index = int(
          rng.integers(0, len(observation_times))
        )

        observation_datetime = datetime.combine(
          observation_date, 
          observation_times[observation_time_index]
          )

        observations.append(
          {
            "student_id": student_id,
            "observed_at": observation_datetime
          }
        )

      interval_days = int(
        rng.integers(
          cadence["interval_min"],
          cadence["interval_max"] + 1,
        )
      )

      observation_date += timedelta(days=interval_days)

  observations.sort(
    key=lambda record: record["observed_at"]
  )

  return observations


def combine_schedules(
    seed: int,
    n_random_off_weeks: int=2,
) -> list[dict]:
  
  rng = _generate_rng(seed)

  combined_schedule = []

  academic_schedule = generate_academic_schedule(START, END, rng, n_random_off_weeks)
  jj_schedule = generate_jiu_jitsu_observations(START, END, rng)

  academic_week_endings = {
    week["week_ending"]
    for week in academic_schedule
  }

  jj_observation_weeks = {
    _week_ending_for(
      observation["observed_at"].date()
    )
    for observation in jj_schedule
  }

  combined_week_endings = (
    academic_week_endings | jj_observation_weeks
  )
  
  sorted_week_endings = sorted(combined_week_endings)
  
  for week_ending in sorted_week_endings:
    academic_entry = next(
      (week
      for week in academic_schedule
      if week["week_ending"] == week_ending
      ),
      None,
    )

    jj_observations_for_week = [
      observation
      for observation in jj_schedule
      if _week_ending_for(
        observation["observed_at"].date()
      ) == week_ending
    ]
    combined_schedule.append(
      {
        "week_ending": week_ending,
        "academic": academic_entry,
        "jiu_jitsu": jj_observations_for_week,
      }
    )
  
  return combined_schedule