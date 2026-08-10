from datetime import date

from src import synthetic_generator as sg


def main():

  seed = 44
  rng = sg._generate_rng(seed)

  schedule = sg.combine_schedules(rng, 2)

  print("\nPipeline inspection")

  rows = sg.derive_session_rows(schedule)

  print("\nRows:", len(rows))
  print("\nAfter derive_session_rows")
  for row in rows[:3]:
    print(row)

  # =============================================================================
  # Observation context
  # =============================================================================

  cutoff_week = date(2026, 1, 25)

  rows = sg.assign_observation_context(
    rows, 
    rng, 
    cutoff_week,
  )

  print("\nRows around observation context:")

  for row in rows:
    if abs((row["true_week_ending"] - cutoff_week).days) <= 7:
      print(
        row["true_week_ending"],
        row["observation_context"],
      )

  # =============================================================================
  # Observer ID
  # =============================================================================

  transition_week = date(2025, 12, 14)

  rows = sg.assign_observer_id(
    rows, 
    transition_week,
  )

  print("\nRows around observer transition:")

  for row in rows:
    if abs((row["true_week_ending"] - transition_week).days) <= 7:
      print(
        row["true_week_ending"],
        row["student_id"],
        row["observer_id"],
      )

  # =============================================================================
  # Core ratings
  # =============================================================================

  rows = sg.assign_core_ratings(
    rows, 
    rng,
  )

  print("\nAfter core ratings")

  for row in rows[:3]:
    print(row)

  # =============================================================================
  # Secondary ratings
  # =============================================================================

  rows = sg.assign_secondary_ratings(
    rows, 
    rng,
  )

  print("\nAfter secondary ratings")

  for row in rows[:3]:
    print(row)

  # =============================================================================
  # Deprecated ratings
  # =============================================================================

  cutoff_week = date(2026, 1, 25)

  rows = sg.assign_deprecated_ratings(
    rows, 
    rng, 
    cutoff_week,
  )

  print("\nRows around deprecated ratings:")

  for row in rows:
    if abs((row["true_week_ending"] - cutoff_week).days) <= 7:
      print(
        row["true_week_ending"],
        row["Coordination and Motor Skills"],
        row["Social Regulation"],
      )

  print("\nFirst three rows after deprecated ratings:")

  for row in rows[:3]:
    print(row)

  # =============================================================================
  # Pages completed
  # =============================================================================

  cutoff_week = date(2025, 12, 7)

  rows = sg.assign_pages_completed(
    rows,
    rng,
    cutoff_week,
  )

  print("\nEarly-season pages:")

  for row in rows:
    if (
      row["session_category"] == "Enrichment"
      and row["true_week_ending"] <= date(2025, 9, 21)
    ):
      print(
        row["true_week_ending"],
        row["student_id"],
        row["Number of Pages Completed"],
      )
  
  print("\nLate-season pages:")

  for row in rows:
    if (
      row["session_category"] == "Enrichment"
      and row["true_week_ending"] >= date(2026, 5, 17)
    ):
      print(
        row["true_week_ending"],
        row["student_id"],
        row["Number of Pages Completed"],
      )

  # =============================================================================
  # Task difficulty
  # =============================================================================

  cutoff_week = date(2026, 1, 25)

  rows = sg.assign_task_difficulty(
    rows,
    rng,
    cutoff_week,
  )
  
  print("\nRows around task difficulty ratings:")

  for row in rows:
    if abs((row["true_week_ending"] - cutoff_week).days) <= 7:
      print(
        row["true_week_ending"],
        row["session_category"],
        row["Task Difficulty or Novelty"],
      )

  print("\nFirst three rows after task difficulty:")

  for row in rows[:3]:
    print(row)

  # =============================================================================
  # Duration
  # =============================================================================

  cutoff_week = date(2025, 12, 14)
  phase_shift_week = date(2026, 2, 15)

  rows = sg.assign_duration(
    rows,
    rng,
    cutoff_week,
    phase_shift_week,
  )

  print("\nRows around when duration gets logged:")

  for row in rows:
    if abs((row["true_week_ending"] - cutoff_week).days) <= 7:
      print(
        row["true_week_ending"],
        row["session_category"],
        row["Duration in Minutes"],
      )

  print("\nFirst three rows after duration:")

  for row in rows[:3]:
    print(row)

  print("\nRows around when duration changes:")

  for row in rows:
    if abs((row["true_week_ending"] - phase_shift_week).days) <= 7:
      print(
        row["true_week_ending"],
        row["session_category"],
        row["Duration in Minutes"],
      )

  # =============================================================================
  # Primary task type
  # =============================================================================

  cutoff_week = date(2026, 4, 5)

  rows = sg.assign_primary_task_type(
    rows,
    rng,
    cutoff_week,
  )

  print("\nRows around when task types are recorded:")

  for row in rows:
    if abs((row["true_week_ending"] - cutoff_week).days) <= 7:
      print(
        row["true_week_ending"],
        row["session_category"],
        row["Primary Task Type"],
      )

  print("\nFirst three rows after primary task types:")

  for row in rows[:3]:
    print(row)

  # =============================================================================
  # Published materials
  # =============================================================================

  cutoff_week = date(2025, 12, 14)

  rows = sg.assign_published_materials_used(
    rows,
    rng,
    cutoff_week,
  )

  print("\nRows around when books are recorded:")

  for row in rows:
    if abs((row["true_week_ending"] - cutoff_week).days) <= 7:
      print(
        row["true_week_ending"],
        row["student_id"],
        row["Published Materials Used"],
      )

  print("\nFirst three rows after published materials:")

  for row in rows[:3]:
    print(row)

  # =============================================================================
  # Puzzle types
  # =============================================================================

  cutoff_week = date(2026, 3, 22)
  primary_task_type_cutoff_week = date(2026, 4, 5)

  rows = sg.assign_puzzle_type(
    rows,
    rng,
    cutoff_week,
    primary_task_type_cutoff_week,
  )

  print("\nRows around when puzzle types are recorded:")

  for row in rows:
    if (
      row["session_category"] == "Enrichment"
      and date(2026, 3, 15) <= row["true_week_ending"] <= date(2026, 4, 19)
    ):
      print(
        row["true_week_ending"],
        row["student_id"],
        row["Primary Task Type"],
        row["Puzzle Type"],
      )


if __name__ == "__main__":
  main()