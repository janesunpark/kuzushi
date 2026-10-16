from copy import deepcopy
from datetime import date, datetime, timedelta
from collections import Counter
import csv
import pytest

from src import synthetic_generator as sg


SESSION_HEADERS = [
  'Timestamp',
  'Observer ID',
  'Student ID',
  'Observation Context',
  'Focus or Attention',
  'Coordination and Motor Skills - may be DELETED',
  'Carryover or Retention',
  'Problem-Solving or Cognitive Flexibility',
  'Resilience (Response to Mistakes or Corrections)',
  'Confidence, Autonomy, or Initiative',
  'Social Regulation - may be DELETED',
  'Frustration Tolerance',
  'Notes',
  'Email Address',
  'Abstract Thinking and Pattern Recognition',
  'Impulse Modulation',
  'Number of Pages Completed',
  'Published Materials Used',
  'Duration in Minutes',
  'Emotional Tone of Teacher',
  'Parent Interaction',
  'Environment or Disruptions',
  'Task Difficulty or Novelty',
  'Puzzle Type',
  'Puzzle Challenge or Novelty',
  'Primary Task Type',
  'Column 24',
  'Column 25',
  'Task Difficulty or Novelty',
  'Column 23',
]

SYNTHESIS_HEADERS = [
  'Timestamp',
  'Observer ID',
  'Student ID',
  'Week of ',
  'Number of Enrichment Sessions',
  'Snapshot',
  'Notable Shifts or Confirmations',
  'Learning Mechanisms Observed',
  'Optional: Data Flags (If Relevant)',
  'Are participants siblings?',
  'Dyad ID',
  'If Jiu-Jitsu sessions were observed, for which learner(s)?',
  'Select any learner(s) that take at least one weekly private lessons in Jiu-Jitsu.',
  'Column 11',
  'Column 12',
  'Column 10',
]

# =============================================================================
# RNG behavior
# =============================================================================

def test_same_seed_same_output():
  rng1 = sg._generate_rng(42)
  rng2 = sg._generate_rng(42)

  assert(
    sg.generate_jiu_jitsu_observations(sg.START, sg.END, rng1)
    ==
    sg.generate_jiu_jitsu_observations(sg.START, sg.END, rng2)
  )


def test_shared_rng_advances_state():
  rng = sg._generate_rng(42)

  first = sg.generate_jiu_jitsu_observations(sg.START, sg.END, rng)
  second = sg.generate_jiu_jitsu_observations(sg.START, sg.END, rng)

  assert first != second

# =============================================================================
# Schedule derivation
# =============================================================================

def test_same_seed_expected_row_count():
  rng = sg._generate_rng(42)
  rows = sg.derive_session_rows(
    sg.combine_schedules(rng, 2)
  )

  assert len(rows) == 170


def test_same_seed_produces_same_rows():
  rng1 = sg._generate_rng(42)
  rng2 = sg._generate_rng(42)

  rows1 = sg.derive_session_rows(
    sg.combine_schedules(rng1, 2)
  )
  rows2 = sg.derive_session_rows(
    sg.combine_schedules(rng2, 2)
  )
  
  assert rows1 == rows2

# =============================================================================
# Observer assignment
# =============================================================================

def test_assign_observer_id_does_not_mutate_input():
  rng = sg._generate_rng(42)

  session_rows = sg.derive_session_rows(
    sg.combine_schedules(rng, 2)
  )

  original_rows = [
    row.copy()
    for row in session_rows
  ]

  sg.assign_observer_id(
    session_rows,
    date(2025, 12, 14)
  )

  assert session_rows == original_rows


def test_observer_id_shifts_at_transition_week():
  rng = sg._generate_rng(42)

  session_rows = sg.derive_session_rows(
    sg.combine_schedules(rng, 2)
  )

  transition_week = date(2025, 12, 14)

  rows1 = sg.assign_observer_id(session_rows, transition_week)

  for row in rows1:
    if row["_true_week_ending"] < transition_week:
      assert row["observer_id"] == "T0"
    else:
      assert row["observer_id"] == "T01"

  rows2 = sg.assign_observer_id(session_rows, transition_week)

  assert rows1 == rows2

# =============================================================================
# Observation context assignment
# =============================================================================

def test_assign_observation_context_does_not_mutate_input():
  rng = sg._generate_rng(42)

  session_rows = sg.derive_session_rows(
    sg.combine_schedules(rng, 2)
  )

  original_rows = [
    row.copy()
    for row in session_rows
  ]

  sg.assign_observation_context(
    session_rows,
    sg._generate_rng(42),
    date(2026, 1, 25),
  )

  assert session_rows == original_rows


def test_enrichment_rows_from_same_meeting_share_context():
  rng = sg._generate_rng(42)

  session_rows = sg.derive_session_rows(
    sg.combine_schedules(rng, 2)
  )

  assigned_rows = sg.assign_observation_context(
    session_rows,
    sg._generate_rng(42),
    date(2026, 1, 25)
  )

  contexts_by_timestamp = {}

  for row in assigned_rows:
    if row["_session_category"] == "Jiu-Jitsu":
      continue

    timestamp = row["timestamp"]

    contexts_by_timestamp.setdefault(
      timestamp,
      set(),
    ).add(row["observation_context"])

  assert all(
    len(contexts) == 1
    for contexts in contexts_by_timestamp.values()
  )


def test_assign_observation_context_preserves__session_category():
  rng = sg._generate_rng(42)

  session_rows = sg.derive_session_rows(
    sg.combine_schedules(rng, 2)
  )

  assigned_rows = sg.assign_observation_context(
    session_rows,
    sg._generate_rng(42),
    date(2026, 1, 25),
  )

  for original, assigned in zip(session_rows, assigned_rows):
    if original["_session_category"] == "Jiu-Jitsu":
      assert assigned["_session_category"] == "Jiu-Jitsu"


def test_assign_observation_context_preserves_jiu_jitsu_context():
  rng = sg._generate_rng(42)

  session_rows = sg.derive_session_rows(
    sg.combine_schedules(rng, 2)
  )

  assigned_rows = sg.assign_observation_context(
    session_rows,
    sg._generate_rng(42),
    date(2026, 1, 25),
  )

  for original, assigned in zip(session_rows, assigned_rows):
    if original["_session_category"] == "Jiu-Jitsu":
      assert(
        assigned["observation_context"] == "Jiu-Jitsu"
      )

# =============================================================================
# Core ratings
# =============================================================================

def test_assign_core_ratings_does_not_mutate_input():
  rng = sg._generate_rng(42)

  session_rows = sg.derive_session_rows(
    sg.combine_schedules(rng, 2)
  )

  original_rows = [
    row.copy()
    for row in session_rows
  ]

  sg.assign_core_ratings(
    session_rows,
    sg._generate_rng(42),
  )

  assert session_rows == original_rows


def test_assign_core_ratings_same_seed_same_output():
  rng = sg._generate_rng(42)

  session_rows = sg.derive_session_rows(
    sg.combine_schedules(rng, 2)
  )

  rows1 = sg.assign_core_ratings(
    session_rows,
    sg._generate_rng(42),
  )

  rows2 = sg.assign_core_ratings(
    session_rows,
    sg._generate_rng(42),
  )

  assert rows1 == rows2


def test_assign_core_ratings_shared_rng_advances_state():
  rng = sg._generate_rng(42)

  session_rows = sg.derive_session_rows(
    sg.combine_schedules(rng, 2)
  )

  rng = sg._generate_rng(42)

  rows1 = sg.assign_core_ratings(
    session_rows,
    rng,
  )

  rows2 = sg.assign_core_ratings(
    session_rows,
    rng,
  )

  assert rows1 != rows2


def test_core_ratings_are_between_one_and_five():
  rng = sg._generate_rng(42)

  session_rows = sg.derive_session_rows(
    sg.combine_schedules(rng, 2)
  )

  assigned_rows = sg.assign_core_ratings(
    session_rows,
    sg._generate_rng(42),
  )

  rating_columns = [
    "Focus or Attention",
    "Carryover or Retention",
    "Confidence, Autonomy, or Initiative",
  ]

  for row in assigned_rows:
    for column in rating_columns:
      assert row[column] in {1, 2, 3, 4, 5}


def test_every_row_receives_core_ratings():
  rng = sg._generate_rng(42)

  session_rows = sg.derive_session_rows(
    sg.combine_schedules(rng, 2)
  )

  assigned_rows = sg.assign_core_ratings(
    session_rows,
    sg._generate_rng(42),
  )

  rating_colunns = [
    "Focus or Attention",
    "Carryover or Retention",
    "Confidence, Autonomy, or Initiative",
  ]

  for row in assigned_rows:
    for column in rating_colunns:
      assert row[column] is not None


def test_assign_core_ratings_preserves_existing_columns():
  rng = sg._generate_rng(42)

  session_rows = sg.derive_session_rows(
    sg.combine_schedules(rng, 2)
  )

  assigned_rows = sg.assign_core_ratings(
    session_rows,
    sg._generate_rng(42),
  )

  for original, assigned in zip(session_rows, assigned_rows):
    assert original["student_id"] == assigned["student_id"]
    assert original["timestamp"] == assigned["timestamp"]
    assert original["_session_category"] == assigned["_session_category"]
    assert original["observation_context"] == assigned["observation_context"]

# =============================================================================
# Boundary weeks
# =============================================================================

# Regression test protecting transition-week behavior.

def test_observation_context_boundary_week_is_fully_new():
  rng = sg._generate_rng(42)

  rows = sg.derive_session_rows(sg.combine_schedules(rng, 2))
  
  rows = sg.assign_observation_context(
    rows, 
    rng, 
    date(2026, 1, 25)
  )

  boundary = [r for r in rows if r["_true_week_ending"] == date(2026, 1, 25) and r["_session_category"] == "Enrichment"]

  assert boundary
  assert all(r["observation_context"] == "Enrichment (Sibling Dyad)" for r in boundary)


def test_deprecated_ratings_boundary_week_is_fully_null():
  rng = sg._generate_rng(42)

  rows = sg.derive_session_rows(sg.combine_schedules(rng, 2))
  
  rows = sg.assign_deprecated_ratings(
    rows, 
    rng, 
    date(2026, 1, 25)
  )

  boundary = [r for r in rows if r["_true_week_ending"] == date(2026, 1, 25)]

  assert boundary
  assert all(r["Coordination and Motor Skills"] is None 
             and r["Social Regulation"] is None for r in boundary)


def test_pages_completed_boundary_week_is_already_active():
  rng = sg._generate_rng(42)

  rows = sg.derive_session_rows(sg.combine_schedules(rng, 2))
  
  rows = sg.assign_pages_completed(
    rows, 
    rng, 
    date(2025, 12, 7)
  )

  boundary = [r for r in rows if r["_true_week_ending"] == date(2025, 12, 7) 
              and r["_session_category"] == "Enrichment"]

  assert boundary
  assert any(r["Number of Pages Completed"] is not None for r in boundary)

# =============================================================================
# Timestamp skew
# =============================================================================

cutoff_week = date(2026, 1, 25)

def test_timestamp_skew_does_not_mutate_original_rows():
  rng = sg._generate_rng(42)

  combined_schedule = sg.combine_schedules(rng, 2)
  session_rows = sg.derive_session_rows(combined_schedule)
  original_rows = deepcopy(session_rows)

  sg.inject_timestamp_skew(
    session_rows,
    sg.generate_synthesis_log_rows(
      combined_schedule, 
      cutoff_week=cutoff_week, 
      n_skipped_weeks=2
    ),
    sg._generate_rng(42),
    n_skewed_weeks=2,
  )

  assert session_rows == original_rows


def test_returned_schedule_has_the_same_number_of_rows():
  rng = sg._generate_rng(42)

  combined_schedule = sg.combine_schedules(rng, 2)
  session_rows = sg.derive_session_rows(combined_schedule)

  skewed_schedule = sg.inject_timestamp_skew(
    session_rows,
    sg.generate_synthesis_log_rows(
      combined_schedule, 
      cutoff_week=cutoff_week, 
      n_skipped_weeks=2
    ),
    sg._generate_rng(42),
    n_skewed_weeks=2,
  )

  assert len(session_rows) == len(skewed_schedule)

# =============================================================================
# Weekly narrative theme selection
# =============================================================================

def test_weekly_narrative_themes_tie_ordering():

  s01_counter = Counter({"engag": 2, "independen": 2})
  s02_counter = Counter({"engag": 2, "independen": 2})

  week_enrichment_counts = {"S01": s01_counter, "S02": s02_counter}
  week_jj_themes = {"S01": set(), "S02": set()}

  selection = sg._select_weekly_narrative_themes(week_enrichment_counts, week_jj_themes)
  cross_learner_entries = selection["all_themes"]["cross_learner"]
  theme_list = [theme for theme, _, _ in cross_learner_entries]

  assert theme_list == ["engag", "independen"]

# =============================================================================
# Weekly snapshot theme selection
# =============================================================================

def test_build_snapshot_cross_bucket_tiebreak():

  rng = sg._generate_rng(42)

  prefix = "Both learners drew on familiar strategies this week"

  selection = {
    "all_themes": {
      "cross_learner": [("familiar", 2, False)],
      "S01_individual": [("independen", 1, False)],
      "S02_individual": [("engag", 2, False)],
    },
    "top_themes": {}
  }

  snapshot = sg._build_snapshot(rng, selection)

  assert snapshot.startswith(prefix)

# =============================================================================
# Narrative field assignment
# =============================================================================

def test_assign_narrative_fields_valid_week_ending():

  rng = sg._generate_rng(42)

  synthesis_row = [{
    "week_ending": date(2026, 5, 31),
    "timestamp": datetime(2025, 12, 25, 0, 0)
  }]

  weekly_counts = {
    date(2026, 5, 31): {"S01": Counter({"engag": 2}), "S02": Counter({"engag": 2})}
  }
  weekly_jj_themes = {
    date(2026, 5, 31): {"S01": set(), "S02": set()}
  }

  result = sg.assign_narrative_fields(
    synthesis_row,
    weekly_counts,
    weekly_jj_themes,
    rng
  )

  assert result[0]["Snapshot"]


def test_assign_narrative_fields_returns_one_row_per_input_row():

  rng = sg._generate_rng(42)

  synthesis_rows = [
    {"week_ending": date(2026, 5, 31)},
    {"week_ending": date(2026, 6, 7)},
  ]

  weekly_counts = {
    date(2026, 5, 31): {"S01": Counter({"engag": 2}), "S02": Counter({"engag": 2})},
    date(2026, 6, 7): {"S01": Counter({"structure": 1}), "S02": Counter()},
  }

  weekly_jj_themes = {
    date(2026, 5, 31): {"S01": set(), "S02": set()},
    date(2026, 6, 7): {"S01": set(), "S02": set()},
  }

  result = sg.assign_narrative_fields(
    synthesis_rows,
    weekly_counts,
    weekly_jj_themes,
    rng
  )

  assert len(result) == len(synthesis_rows)


def test_assign_narrative_fields_returns_both_learners_individual_notable_shifts():

  rng = sg._generate_rng(42)

  synthesis_row = [{"week_ending": date(2026, 5, 31)}]

  weekly_counts = {
    date(2026, 5, 31): {
      "S01": Counter({"structure": 2}), 
      "S02": Counter({"familiar": 2})
    }
  }

  weekly_jj_themes = {
    date(2026, 5, 31): {"S01": set(), "S02": set()}
  }

  result = sg.assign_narrative_fields(
    synthesis_row,
    weekly_counts,
    weekly_jj_themes,
    rng
  )

  shift_narrative = result[0]["Notable Shifts or Confirmations"]
  bullets = shift_narrative.splitlines()

  assert len(bullets) == 2
  assert bullets[0].startswith("* S01") 
  assert bullets[1].startswith("* S02")

# =============================================================================
# Weekly timestamp assignment
# =============================================================================

def test_assign_synthesis_timestamp_same_seed_assigns_same_timestamp():

  rng1 = sg._generate_rng(42)
  rng2 = sg._generate_rng(42)

  synthesis_row = [{"week_ending": date(2026, 5, 31)}]

  rows1 = sg.assign_synthesis_timestamp(synthesis_row, rng1)
  rows2 = sg.assign_synthesis_timestamp(synthesis_row, rng2)

  assert rows1 == rows2


def test_assign_synthesis_timestamp_days_offset_in_both_directions():

  rng = sg._generate_rng(42)

  synthesis_rows = [
    {"week_ending": date(2026, 1, 25) + timedelta(days=7 * i)}
    for i in range(20)
  ]

  timestamped_rows = sg.assign_synthesis_timestamp(synthesis_rows, rng)

  offsets = [
    (row["timestamp"].date() - row["week_ending"]).days for row in timestamped_rows
  ]

  assert -3 <= min(offsets) < 0
  assert 0 < max(offsets) <= 3


def test_assign_synthesis_timestamp_gives_each_row_its_own_datetime_time():

  rng = sg._generate_rng(42)

  synthesis_rows = [
    {"week_ending": date(2026, 1, 25) + timedelta(days=7 * i)}
    for i in range(20)
  ]

  timestamped_rows = sg.assign_synthesis_timestamp(synthesis_rows, rng)

  assert all(isinstance(row["timestamp"], datetime) for row in timestamped_rows)

  unique_times_set = {row["timestamp"].time() for row in timestamped_rows}

  assert len(unique_times_set) == len(timestamped_rows)

# =============================================================================
# Bronze writer guardrails
# =============================================================================

def test_bronze_writer_check_ghost_cell_is_empty_and_real_cell_keeps_value(tmp_path):

  target_header = "Task Difficulty or Novelty"

  str_path = str(tmp_path/"test_data.csv")

  row: dict[str, str | None] = {internal: "test_val" for internal, _ in sg.SESSION_COLUMNS}
  row["Task Difficulty or Novelty"] = "4"
  row["Task Difficulty or Novelty.1"] = ""

  sg.write_session_csv([row], str_path)

  with open(str_path, mode="r", newline="", encoding="utf-8") as file:
    reader = csv.reader(file)
    parsed_rows = list(reader)

  duplicate_header_count = parsed_rows[0].count(target_header)

  indices = [index for index, header in enumerate(parsed_rows[0]) if header == target_header]

  assert duplicate_header_count == 2
  assert parsed_rows[1][indices[0]] == "4"
  assert parsed_rows[1][indices[1]] == ""


def test_bronze_writer_raises_KeyError_with_missing_internal_key_from_row(tmp_path):

  str_path = str(tmp_path/"test_data.csv")

  row: dict[str, str | None] = {internal: "test_val" for internal, _ in sg.SESSION_COLUMNS}
  del row["observer_id"]

  with pytest.raises(KeyError) as excinfo:
    sg.write_session_csv([row], str_path)

  assert "observer_id" in str(excinfo.value)
  assert "Observer ID" in str(excinfo.value)


def test_bronze_writer_allows_key_holding_None_and_writes_empty_cell(tmp_path):

  real_header = "Resilience (Response to Mistakes or Corrections)"

  str_path = str(tmp_path/"test_data.csv")

  row: dict[str, str | None] = {internal: "test_val" for internal, _ in sg.SESSION_COLUMNS}
  row["Resilience"] = None

  sg.write_session_csv([row], str_path)

  with open(str_path, mode="r", newline="", encoding="utf-8") as file:
    reader = csv.reader(file)
    parsed_rows = list(reader)

  assert len(parsed_rows[1]) == len(sg.SESSION_COLUMNS)
  assert parsed_rows[1][parsed_rows[0].index(real_header)] == ""


def test_write_session_csv_header_rows_match_expected_result(tmp_path):

  str_path = str(tmp_path/"test_data.csv")

  row: dict[str, str | None] = {internal: "test_val" for internal, _ in sg.SESSION_COLUMNS}

  sg.write_session_csv([row], str_path)

  with open(str_path, mode="r", newline="", encoding="utf-8") as file:
    reader = csv.reader(file)
    parsed_headers = list(reader)[0]

  assert parsed_headers == SESSION_HEADERS


def test_write_synthesis_csv_header_rows_match_expected_result(tmp_path):

  str_path = str(tmp_path/"test_data.csv")

  row: dict[str, str | None] = {internal: "test_val" for internal, _ in sg.SYNTHESIS_COLUMNS}

  sg.write_synthesis_csv([row], str_path)

  with open(str_path, mode="r", newline="", encoding="utf-8") as file:
    reader = csv.reader(file)
    parsed_headers = list(reader)[0]

  assert parsed_headers == SYNTHESIS_HEADERS


def test_write_synthesis_csv_writes_each_value_under_its_own_header(tmp_path):

  str_path = str(tmp_path/"test_data.csv")

  row: dict[str, str | None] = {internal: "test_val" for internal, _ in reversed(sg.SYNTHESIS_COLUMNS)}

  row["Column 11"] = None
  row["Column 10"] = None
  row["Column 12"] = None
  row["JJ Observed"] = "S01, S02"
  row["Private Lessons"] = "S02"

  sg.write_synthesis_csv([row], str_path)

  with open(str_path, mode="r", newline="", encoding="utf-8") as file:
    reader = csv.reader(file)
    parsed_rows = list(reader)

  assert len(parsed_rows[1]) == len(SYNTHESIS_HEADERS)
  assert parsed_rows[1][parsed_rows[0].index("Column 11")] == ""
  assert parsed_rows[1][parsed_rows[0].index("Column 10")] == ""
  assert parsed_rows[1][parsed_rows[0].index("Column 12")] == ""

  jj_observed_header = "If Jiu-Jitsu sessions were observed, for which learner(s)?"
  jj_private_header = "Select any learner(s) that take at least one weekly private lessons in Jiu-Jitsu."

  assert parsed_rows[1][parsed_rows[0].index(jj_observed_header)] == "S01, S02"
  assert parsed_rows[1][parsed_rows[0].index(jj_private_header)] == "S02"

# =============================================================================
# Phase lookup
# =============================================================================

BEFORE_FIRST_PHASE = date(1999, 12, 25)
FIRST_PHASE_START = date(2000, 1, 1)
FIRST_PHASE_WEIGHTS = {"MathQuest KA Textbook": 3}
SECOND_PHASE_START = date(2000, 2, 1)
SECOND_PHASE_WEIGHTS = {"MathQuest PKA Textbook": 4}

PHASES = [
  (FIRST_PHASE_START, FIRST_PHASE_WEIGHTS),
  (SECOND_PHASE_START, SECOND_PHASE_WEIGHTS),
]


def test_find_phase_raises_ValueError_if_date_is_before_earliest_phase():

  with pytest.raises(ValueError) as excinfo:
    sg._find_phase(PHASES, BEFORE_FIRST_PHASE)

  assert repr(BEFORE_FIRST_PHASE) in str(excinfo.value)
  assert repr(FIRST_PHASE_START) in str(excinfo.value)


def test_find_phase_returns_first_phase_weights_on_its_start_date():

  assert sg._find_phase(PHASES, FIRST_PHASE_START) == FIRST_PHASE_WEIGHTS
  assert sg._find_phase(PHASES, SECOND_PHASE_START) == SECOND_PHASE_WEIGHTS
