from copy import deepcopy
from datetime import date

from src import synthetic_generator as sg


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
  rows = sg.derive_session_rows(
    sg.combine_schedules(42, 2)
  )

  assert len(rows) == 169


def test_same_seed_produces_same_rows():
  rows1 = sg.derive_session_rows(
    sg.combine_schedules(42, 2)
  )
  rows2 = sg.derive_session_rows(
    sg.combine_schedules(42, 2)
  )
  
  assert rows1 == rows2


# =============================================================================
# Observer assignment
# =============================================================================


def test_assign_observer_id_does_not_mutate_input():
  session_rows = sg.derive_session_rows(
    sg.combine_schedules(42, 2)
  )

  original_rows = [
    row.copy()
    for row in session_rows
  ]

  sg.assign_observer_id(
    session_rows,
    date(2025, 12, 7)
  )

  assert session_rows == original_rows


def test_observer_id_shifts_at_transition_week():
  session_rows = sg.derive_session_rows(
    sg.combine_schedules(42, 2)
  )

  transition_week = date(2025, 12, 7)

  rows1 = sg.assign_observer_id(session_rows, transition_week)

  for row in rows1:
    if row["true_week_ending"] < transition_week:
      assert row["observer_id"] == "T0"
    else:
      assert row["observer_id"] == "T01"

  rows2 = sg.assign_observer_id(session_rows, transition_week)

  assert rows1 == rows2


# =============================================================================
# Observation context assignment
# =============================================================================


def test_assign_observation_context_does_not_mutate_input():
  session_rows = sg.derive_session_rows(
    sg.combine_schedules(42, 2)
  )

  original_rows = [
    row.copy()
    for row in session_rows
  ]

  sg.assign_observation_context(
    session_rows,
    sg._generate_rng(42),
  )

  assert session_rows == original_rows


def test_enrichment_rows_from_same_meeting_share_context():
  session_rows = sg.derive_session_rows(
    sg.combine_schedules(42, 2)
  )

  assigned_rows = sg.assign_observation_context(
    session_rows,
    sg._generate_rng(42),
  )

  contexts_by_timestamp = {}

  for row in assigned_rows:
    if row["session_category"] == "Jiu-Jitsu":
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


def test_assign_observation_context_preserves_session_category():
  session_rows = sg.derive_session_rows(
    sg.combine_schedules(42, 2)
  )

  assigned_rows = sg.assign_observation_context(
    session_rows,
    sg._generate_rng(42),
  )

  for original, assigned in zip(session_rows, assigned_rows):
    if original["session_category"] == "Jiu-Jitsu":
      assert assigned["session_category"] == "Jiu-Jitsu"


def test_assign_observation_context_preserves_jiu_jitsu_context():
  session_rows = sg.derive_session_rows(
    sg.combine_schedules(42, 2)
  )

  assigned_rows = sg.assign_observation_context(
    session_rows,
    sg._generate_rng(42),
  )

  for original, assigned in zip(session_rows, assigned_rows):
    if original["session_category"] == "Jiu-Jitsu":
      assert(
        assigned["observation_context"] == "Jiu-Jitsu"
      )


# =============================================================================
# Core ratings
# =============================================================================


def test_assign_core_ratings_does_not_mutate_input():
  session_rows = sg.derive_session_rows(
    sg.combine_schedules(42, 2)
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
  session_rows = sg.derive_session_rows(
    sg.combine_schedules(42, 2)
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
  session_rows = sg.derive_session_rows(
    sg.combine_schedules(42, 2)
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
  session_rows = sg.derive_session_rows(
    sg.combine_schedules(42, 2)
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
  session_rows = sg.derive_session_rows(
    sg.combine_schedules(42, 2)
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
  session_rows = sg.derive_session_rows(
    sg.combine_schedules(42, 2)
  )

  assigned_rows = sg.assign_core_ratings(
    session_rows,
    sg._generate_rng(42),
  )

  for original, assigned in zip(session_rows, assigned_rows):
    assert original["student_id"] == assigned["student_id"]
    assert original["timestamp"] == assigned["timestamp"]
    assert original["session_category"] == assigned["session_category"]
    assert original["observation_context"] == assigned["observation_context"]

      
# =============================================================================
# Timestamp skew
# =============================================================================


def test_timestamp_skew_does_not_mutate_original_rows():
  session_rows = sg.derive_session_rows(
    sg.combine_schedules(42, 2)
  )
  original_rows = deepcopy(session_rows)

  combined_schedule = sg.combine_schedules(42, 2)

  sg.inject_timestamp_skew(
    session_rows,
    sg.generate_synthesis_log_rows(combined_schedule, 2),
    sg._generate_rng(42),
    n_skewed_weeks=2,
  )

  assert session_rows == original_rows


def test_returned_schedule_has_the_same_number_of_rows():
  session_rows = sg.derive_session_rows(
    sg.combine_schedules(42, 2)
  )

  combined_schedule = sg.combine_schedules(42, 2)

  skewed_schedule = sg.inject_timestamp_skew(
    session_rows,
    sg.generate_synthesis_log_rows(combined_schedule, 2),
    sg._generate_rng(42),
    n_skewed_weeks=2,
  )

  assert len(session_rows) == len(skewed_schedule)