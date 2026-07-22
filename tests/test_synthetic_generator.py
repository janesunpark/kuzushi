from synthetic_generator import (
  START,
  END,
  _generate_rng,
  generate_jiu_jitsu_observations,
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