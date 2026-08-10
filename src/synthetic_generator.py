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


def _find_phase(phases, true_week_ending):
  selected_weights = None

  for start_date, weights in phases:
    if start_date <= true_week_ending:
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
    n_skipped_weeks: int=0,
) -> list[dict]:

  if n_skipped_weeks > len(combined_schedule):
    raise ValueError(
      "Number of weeks to be skipped cannot exceed the number of recorded sessions."
    )

  synthesis_logs_rows = []
  
  for session in combined_schedule[n_skipped_weeks:]:
    if session["academic"] is not None:
      synthesis_logs_rows.append(
        {
          "week_ending": session["week_ending"],
          "num_sessions_reported": session["academic"]["num_sessions"],
        }
      )

  return synthesis_logs_rows


def assign_observer_id(
    session_rows: list[dict],
    transition_week: date,
) -> list[dict]:

  finalized_rows = []

  for row in session_rows:
    new_row = row.copy()

    if new_row["true_week_ending"] >= transition_week:
      new_row["observer_id"] = "T01"
    else: 
      new_row["observer_id"] = "T0"

    finalized_rows.append(new_row)

  return finalized_rows


def assign_observation_context(
  session_rows: list[dict],
  rng: np.random.Generator,
  cutoff_week: date,
) -> list[dict]:

  meeting_categories = {}
  finalized_rows = []

  categories = [
    "Enrichment: Group Session",
    "Enrichment: Group Activity",
  ]

  probabilities = np.array([43, 12]) / sum([43, 12])

  for row in session_rows:
    new_row = row.copy()

    if new_row["session_category"] == "Enrichment":
      session_key = new_row["timestamp"]

      if session_key not in meeting_categories:
        if new_row["true_week_ending"] >= cutoff_week:
          meeting_categories[session_key] = "Enrichment (Sibling Dyad)"

        else:
          meeting_categories[session_key] = str(
            rng.choice(
              categories,
              p=probabilities,
            )
          )

      new_row["observation_context"] = (
        meeting_categories[session_key]
      )

    finalized_rows.append(new_row)

  return finalized_rows


def assign_core_ratings(
    session_rows: list[dict],
    rng: np.random.Generator,
) -> list[dict]:

  finalized_rows = []

  student_weights = {
    "S01": {
      "Focus or Attention": {
        "ratings": np.arange(1, 6),
        "weights": np.array([3, 7, 19, 27, 18])/sum([3, 7, 19, 27, 18]),
      },
      "Carryover or Retention": {
        "ratings": np.arange(1, 6),
        "weights": np.array([1, 2, 26, 30, 15])/sum([1, 2, 26, 30, 15]),
      },
      "Confidence, Autonomy, or Initiative": {
        "ratings": np.arange(1, 6),
        "weights": np.array([1, 4, 18, 27, 24])/sum([1, 4, 18, 27, 24]),
      },
    },

    "S02": {
      "Focus or Attention": {
        "ratings": np.arange(1, 6),
        "weights": np.array([3, 10, 28, 25, 14])/sum([3, 10, 28, 25, 14]),
      },
      "Carryover or Retention": {
        "ratings": np.arange(1, 6),
        "weights": np.array([0, 5, 32, 29, 14])/sum([0, 5, 32, 29, 14]),
      },
      "Confidence, Autonomy, or Initiative": {
        "ratings": np.arange(1, 6),
        "weights": np.array([3, 6, 23, 25, 23])/sum([3, 6, 23, 25, 23]),
      },
    },
  }

  for row in session_rows:
    new_row = row.copy()

    student_id = new_row["student_id"]
    distributions = student_weights[student_id]

    for domain, distribution in distributions.items():

      new_row[domain] = int(
        rng.choice(
          distribution["ratings"],
          p=distribution["weights"],
        )
      )

    finalized_rows.append(new_row)

  return finalized_rows


def assign_secondary_ratings(
    session_rows: list[dict],
    rng: np.random.Generator,
) -> list[dict]:

  finalized_rows = []

  null_rates = {
    "Enrichment": {
      "Problem-Solving or Cognitive Flexibility": 0.15,
      "Resilience": 0.1,
      "Frustration Tolerance": 0.13,
      "Abstract Thinking and Pattern Recognition": 0.23,
      "Impulse Modulation": 0.28,
    },
    "Jiu-Jitsu": {
      "Problem-Solving or Cognitive Flexibility": 0.15,
      "Resilience": 0.11,
      "Frustration Tolerance": 0.27,
      "Abstract Thinking and Pattern Recognition": 0.5,
      "Impulse Modulation": 0.55,
    },
  }

  pooled_value_distribution = {
    "Problem-Solving or Cognitive Flexibility": {
      "ratings": np.arange(1, 6),
      "weights": np.array([14, 12, 62, 26, 17])/sum([14, 12, 62, 26, 17]),
    },
    "Resilience": {
      "ratings": np.arange(1, 6),
      "weights": np.array([13, 10, 64, 27, 25])/sum([13, 10, 64, 27, 25]),
    },
    "Frustration Tolerance": {
      "ratings": np.arange(1, 6),
      "weights": np.array([18, 9, 51, 33, 20])/sum([18, 9, 51, 33, 20]),
    },
    "Abstract Thinking and Pattern Recognition": {
      "ratings": np.arange(1, 6),
      "weights": np.array([5, 19, 38, 31, 20])/sum([5, 19, 38, 31, 20]),
    },
    "Impulse Modulation": {
      "ratings": np.arange(1, 6),
      "weights": np.array([13, 15, 34, 20, 23])/sum([13, 15, 34, 20, 23]),
    },
  }

  for row in session_rows:
    new_row = row.copy()

    context = new_row["session_category"]
    context_null_rates = null_rates[context]

    for domain, null_rate in context_null_rates.items():

      is_null = rng.choice(
        [True, False],
        p=[null_rate, 1 - null_rate],
      )

      if is_null:
        new_row[domain] = None
      else:
        distribution = pooled_value_distribution[domain]

        new_row[domain] = int(
          rng.choice(
            distribution["ratings"],
            p=distribution["weights"],
          )
        )

    finalized_rows.append(new_row)

  return finalized_rows


def assign_deprecated_ratings(
    session_rows: list[dict],
    rng: np.random.Generator,
    cutoff_week: date,
) -> list[dict]:

  finalized_rows = []

  null_rates = {
    "Coordination and Motor Skills": 0.296,
    "Social Regulation": 0.042,
  }

  for row in session_rows:
    new_row = row.copy()
    current_date = new_row["true_week_ending"]

    if current_date >= cutoff_week:
      for domain in null_rates:
        new_row[domain] = None

    else:
      for domain in null_rates:
        null_rate = null_rates[domain]

        is_null = rng.choice(
          [True, False],
          p=[null_rate, 1 - null_rate],
        )

        if is_null:
          new_row[domain] = None
        else:
          new_row[domain] = int(
            rng.choice(
              np.arange(1, 6),
              p=np.array([20, 20, 20, 20, 20])/sum([20, 20, 20, 20, 20])
            )
          )

    finalized_rows.append(new_row)

  return finalized_rows


def assign_pages_completed(
    session_rows: list[dict],
    rng: np.random.Generator,
    cutoff_week: date,
) -> list[dict]:

  finalized_rows = []

  for row in session_rows:
    new_row = row.copy()

    if new_row["session_category"] == "Jiu-Jitsu":
      new_row["Number of Pages Completed"] = None

    else:
      if new_row["true_week_ending"] < cutoff_week:
        new_row["Number of Pages Completed"] = None

      else:
        current_week = new_row["true_week_ending"]

        progress = (
          (current_week - cutoff_week).days / 
          (END - cutoff_week).days
        )

        base_mean = 5.2 if new_row["student_id"] == "S01" else 6.5
        final_mean = 6.0 if new_row["student_id"] == "S01" else 7.5

        expected_pages = (
          base_mean + 
          progress * (final_mean - base_mean)
        )

        pages = int(round(
          rng.normal(expected_pages, 3.0)
        ))

        pages = max(1, min(21, pages))

        new_row["Number of Pages Completed"] = pages

    finalized_rows.append(new_row)

  return finalized_rows


def assign_task_difficulty(
    session_rows: list[dict],
    rng: np.random.Generator,
    cutoff_week: date,
) -> list[dict]:

  finalized_rows = []

  distribution = {
    "S01": {
      "ratings": np.arange(1, 6),
      "weights": np.array([5, 11, 10, 6, 5])/sum([5, 11, 10, 6, 5]),
    },
    "S02": {
      "ratings": np.arange(1, 6),
      "weights": np.array([2, 8, 18, 4, 5])/sum([2, 8, 18, 4, 5]),
    },
  }

  for row in session_rows:
    new_row = row.copy()

    new_row["Task Difficulty or Novelty"] = None

    if new_row["true_week_ending"] >= cutoff_week:
      student = new_row["student_id"]

      new_row["Task Difficulty or Novelty"] = int(
        rng.choice(
          distribution[student]["ratings"],
          p=distribution[student]["weights"]
        )
      ) 

    finalized_rows.append(new_row)

  return finalized_rows


def assign_duration(
    session_rows:list[dict],
    rng: np.random.Generator,
    cutoff_week: date,
    phase_shift_week: date,
) -> list[dict]:

  finalized_rows = []

  early_duration_distribution = {
    45 : 2,
    60 : 4,
    75 : 4,
    80 : 10,
    90 : 2, 
    120: 8,
  }

  late_duration_distribution = {
    60 : 18,
    80 : 38,
    90 : 4,
  }

  for row in session_rows:
    new_row = row.copy()

    if new_row["true_week_ending"] < cutoff_week:
      new_row["Duration in Minutes"] = None

    elif new_row["session_category"] == "Jiu-Jitsu":
      new_row["Duration in Minutes"] = 45

    else: 
      if new_row["true_week_ending"] >= phase_shift_week:
        distribution = late_duration_distribution

      else:
        distribution = early_duration_distribution

      minutes = list(distribution.keys())
      weights = np.array(list(distribution.values()))
      weights = weights / weights.sum()

      new_row["Duration in Minutes"] = int(
        rng.choice(minutes, p=weights)
      )

    finalized_rows.append(new_row)

  return finalized_rows


def assign_primary_task_type(
    session_rows: list[dict],
    rng: np.random.Generator,
    cutoff_week: date,
) -> list[dict]:

  finalized_rows = []

  task_distribution = {
    "Mixed" : 20,
    "Worksheet" : 14,
    "Puzzle" : 1,
  }

  for row in session_rows:
    new_row = row.copy()

    new_row["Primary Task Type"] = None

    if (
      new_row["true_week_ending"] >= cutoff_week
      and new_row["session_category"] == "Enrichment"
    ):
      tasks = list(task_distribution.keys())
      weights = np.array(list(task_distribution.values()))
      weights = weights / weights.sum()

      new_row["Primary Task Type"] = str(rng.choice(
        tasks,
        p=weights
      ))
  
    finalized_rows.append(new_row)

  return finalized_rows


def assign_published_materials_used(
    session_rows: list[dict],
    rng: np.random.Generator,
    cutoff_week: date,
) -> list[dict]:

  finalized_rows = []

  s01_phases = [
    (date(2025, 12, 14), {"MathQuest KA Workbook": 4, "MathQuest KA Textbook": 3, "MathQuest PKA Workbook": 1}),
    (date(2026, 1, 18),  {"MathQuest KB Workbook": 1, "MathQuest KA Textbook": 1, "MathQuest KA Workbook": 1, "MathQuest KB Textbook": 1}),
    (date(2026, 2, 1),   {"MathQuest PKB Workbook": 18, "MathQuest PKB Textbook": 16, "MathQuest KB Workbook": 5, "MathQuest KB Textbook": 1}),
    (date(2026, 6, 7),   {"MathQuest KA Textbook": 3, "MathQuest KA Workbook": 2}),
  ]

  s02_phases = [
    (date(2025, 12, 14), {"MathQuest KA Workbook": 3, "MathQuest KA Textbook": 3}),
    (date(2026, 1, 11),  {"MathQuest KB Textbook": 1, "MathQuest KA Workbook": 1}),
    (date(2026, 1, 18),   {"MathQuest KB Workbook": 25, "MathQuest KB Textbook": 21}),
    (date(2026, 6, 7),   {"MathQuest KB Textbook": 2, "MathQuest 1A Textbook": 1}),
  ]

  level_phases = {
    "S01": s01_phases,
    "S02": s02_phases,
  }

  for row in session_rows:
    new_row = row.copy()

    if (
      new_row["true_week_ending"] < cutoff_week
      or new_row["session_category"] != "Enrichment"
    ):
      new_row["Published Materials Used"] = None

    else:
      weights = _find_phase(
        level_phases[new_row["student_id"]], 
        new_row["true_week_ending"]
      )

      items = list(weights.keys())
      probs = np.array(list(weights.values()))
      probs = probs / probs.sum()

      item_count = int(
        rng.choice(
          [1, 2], 
          p=[0.76, 0.24]
          )
        )

      if item_count == 1:
        value = [str(rng.choice(items, p=probs))]

      elif rng.random() < 0.86:
          level_weights = _level_weights(weights)
          levels = list(level_weights.keys())
          level_probs = np.array(list(level_weights.values()))
          level_probs = level_probs / level_probs.sum()

          level = str(
            rng.choice(
              levels, 
              p=level_probs
              )
            )

          value = [f"MathQuest {level} Textbook", f"MathQuest {level} Workbook"]

      else:
        value = [
          str(v) 
          for v in rng.choice(
            items, 
            size=2, 
            replace=False, 
            p=probs
          )
        ] 

      new_row["Published Materials Used"] = ", ".join(value)

    finalized_rows.append(new_row)

  return finalized_rows


def assign_puzzle_type(
    session_rows: list[dict],
    rng: np.random.Generator,
    cutoff_week: date,
    primary_task_type_cutoff_week: date,
) -> list[dict]:

  finalized_rows = []

  item_distribution = {
    "S01": {
      "items": np.array([
        "CubePix",
        "GeoCrystals",
        "Tetromino Square",
        "Geoboard",
        "Pattern Blocks",
      ]),
      "weights": np.array([7, 5, 3, 2, 1]),
    },
    "S02": {
      "items": np.array([
        "CubePix",
        "GeoCrystals",
        "Tetromino Square",
        "Geoboard",
        "Pattern Blocks",
      ]),
      "weights": np.array([10, 5, 5, 3, 1]),
    },
  }

  null_rates = {
    "Worksheet": 0.75,
    "Mixed": 0.0,
    "Puzzle": 0.0,
  }

  item_counts = {
    "Mixed": {
      "counts": np.array([1, 2, 3]),
      "weights": np.array([8, 12, 1]),
    },
    "Puzzle": {
      "counts": np.array([1, 2, 3]),
      "weights": np.array([8, 12, 1]),
    },
  }

  for row in session_rows:
    new_row = row.copy()
    new_row["Puzzle Type"] = None

    if (
      new_row["true_week_ending"] >= cutoff_week
      and new_row["session_category"] == "Enrichment"
    ):

      if new_row["true_week_ending"] < primary_task_type_cutoff_week:
        student_id = new_row["student_id"]
        puzzles = item_distribution[student_id]["items"]
        weights = item_distribution[student_id]["weights"]
        weights = weights / weights.sum()

        if new_row["true_week_ending"] < primary_task_type_cutoff_week:

          if rng.random() >= 0.5:
            new_row["Puzzle Type"] = str(rng.choice(puzzles, p=weights))

      else:
        task_type = new_row['Primary Task Type']

        if rng.random() >= null_rates[task_type]:
          if task_type == "Worksheet":
            item_count = 1

          else:
            counts = item_counts[task_type]["counts"]

            probs = item_counts[task_type]["weights"]
            probs = probs / probs.sum()

            item_count = int(
              rng.choice(
                counts,
                p=probs,
              )
            )

          selected_puzzles = [
            str(v) 
            for v in rng.choice(
              puzzles,
              size=item_count,
              replace=False,
              p=weights,
            )
          ]

          new_row["Puzzle Type"] = ", ".join(selected_puzzles)

    finalized_rows.append(new_row)

  return finalized_rows


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


