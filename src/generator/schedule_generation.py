from src.generator._helpers import _generate_break_periods, _remove_random_off_weeks, _week_ending_for, START, END

from datetime import date, datetime, time, timedelta

import numpy as np

# =================================================================================
# Schedule generators
# =================================================================================

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
    time(13, 30),
  ]

  spring_times = [
    time(14, 30),
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
        "student_id": ["S01", "S02"],
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
    time(16, 30),
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
            "student_id": [student_id],
            "observed_at": observation_datetime,
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


def generate_s03_observations(
    start: date,
    end: date,
    rng: np.random.Generator,
) -> list[dict]:

  if start > end:
    raise ValueError("Start date must not be after end date.")
  
  s03_observations = []

  spring_start = date(start.year + 1, 1, 1)
  spring_start_monday = (
    spring_start - timedelta(days=spring_start.weekday())
  )

  if end >= spring_start_monday:
    raise ValueError("End date must be within the start year.")

  adult_jj_times = [
    time(6, 15),
    time(19, 30),
    time(20, 30),
  ]

  daytime_class_times = [
    time(8, 0),
    time(10, 0),
    time(11, 30),
  ]

  break_periods = _generate_break_periods(start, end)

  current_week = _week_ending_for(start)

  while current_week <= end: 

    week_start = current_week - timedelta(days=6)

    valid_start = max(week_start, start)
    valid_end = min(current_week, end)
    valid_dates = [
      valid_start + timedelta(days=offset)
      for offset in range(
        (valid_end - valid_start).days + 1
      ) if not any(
        break_start <= valid_start + timedelta(days=offset) <= break_end
        for break_start, break_end in break_periods
      )
    ]

    if not valid_dates:
      current_week += timedelta(days=7)
      continue

    observation_date = rng.choice(
      valid_dates
    )

    observation_time = rng.choice(
      daytime_class_times
    )
    
    context = str(
      rng.choice(
        [
          "College Course - Logical Reasoning (Math and CS)",
          "Weight Training",
        ],
        p=[0.6, 0.4],
      )
    )

    s03_observations.append(
      {
        "student_id": ["S03"],
        "context": context,
        "observed_at": datetime.combine(
          observation_date,
          observation_time,
        ),
      }
    )

    available_jj_datetimes = [
      datetime.combine(
        jj_date, 
        jj_time,
      ) 
      for jj_date in valid_dates
      for jj_time in adult_jj_times
    ]

    jj_observations_this_week = int(
      rng.choice(
        [1, 2, 3],
        p=[0.3, 0.6, 0.1],
      )
    )

    if jj_observations_this_week > len(available_jj_datetimes):
      raise ValueError(
        "Not enough unique Jiu-Jitsu timestamps "
        " for the requested weekly observations."
      ) 

    selected_indices = rng.choice(
      len(available_jj_datetimes),
      size=jj_observations_this_week,
      replace=False,
    )

    for index in selected_indices:
      jj_observed_at = available_jj_datetimes[int(index)]   

      s03_observations.append(
        {
          "student_id": ["S03"],
          "context": "Jiu-Jitsu",
          "observed_at": jj_observed_at,
        }
      )

    current_week += timedelta(days=7)

  return sorted(
    s03_observations,
    key=lambda observation: observation["observed_at"],
  )

# =================================================================================
# Schedule orchestration
# =================================================================================

def combine_schedules(
    rng: np.random.Generator,
    n_random_off_weeks: int=2,
) -> list[dict]:

  combined_schedule = []

  academic_schedule = generate_academic_schedule(
    START, 
    END, 
    rng, 
    n_random_off_weeks
  )
  jj_schedule = generate_jiu_jitsu_observations(
    START, 
    END, 
    rng
  )

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


def derive_session_rows(
    combined_schedule: list[dict]
) -> list[dict]:

  derived_session_rows = []

  for week in combined_schedule:

    true_week_ending = week["week_ending"]

    academic = week["academic"]
    if academic is not None:
      for timestamp in academic["meeting_dates"]:
        for student_id in academic["student_id"]:
          derived_session_rows.append(
            {
              "true_week_ending": true_week_ending,
              "timestamp": timestamp,
              "student_id": student_id,
              "session_category": "Enrichment",
              "observation_context": "Enrichment",
            }
          )

    for jj_observation in week["jiu_jitsu"]:
      for student_id in jj_observation["student_id"]:
        derived_session_rows.append(
          {
            "true_week_ending": true_week_ending,
            "timestamp": jj_observation["observed_at"],
            "student_id": student_id,
            "session_category": "Jiu-Jitsu",
            "observation_context": "Jiu-Jitsu",
          }
        )

  return sorted(
    derived_session_rows,
    key=lambda row: row["timestamp"]
  )


def generate_synthesis_log_rows(
    combined_schedule: list[dict],
    cutoff_week: date,
    n_skipped_weeks: int=0,
) -> list[dict]:

  if n_skipped_weeks > len(combined_schedule):
    raise ValueError(
      "Number of weeks to be skipped cannot exceed the number of recorded sessions."
    )

  synthesis_logs_rows = []
  
  for session in combined_schedule[n_skipped_weeks:]:
    if session["academic"] is not None and session["week_ending"] >= cutoff_week:
      synthesis_logs_rows.append(
        {
          "week_ending": session["week_ending"],
          "num_sessions_reported": session["academic"]["num_sessions"],
        }
      )

  return synthesis_logs_rows


def inject_timestamp_skew(
    session_rows: list[dict],
    synthesis_log_rows: list[dict],
    rng: np.random.Generator,
    n_skewed_weeks: int=2,
) -> list[dict]:

  selectable_week_endings = [
    row["week_ending"]
    for row in synthesis_log_rows[:-1]
  ]

  if n_skewed_weeks > len(selectable_week_endings):
    raise ValueError(
      "Number of skewed weeks cannot exceed "
      "the number of selectable Enrichment weeks."
    )

  selected_indices = rng.choice(
    len(selectable_week_endings),
    size=n_skewed_weeks,
    replace=False,
  )

  selected_week_endings = {
    selectable_week_endings[i]
    for i in selected_indices
  }

  skewed_schedule = []

  for row in session_rows:
    new_row = row.copy()

    if (
      new_row["session_category"] == "Enrichment"
      and new_row["true_week_ending"] in selected_week_endings
    ):
      new_row["timestamp"] += timedelta(days=7)

    skewed_schedule.append(new_row)

  return sorted(
    skewed_schedule,
    key=lambda row: row["timestamp"]
  )