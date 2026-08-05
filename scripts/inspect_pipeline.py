from src import synthetic_generator as sg

from datetime import date

def main():

  seed = 42
  rng = sg._generate_rng(seed)

  schedule = sg.combine_schedules(rng, 2)

  print("\nPipeline inspection")

  rows = sg.derive_session_rows(schedule)
  print("\nRows:", len(rows))
  print("\nAfter derive_session_rows")
  for row in rows[:3]:
     print(row)

  rows = sg.assign_observation_context(rows, rng, date(2026, 1, 25))
  transition = date(2026, 1, 25)

  print("\nRows around observation context:")
  for row in rows:
      if abs((row["true_week_ending"] - transition).days) <= 7:
          print(
              row["true_week_ending"],
              row["observation_context"],
          )

  rows = sg.assign_observer_id(rows, date(2025, 12, 7))
  transition = date(2025, 12, 7)

  print("\nRows around observer transition:")
  for row in rows:
      if abs((row["true_week_ending"] - transition).days) <= 7:
          print(
              row["true_week_ending"],
              row["student_id"],
              row["observer_id"],
          )

  rows = sg.assign_core_ratings(rows, rng)
  print("\nAfter core ratings")
  for row in rows[:3]:
     print(row)

  rows = sg.assign_secondary_ratings(rows, rng)
  print("\nAfter secondary ratings")
  for row in rows[:3]:
     print(row)

  rows = sg.assign_deprecated_ratings(rows, rng, date(2026, 1, 25))
  transition = date(2026, 1, 25)
  
  print("\nRows around deprecated ratings:")
  for row in rows:
      if abs((row["true_week_ending"] - transition).days) <= 7:
          print(
              row["true_week_ending"],
              row["Coordination and Motor Skills"],
              row["Social Regulation"],
          )

  print(rows[:3])


  rows = sg.assign_pages_completed(rows, rng, date(2025, 12, 7))
  transition = date(2025, 12, 7)

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


if __name__ == "__main__":
  main()