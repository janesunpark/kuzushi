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
    "individual": "{student} stayed motivated to take on additional work despite it being more challenging",
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

JJ_ADDENDUM = "This is a behavior also noted during this week's Jiu-Jitsu observation, though still treated as a preliminary, single-week signal across contexts rather than confirmed transfer"

CONNECTOR_PHRASES = {
  "connector": ["Specifically,", "For example,", "For instance,"]
}

LEARNING_MECHANISM_PHRASES = {
  "familiar": {
    "individual": "{student}'s learning mechanism relied on familiar visual cues and working around them, suggesting that familiarity can serve as a strategic entry point in problem-solving",
    "cross_learner": "Both learners appeared to rely on familiar problem-solving approaches, particularly in unfamiliar tasks. This suggests a developing strategy that stems from recognizing familiar patterns and constraints",
  },
  "flexib": {
    "individual": "{student} showed improved cognitive flexibility, suggesting growing openness toward strategic adjustments mid-task",
    "cross_learner": "Both learners showed flexible reasoning by maneuvering a step that they found challenging in prior sessions, suggesting greater flexibility in problem-solving contexts",
  },
  "independen": {
    "individual": "{student} showed a preference for independent exploration of concepts, suggesting a growing sense of autonomy",
    "cross_learner": "Both learners completed tasks independently across a variety of materials and challenge levels. Prior success in independent task completion appears to support confidence, initiative, and willingness to follow through on increasingly challenging tasks",
  },
  "engag": {
    "individual": "{student} showed stable session flow from worksheet engagement to play, suggesting that engagement level in one task type does not necessarily impede engagement in another",
    "cross_learner": "Both learners preferred different approaches to task engagement, suggesting that learner-specific pathways may impact individual patterns of engagement",
  },
  "motivat": {
    "individual": "{student} showed competitive motivation, suggesting that comparison dynamics may encourage task completion",
    "cross_learner": "Both learners showed sensitivity toward different motivational markers, suggesting that unique motivational preferences may contribute to learner-specific pathways",
  },
  "structure": {
    "individual": "{student} sought creative problem-solving approaches within structured materials, suggesting that appropriate, skill-based structure can provide opportunities for exploratory learning",
    "cross_learner": "Both learners spontaneously extended learned structures, suggesting a growing interest in exploratory application",
  },
  "spatial_pattern": {
    "individual": "{student} recognized recurring patterns across puzzle sets, suggesting a recognition of geometric pattern equivalence across different spatial contexts",
    "cross_learner": "Both learners approached spatial matching tasks by relying on prior successful patterns, even in tasks that were more challenging. This suggests growing confidence and spatial awareness",
  },
  "reward": {
    "individual": "{student} showed a strong response to visible reward markers, suggesting that external incentives may currently play a meaningful role in sustaining task effort",
    "cross_learner": "Both learners responded to different reward systems, suggesting that reward sensitivity may itself be a learner-specific pathway rather than a shared mechanism",
  },
  "scaffold": {
    "individual": "{student} relied on a scaffolded starting point before continuing independently, suggesting that structured support at the outset can free up capacity for independent problem-solving later in a task",
    "cross_learner": "Both learners made use of scaffolded starting points differently, suggesting that the amount of initial support each benefits from may vary by learner",
  },
}

DATA_FLAG_PHRASES = {
  "familiar": {
    "individual": "Observe whether {student} continues to rely on familiar entry points as task difficulty increases, or begins initiating less familiar approaches independently",
    "cross_learner": "Continue monitoring how each learner's use of familiar strategies evolves, given that both currently anchor to different kinds of familiarity",
  },
  "flexib": {
    "individual": "Track whether specific tasks promote abstraction flexibility for {student}",
    "cross_learner": "Observe if flexible transfer of strategies appears across different task types for both learners",
  },
  "independen": {
    "individual": "Continue monitoring whether {student} chooses to complete tasks independently",
    "cross_learner": "Track if either learner prefers to complete specific types of tasks independently",
  },
  "engag": {
    "individual": "Track how long it takes for {student} to re-engage and resume task",
    "cross_learner": "Continue monitoring if sustained engagement patterns persist when worksheet tasks are followed by play time",
  },
  "motivat": {
    "individual": "Track different contributing factors to {student}'s motivation",
    "cross_learner": "Observe whether both learners show signs of developing intrinsic motivation",
  },
  "structure": {
    "individual": "Observe how task structure appears to influence {student}'s conceptual consolidation",
    "cross_learner": "Observe whether individual preference for specific task structure is connected to learner-specific pathways",
  },
  "spatial_pattern": {
    "individual": "Track {student}'s problem-solving patterns and geometric discrimination in spatial tasks",
    "cross_learner": "Continue monitoring both learners' spatial reasoning and pattern detection across different task forms"
  },
  "reward": {
    "individual": "Continue monitoring {student}'s response to reward systems",
    "cross_learner": "Track if individual learner response to reward changes depending on context, such as perceived cost of effort, inclination toward play, and perceived task difficulty",
  },
  "scaffold": {
    "individual": "Observe if {student} recalls a specific strategy in a similarly constrained, scaffolded problem",
    "cross_learner": "Continue observing how scaffolded approaches contribute to task completion and learner confidence",
  },
}

def _first_known_theme(entries, phrase_bank):
  for entry in entries:
    if entry[0] in phrase_bank:
      return entry
  return None


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
    bullet += ". " + JJ_ADDENDUM

  return bullet + "."


def _build_snapshot(
    rng: np.random.Generator,
    selection: dict,
) -> str:

  candidates = []

  all_themes = selection["all_themes"]

  for bucket_type, entries in all_themes.items():
    for theme, score, has_jj in entries:
      candidates.append(
        (theme, bucket_type, score, has_jj)
      )

  known_candidates = [
    entry
    for entry in candidates
    if entry[0] in THEME_PHRASES
  ]

  if not known_candidates:
    return ""

  def _priority_key(entry):
    theme, bucket_type, score, has_jj = entry
    return (score, bucket_type == "cross_learner")

  winning_theme, winning_bucket_type, _, _ = max(
    known_candidates,
    key=_priority_key
  )

  if winning_bucket_type == "cross_learner":
    phrase_type = "cross_learner"
    student = None
  else:
    phrase_type = "individual"
    student = winning_bucket_type.split("_")[0]

  phrase = THEME_PHRASES[winning_theme][phrase_type]

  if student is not None:
    phrase = phrase.format(student=student)

  first_sentence = f"{phrase[0].upper()}{phrase[1:]}"

  s01_theme = _first_known_theme(
    all_themes["S01_individual"], 
    THEME_PHRASES
  )
  s02_theme = _first_known_theme(
    all_themes["S02_individual"],
    THEME_PHRASES
  )

  individual_sentences = []

  if s01_theme is not None and s01_theme[0] != winning_theme:
    s01_sentence = THEME_PHRASES[s01_theme[0]]["individual"]
    s01_sentence = s01_sentence.format(student="S01")
    individual_sentences.append(s01_sentence)

  if s02_theme is not None and s02_theme[0] != winning_theme:
    s02_sentence = THEME_PHRASES[s02_theme[0]]["individual"]
    s02_sentence = s02_sentence.format(student="S02")
    individual_sentences.append(s02_sentence)

  sentences = [first_sentence]

  if individual_sentences:
    connector = rng.choice(
      CONNECTOR_PHRASES["connector"]
    )

    if len(individual_sentences) == 1:
      sentences.append(
        f"{connector} {individual_sentences[0]}"
      )
    else:
      sentences.append(
        f"{connector} {individual_sentences[0]}, while {individual_sentences[1]}"
      )

  return " ".join(
    f"{sentence}." if not sentence.endswith(".") else sentence
    for sentence in sentences
  )


def _build_learning_mechanism(
    selection: dict,
) -> str:

  all_themes = selection["all_themes"]

  s01_theme = _first_known_theme(
    all_themes["S01_individual"],
    LEARNING_MECHANISM_PHRASES
  )
  s02_theme = _first_known_theme(
    all_themes["S02_individual"],
    LEARNING_MECHANISM_PHRASES
  )
  cross_theme = _first_known_theme(
    all_themes["cross_learner"],
    LEARNING_MECHANISM_PHRASES
  )

  bullets = []

  if s01_theme is not None:
    s01_bullet = LEARNING_MECHANISM_PHRASES[s01_theme[0]]["individual"]
    s01_bullet = s01_bullet.format(student="S01")
    bullets.append(s01_bullet)

  if s02_theme is not None:
    s02_bullet = LEARNING_MECHANISM_PHRASES[s02_theme[0]]["individual"]
    s02_bullet = s02_bullet.format(student="S02")
    bullets.append(s02_bullet)

  if cross_theme is not None:
    cross_learner_bullet = LEARNING_MECHANISM_PHRASES[cross_theme[0]]["cross_learner"] 
    bullets.append(cross_learner_bullet)

  if not bullets:
    return ""
  return "* " + "\n* ".join([item + "." for item in bullets])


def _build_data_flags(
    selection: dict,
) -> str:

  all_themes = selection["all_themes"]

  s01_theme = _first_known_theme(
    all_themes["S01_individual"],
    DATA_FLAG_PHRASES
  )
  s02_theme = _first_known_theme(
    all_themes["S02_individual"],
    DATA_FLAG_PHRASES
  )
  cross_theme = _first_known_theme(
    all_themes["cross_learner"],
    DATA_FLAG_PHRASES
  )

  bullets = []

  if s01_theme is not None:
    s01_bullet = DATA_FLAG_PHRASES[s01_theme[0]]["individual"]
    s01_bullet = s01_bullet.format(student="S01")
    bullets.append(s01_bullet)

  if s02_theme is not None:
    s02_bullet = DATA_FLAG_PHRASES[s02_theme[0]]["individual"]
    s02_bullet = s02_bullet.format(student="S02")
    bullets.append(s02_bullet)

  if cross_theme is not None:
    cross_learner_bullet = DATA_FLAG_PHRASES[cross_theme[0]]["cross_learner"]
    bullets.append(cross_learner_bullet)

  if not bullets:
    return ""
  return "* " + "\n* ".join([item + "." for item in bullets])