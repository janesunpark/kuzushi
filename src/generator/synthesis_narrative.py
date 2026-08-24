from collections import Counter
import numpy as np


THEME_PHRASES = {
  "familiar": {
    "individual": "{student} continued to lean on familiar entry points and previously successful approaches when starting new tasks",
    "cross_learner": "both learners drew on familiar strategies this week, though each anchored to a different kind of familiarity",
  },
  "flexib": {
    "individual": "{student} showed flexibility by adjusting approach midway through a task when the first strategy wasn't working",
    "cross_learner": "both learners made strategic adjustments to complete tasks, demonstrating an emerging sense of cognitive flexibility",
  },
  "independen": {
    "individual": "{student} showed increased autonomy by requesting to complete the task independently",
    "cross_learner": "both learners worked independently on their own tasks and completed them with minimal support",
  },
  "engag": {
    "individual": "{student} sustained engagement across longer task sequences",
    "cross_learner": "both learners showed sustained engagement this week, with attention holding through longer stretches of task time",
  },
  "motivat": {
    "individual": "{student} stayed motivated to take on additional work, despite it being more challenging",
    "cross_learner": "both learners showed increased participation in response to external sources of motivation, such as visible markers of achievement and prizes",
  },
  "structure": {
    "individual": "{student} brought a clear structure to multi-step tasks, working through them in a self-directed order",
    "cross_learner": "both learners brought their own structure to multi-step tasks, though how each broke the steps down differed",
  },
  "spatial_pattern": {
    "individual": "{student} correctly extended the geometric pattern",
    "cross_learner": "both learners grasped the underlying spatial patterns in geometric puzzles by actively manipulating the shapes to complete tasks",
  },
}

FRAMING_CLAUSES = {
  "confirmed": [
    "continuing a trend that has held across recent weeks",
    "consistent with what recent sessions have shown",
  ],
  "shift": [
    "an inclination that had not been as prominent earlier this season",
    "an emerging tendency worth continuing to watch",
  ],
}

JJ_ADDENDUM = ", a behavior also noted during this week's Jiu-Jitsu observation, though still treated as a preliminary, single-week signal across contexts rather than confirmed transfer"


def _select_weekly_narrative_themes(
    week_enrichment_counts: dict[str, Counter],
    week_jj_themes: dict[str, set],
) -> dict:

  cross_learner_raw = []
  s01_individual_raw = []
  s02_individual_raw = []

  s01_counter = week_enrichment_counts["S01"]
  s02_counter = week_enrichment_counts["S02"]
  s01_jj = week_jj_themes.get("S01", set())
  s02_jj = week_jj_themes.get("S02", set())

  all_theme_names = set(s01_counter) | set(s02_counter)

  for theme in all_theme_names:
    in_s01 = theme in s01_counter
    in_s02 = theme in s02_counter

    if in_s01 and in_s02:
      score = min(s01_counter[theme], s02_counter[theme])
      has_jj = theme in s01_jj or theme in s02_jj
      cross_learner_raw.append((theme, score, has_jj))

    elif in_s01:
      s01_individual_raw.append((theme, s01_counter[theme], theme in s01_jj))
    else:
      s02_individual_raw.append((theme, s02_counter[theme], theme in s02_jj))

  def _rank(bucket):
    return sorted(bucket, key=lambda entry: (entry[1], entry[2]), reverse=True)

  all_themes = {
    "cross_learner": _rank(cross_learner_raw),
    "S01_individual": _rank(s01_individual_raw),
    "S02_individual": _rank(s02_individual_raw),
  }

  top_themes = {
    bucket: entries[:2]
    for bucket, entries in all_themes.items()
  }

  return {"all_themes": all_themes, "top_themes": top_themes}


def _build_shift_bullet(
    rng: np.random.Generator,
    theme,
    score,
    has_jj,
    bucket_type,
    week_top_score,
    student=None
): 
  is_strong = score >= 0.5 * week_top_score and score >=2
  framing = rng.choice(FRAMING_CLAUSES["confirmed" if is_strong else "shift"])

  phrase = THEME_PHRASES[theme][bucket_type]
  if bucket_type == "individual":
    phrase = phrase.format(student=student)

  bullet = f"{phrase[0].upper()}{phrase[1:]}, {framing}"
  if has_jj:
    bullet += JJ_ADDENDUM

  return bullet + "."