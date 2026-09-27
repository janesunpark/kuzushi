from datetime import date

from src.generator._helpers import _generate_rng
from src.generator.schedule_generation import (
    combine_schedules,
    derive_session_rows,
    generate_synthesis_log_rows,
)
from src.generator.session_enrichment import (
    assign_observation_context,
    assign_observer_id,
    assign_core_ratings,
    assign_secondary_ratings,
    assign_primary_task_type,
    assign_puzzle_type,
    assign_notes,
)
from src.generator.synthesis_enrichment import (
    assign_synthesis_static_fields,
    assign_jj_synthesis_fields,
    summarize_weekly_notes_themes,
)
from src.generator.synthesis_narrative import (
    _select_weekly_narrative_themes,
    assign_narrative_fields,
    assign_synthesis_timestamp,
)

NARRATIVE_FIELDS = [
    "Snapshot",
    "Notable Shifts or Confirmations",
    "Learning Mechanisms Observed",
    "Optional: Data Flags (If Relevant)",
]


def inspect_theme_selection(
    weekly_counts,
    weekly_jj_themes,
    week
): 
    print("=" * 60)
    print(f"THEME SELECTION - week {week}")
    print("=" * 60)

    selection = _select_weekly_narrative_themes(
        weekly_counts[week],
        weekly_jj_themes.get(week, {})
    )

    for bucket, entries in selection["all_themes"].items():
        print(f"\n{bucket}:")
        for theme, score, has_jj in entries:
            print(f" {theme:<15} score={score:<3} JJ={has_jj}")


def inspect_narrative_row(row):
    print("\n" + "-" * 60)
    print(f"SYNTHESIS ROW - week {row['week_ending']}")
    print("-" * 60)
    for field in NARRATIVE_FIELDS:
        print(f"\n--- {field} ---")
        print(row[field] if row[field] else "(empty)")


def main():
    seed = 42
    rng = _generate_rng(seed)

    schedule = combine_schedules(rng, 2)
    rows = derive_session_rows(schedule)
    rows = assign_observation_context(rows, rng, date(2026, 1, 25))
    rows = assign_observer_id(rows, date(2025, 12, 14))
    rows = assign_core_ratings(rows, rng)
    rows = assign_secondary_ratings(rows, rng)
    rows = assign_primary_task_type(rows, rng, date(2026, 4, 5))
    rows = assign_puzzle_type(rows, rng, date(2026, 3, 22), date(2026, 4, 5))
    rows = assign_notes(rows, rng)

    weekly_counts, weekly_jj_themes = summarize_weekly_notes_themes(rows)

    synthesis_cutoff = date(2026, 1, 25)
    synthesis_rows = generate_synthesis_log_rows(
        schedule,
        synthesis_cutoff,
        2
    )
    synthesis_rows = assign_synthesis_static_fields(synthesis_rows)
    synthesis_rows = assign_jj_synthesis_fields(synthesis_rows, rng, date(2026, 2, 22))

    print(f"Synthesis rows before narrative fields: {len(synthesis_rows)}\n")

    synthesis_rows = assign_narrative_fields(
        synthesis_rows, weekly_counts, weekly_jj_themes, rng
    )

    print(f"Synthesis rows after narrative fields: {len(synthesis_rows)}\n")

    # Inspect the first two weeks: theme selection alongside the actual field output, so it's visible which theme drove which sentences.
    for row in synthesis_rows[:5]:
        inspect_theme_selection(weekly_counts, weekly_jj_themes, row["week_ending"])
        inspect_narrative_row(row)

    
if __name__ == "__main__":
    main()