from synthetic_generator import (
  START,
  END,
  _generate_rng,
  generate_jiu_jitsu_observations,
  combine_schedules,
  derive_session_rows
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