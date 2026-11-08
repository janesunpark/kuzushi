from datetime import date
import pytest

from src.generator.pipeline import generate_synthetic_logs

def test_same_seed_same_logs():
  assert generate_synthetic_logs(42) == generate_synthetic_logs(42)


def test_different_seed_different_logs():
  assert generate_synthetic_logs(42) != generate_synthetic_logs(44)

@pytest.mark.parametrize("seed", [42, 1, 2, 17])
def test_weekly_counts_match_session_rows(seed):

  session_rows, synthesis_rows = generate_synthetic_logs(seed)
  assert synthesis_rows
  
  timestamp_dict = {}
  for row in session_rows:
    if row["_session_category"] == "Enrichment":
      week = row["_true_week_ending"]
      if week not in timestamp_dict:
        timestamp_dict[week] = set()
      timestamp_dict[week].add(row["timestamp"])

  for weekly_row in synthesis_rows:
    week = weekly_row["week_ending"]
    assert len(timestamp_dict.get(week, set())) == weekly_row["num_sessions_reported"], week


def test_december_form_fields_are_filled():

  START_DATE = date(2025, 12, 14)
  END_DATE = date(2026, 1, 25)
  session_rows, synthesis_rows = generate_synthetic_logs(42)
  matched = 0

  for row in session_rows:
    if START_DATE <= row["_true_week_ending"] < END_DATE:
      if row["_session_category"] == "Enrichment":
        matched += 1

        assert row["observer_id"] == "T01"
        assert row["Duration in Minutes"] is not None
        assert row["Published Materials Used"] is not None, row["_session_category"]
        assert row["Emotional Tone of Teacher"] is not None
        assert row["Parent Interaction"] is not None
        assert row["Environment or Disruptions"] is not None

  assert matched > 0