from datetime import date

from src.generator._helpers import _generate_rng
from src.generator.schedule_generation import (
  combine_schedules,
  derive_session_rows,
  generate_synthesis_log_rows,
  inject_timestamp_skew,
)
from src.generator.session_enrichment import (
  assign_observation_context,
  assign_observer_id,
  assign_core_ratings,
  assign_secondary_ratings,
  assign_deprecated_ratings,
  assign_pages_completed,
  assign_task_difficulty,
  assign_duration,
  assign_primary_task_type,
  assign_published_materials_used,
  assign_puzzle_type,
  assign_puzzle_challenge,
  assign_session_context_fields,
  assign_static_null_fields,
  assign_notes,
)
from src.generator.synthesis_enrichment import (
  assign_synthesis_static_fields,
  assign_jj_synthesis_fields,
  summarize_weekly_notes_themes,
)
from src.generator.synthesis_narrative import (
  assign_narrative_fields,
  assign_synthesis_timestamp,
)

FORM_UPDATE_1_WEEK = date(2025, 12, 14)
FORM_UPDATE_2_WEEK = date(2026, 1, 25)
ASSIGN_PAGES_WEEK = date(2025, 12, 7)
DURATION_SHIFT_WEEK = date(2026, 2, 15)
PUZZLE_START_WEEK = date(2026, 3, 22)
PRIMARY_TASK_WEEK = date(2026, 4, 5)
RANDOM_OFF_WEEKS = 2

SYNTHESIS_START_WEEK = date(2026, 1, 25)
JJ_SYNTHESIS_WEEK = date(2026, 2, 22)
SYNTHESIS_SKIPPED_WEEKS = 2
TIMESTAMP_SKEWED_WEEKS = 2


def generate_synthetic_logs(seed: int) -> tuple[list[dict], list[dict]]:

  rng = _generate_rng(seed)
  schedule = combine_schedules(rng, RANDOM_OFF_WEEKS)

  session_rows = derive_session_rows(schedule)
  session_rows = assign_observation_context(session_rows, rng, FORM_UPDATE_2_WEEK)
  session_rows = assign_observer_id(session_rows, FORM_UPDATE_1_WEEK)
  session_rows = assign_core_ratings(session_rows, rng)
  session_rows = assign_secondary_ratings(session_rows, rng)
  session_rows = assign_deprecated_ratings(session_rows, rng, FORM_UPDATE_2_WEEK)
  session_rows = assign_pages_completed(session_rows, rng, ASSIGN_PAGES_WEEK)
  session_rows = assign_task_difficulty(session_rows, rng, FORM_UPDATE_2_WEEK)
  session_rows = assign_duration(session_rows, rng, cutoff_week=FORM_UPDATE_1_WEEK, phase_shift_week=DURATION_SHIFT_WEEK)
  session_rows = assign_primary_task_type(session_rows, rng, PRIMARY_TASK_WEEK)
  session_rows = assign_published_materials_used(session_rows, rng, FORM_UPDATE_1_WEEK)
  session_rows = assign_puzzle_type(session_rows, rng, cutoff_week=PUZZLE_START_WEEK, primary_task_type_cutoff_week=PRIMARY_TASK_WEEK)
  session_rows = assign_puzzle_challenge(session_rows, rng)
  session_rows = assign_session_context_fields(session_rows, rng, FORM_UPDATE_1_WEEK)
  session_rows = assign_static_null_fields(session_rows)
  session_rows = assign_notes(session_rows, rng)

  synthesis_rows = generate_synthesis_log_rows(schedule, cutoff_week=SYNTHESIS_START_WEEK, n_skipped_weeks=SYNTHESIS_SKIPPED_WEEKS)
  synthesis_rows = assign_synthesis_static_fields(synthesis_rows)
  synthesis_rows = assign_jj_synthesis_fields(synthesis_rows, rng, JJ_SYNTHESIS_WEEK)
  weekly_counts, weekly_jj_themes = summarize_weekly_notes_themes(session_rows)
  synthesis_rows = assign_narrative_fields(synthesis_rows, weekly_counts, weekly_jj_themes, rng)
  synthesis_rows = assign_synthesis_timestamp(synthesis_rows, rng)
  session_rows = inject_timestamp_skew(session_rows, synthesis_rows, rng, TIMESTAMP_SKEWED_WEEKS)

  return session_rows, synthesis_rows