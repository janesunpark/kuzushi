from collections import Counter
import numpy as np

from src.generator.synthesis_narrative import _select_weekly_narrative_themes, _build_snapshot

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
