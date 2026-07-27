from synthetic_generator import (
  START,
  END,
  _generate_rng,
  generate_jiu_jitsu_observations,
  combine_schedules,
  derive_session_rows,
  inject_timestamp_skew,
)


def test_same_seed_same_output():
  rng1 = _generate_rng(42)
  rng2 = _generate_rng(42)

  assert(
    generate_jiu_jitsu_observations(START, END, rng1)
    ==
    generate_jiu_jitsu_observations(START, END, rng2)
  )


def test_shared_rng_advances_state():
  rng = _generate_rng(42)

  first = generate_jiu_jitsu_observations(START, END, rng)
  second = generate_jiu_jitsu_observations(START, END, rng)

  assert first != second


def test_same_seed_expected_row_count():
  row = derive_session_rows(
    combine_schedules(42, 2)
  )
  assert len(row) == 169


def test_same_seed_produces_same_rows():
  rows1 = derive_session_rows(
    combine_schedules(42, 2)
  )
  rows2 = derive_session_rows(
    combine_schedules(42, 2)
  )
  assert rows1 == rows2


from copy import deepcopy

def test_timestamp_skew_does_not_mutate_original_rows():
  session_rows = derive_session_rows(
    combine_schedules(42, 2)
  )
  original_rows = deepcopy(session_rows)

  rng = _generate_rng(42)

  inject_timestamp_skew(
    session_rows,
    rng,
    n_skewed_weeks=2,
  )

  assert session_rows == original_rows


def test_returned_schedule_has_the_same_number_of_rows():
  session_rows = derive_session_rows(
    combine_schedules(42, 2)
  )

  skewed_schedule = inject_timestamp_skew(
    session_rows,
    _generate_rng(42),
    n_skewed_weeks=2,
  )

  assert len(session_rows) == len(skewed_schedule)


  