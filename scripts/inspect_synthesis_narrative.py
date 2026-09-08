from collections import Counter
import numpy as np

from src.generator.synthesis_narrative import (
  _select_weekly_narrative_themes, 
  _build_snapshot, 
  _build_shift_bullet, 
  _build_learning_mechanism
)

def inspect_weekly_narrative(selection):
  print("=" * 60)
  print("THEME SELECTION")
  print("=" * 60)

  all_themes = selection["all_themes"]
  top_themes = selection["top_themes"]

  for bucket, entries in all_themes.items():
    print(f"\n{bucket}:")
    for theme, score, has_jj in entries:
      print(
        f"  {theme:<15} "
        f"score={score:<3} "
        f"JJ={has_jj}"
      )

  print("\n" + "-" * 60)
  print("TOP THEMES")
  print("-" * 60)

  for bucket, entries in top_themes.items():
    print(f"\n{bucket}:")
    for entry in entries:
      print(f"  {entry}")

rng = np.random.default_rng(42)

week_enrichment_counts = {
  "S01": Counter({
    "flexib": 4,
    "engag": 3,
    "structure": 2,
  }),
  "S02": Counter({
    "flexib": 3,
    "motivat": 2,
    "familiar": 2,
  }),
}

week_jj_themes = {
  "S01": {"flexib", "structure"},
  "S02": {"motivat"},
}

selection = _select_weekly_narrative_themes(
  week_enrichment_counts,
  week_jj_themes,
)

inspect_weekly_narrative(selection)

print("\n" + "-" * 60)
print("SNAPSHOT")
print("-" * 60)

snapshot = _build_snapshot(rng, selection)

print(snapshot)

print("\n" + "-" * 60)
print("NOTABLE SHIFTS OR CONFIRMATIONS")
print("-" * 60)

week_top_score = max(
  entry[1]
  for entries in selection["all_themes"].values()
  for entry in entries
)

for student in ["S01", "S02"]:
  entries = selection["all_themes"][f"{student}_individual"]

  if not entries:
    continue

  theme, score, has_jj = entries[0]

  notable_shift = _build_shift_bullet(
    rng,
    theme=theme,
    score=score,
    has_jj=has_jj,
    bucket_type="individual",
    week_top_score=week_top_score,
    student=student,
  )

  print(notable_shift)

print("\n" + "-" * 60)
print("LEARNING MECHANISMS OBSERVED")
print("-" * 60)

learning_mechanisms = _build_learning_mechanism(rng, selection)

print(learning_mechanisms)