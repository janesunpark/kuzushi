from src.generator._helpers import _find_phase, _level_weights, END
from src.generator.schedule_generation import *  


def assign_observer_id(
    session_rows: list[dict],
    transition_week: date,
) -> list[dict]:

  finalized_rows = []

  for row in session_rows:
    new_row = row.copy()

    if new_row["_true_week_ending"] >= transition_week:
      new_row["observer_id"] = "T01"
    else: 
      new_row["observer_id"] = "T0"

    finalized_rows.append(new_row)

  return finalized_rows


def assign_observation_context(
  session_rows: list[dict],
  rng: np.random.Generator,
  cutoff_week: date,
) -> list[dict]:

  meeting_categories = {}
  finalized_rows = []

  categories = [
    "Enrichment: Group Session",
    "Enrichment: Group Activity",
  ]

  probabilities = np.array([43, 12]) / sum([43, 12])

  for row in session_rows:
    new_row = row.copy()

    if new_row["_session_category"] == "Enrichment":
      session_key = new_row["timestamp"]

      if session_key not in meeting_categories:
        if new_row["_true_week_ending"] >= cutoff_week:
          meeting_categories[session_key] = "Enrichment (Sibling Dyad)"

        else:
          meeting_categories[session_key] = str(
            rng.choice(
              categories,
              p=probabilities,
            )
          )

      new_row["observation_context"] = (
        meeting_categories[session_key]
      )

    finalized_rows.append(new_row)

  return finalized_rows


def assign_core_ratings(
    session_rows: list[dict],
    rng: np.random.Generator,
) -> list[dict]:

  finalized_rows = []

  student_weights = {
    "S01": {
      "Focus or Attention": {
        "ratings": np.arange(1, 6),
        "weights": np.array([3, 7, 19, 27, 18])/sum([3, 7, 19, 27, 18]),
      },
      "Carryover or Retention": {
        "ratings": np.arange(1, 6),
        "weights": np.array([1, 2, 26, 30, 15])/sum([1, 2, 26, 30, 15]),
      },
      "Confidence, Autonomy, or Initiative": {
        "ratings": np.arange(1, 6),
        "weights": np.array([1, 4, 18, 27, 24])/sum([1, 4, 18, 27, 24]),
      },
    },

    "S02": {
      "Focus or Attention": {
        "ratings": np.arange(1, 6),
        "weights": np.array([3, 10, 28, 25, 14])/sum([3, 10, 28, 25, 14]),
      },
      "Carryover or Retention": {
        "ratings": np.arange(1, 6),
        "weights": np.array([0, 5, 32, 29, 14])/sum([0, 5, 32, 29, 14]),
      },
      "Confidence, Autonomy, or Initiative": {
        "ratings": np.arange(1, 6),
        "weights": np.array([3, 6, 23, 25, 23])/sum([3, 6, 23, 25, 23]),
      },
    },
  }

  for row in session_rows:
    new_row = row.copy()

    student_id = new_row["student_id"]
    distributions = student_weights[student_id]

    for domain, distribution in distributions.items():

      new_row[domain] = int(
        rng.choice(
          distribution["ratings"],
          p=distribution["weights"],
        )
      )

    finalized_rows.append(new_row)

  return finalized_rows


def assign_secondary_ratings(
    session_rows: list[dict],
    rng: np.random.Generator,
) -> list[dict]:

  finalized_rows = []

  null_rates = {
    "Enrichment": {
      "Problem-Solving or Cognitive Flexibility": 0.15,
      "Resilience": 0.1,
      "Frustration Tolerance": 0.13,
      "Abstract Thinking and Pattern Recognition": 0.23,
      "Impulse Modulation": 0.28,
    },
    "Jiu-Jitsu": {
      "Problem-Solving or Cognitive Flexibility": 0.15,
      "Resilience": 0.11,
      "Frustration Tolerance": 0.27,
      "Abstract Thinking and Pattern Recognition": 0.5,
      "Impulse Modulation": 0.55,
    },
  }

  pooled_value_distribution = {
    "Problem-Solving or Cognitive Flexibility": {
      "ratings": np.arange(1, 6),
      "weights": np.array([14, 12, 62, 26, 17])/sum([14, 12, 62, 26, 17]),
    },
    "Resilience": {
      "ratings": np.arange(1, 6),
      "weights": np.array([13, 10, 64, 27, 25])/sum([13, 10, 64, 27, 25]),
    },
    "Frustration Tolerance": {
      "ratings": np.arange(1, 6),
      "weights": np.array([18, 9, 51, 33, 20])/sum([18, 9, 51, 33, 20]),
    },
    "Abstract Thinking and Pattern Recognition": {
      "ratings": np.arange(1, 6),
      "weights": np.array([5, 19, 38, 31, 20])/sum([5, 19, 38, 31, 20]),
    },
    "Impulse Modulation": {
      "ratings": np.arange(1, 6),
      "weights": np.array([13, 15, 34, 20, 23])/sum([13, 15, 34, 20, 23]),
    },
  }

  for row in session_rows:
    new_row = row.copy()

    context = new_row["_session_category"]
    context_null_rates = null_rates[context]

    for domain, null_rate in context_null_rates.items():

      is_null = rng.choice(
        [True, False],
        p=[null_rate, 1 - null_rate],
      )

      if is_null:
        new_row[domain] = None
      else:
        distribution = pooled_value_distribution[domain]

        new_row[domain] = int(
          rng.choice(
            distribution["ratings"],
            p=distribution["weights"],
          )
        )

    finalized_rows.append(new_row)

  return finalized_rows


def assign_deprecated_ratings(
    session_rows: list[dict],
    rng: np.random.Generator,
    cutoff_week: date,
) -> list[dict]:

  finalized_rows = []

  null_rates = {
    "Coordination and Motor Skills": 0.296,
    "Social Regulation": 0.042,
  }

  for row in session_rows:
    new_row = row.copy()
    current_date = new_row["_true_week_ending"]

    if current_date >= cutoff_week:
      for domain in null_rates:
        new_row[domain] = None

    else:
      for domain in null_rates:
        null_rate = null_rates[domain]

        is_null = rng.choice(
          [True, False],
          p=[null_rate, 1 - null_rate],
        )

        if is_null:
          new_row[domain] = None
        else:
          new_row[domain] = int(
            rng.choice(
              np.arange(1, 6),
              p=np.array([20, 20, 20, 20, 20])/sum([20, 20, 20, 20, 20])
            )
          )

    finalized_rows.append(new_row)

  return finalized_rows


def assign_pages_completed(
    session_rows: list[dict],
    rng: np.random.Generator,
    cutoff_week: date,
) -> list[dict]:

  finalized_rows = []

  for row in session_rows:
    new_row = row.copy()

    if new_row["_session_category"] == "Jiu-Jitsu":
      new_row["Number of Pages Completed"] = None

    else:
      if new_row["_true_week_ending"] < cutoff_week:
        new_row["Number of Pages Completed"] = None

      else:
        current_week = new_row["_true_week_ending"]

        progress = (
          (current_week - cutoff_week).days / 
          (END - cutoff_week).days
        )

        base_mean = 5.2 if new_row["student_id"] == "S01" else 6.5
        final_mean = 6.0 if new_row["student_id"] == "S01" else 7.5

        expected_pages = (
          base_mean + 
          progress * (final_mean - base_mean)
        )

        pages = int(round(
          rng.normal(expected_pages, 3.0)
        ))

        pages = max(1, min(21, pages))

        new_row["Number of Pages Completed"] = pages

    finalized_rows.append(new_row)

  return finalized_rows


def assign_task_difficulty(
    session_rows: list[dict],
    rng: np.random.Generator,
    cutoff_week: date,
) -> list[dict]:

  finalized_rows = []

  distribution = {
    "S01": {
      "ratings": np.arange(1, 6),
      "weights": np.array([5, 11, 10, 6, 5])/sum([5, 11, 10, 6, 5]),
    },
    "S02": {
      "ratings": np.arange(1, 6),
      "weights": np.array([2, 8, 18, 4, 5])/sum([2, 8, 18, 4, 5]),
    },
  }

  for row in session_rows:
    new_row = row.copy()

    new_row["Task Difficulty or Novelty"] = None

    if new_row["_true_week_ending"] >= cutoff_week:
      student = new_row["student_id"]

      new_row["Task Difficulty or Novelty"] = int(
        rng.choice(
          distribution[student]["ratings"],
          p=distribution[student]["weights"]
        )
      ) 

    finalized_rows.append(new_row)

  return finalized_rows


def assign_duration(
    session_rows:list[dict],
    rng: np.random.Generator,
    cutoff_week: date,
    phase_shift_week: date,
) -> list[dict]:

  finalized_rows = []

  early_duration_distribution = {
    45 : 2,
    60 : 4,
    75 : 4,
    80 : 10,
    90 : 2, 
    120: 8,
  }

  late_duration_distribution = {
    60 : 18,
    80 : 38,
    90 : 4,
  }

  for row in session_rows:
    new_row = row.copy()

    if new_row["_true_week_ending"] < cutoff_week:
      new_row["Duration in Minutes"] = None

    elif new_row["_session_category"] == "Jiu-Jitsu":
      new_row["Duration in Minutes"] = 45

    else: 
      if new_row["_true_week_ending"] >= phase_shift_week:
        distribution = late_duration_distribution

      else:
        distribution = early_duration_distribution

      minutes = list(distribution.keys())
      weights = np.array(list(distribution.values()))
      weights = weights / weights.sum()

      new_row["Duration in Minutes"] = int(
        rng.choice(minutes, p=weights)
      )

    finalized_rows.append(new_row)

  return finalized_rows


def assign_primary_task_type(
    session_rows: list[dict],
    rng: np.random.Generator,
    cutoff_week: date,
) -> list[dict]:

  finalized_rows = []

  task_distribution = {
    "Mixed" : 20,
    "Worksheet" : 14,
    "Puzzle" : 1,
  }

  for row in session_rows:
    new_row = row.copy()

    new_row["Primary Task Type"] = None

    if (
      new_row["_true_week_ending"] >= cutoff_week
      and new_row["_session_category"] == "Enrichment"
    ):
      tasks = list(task_distribution.keys())
      weights = np.array(list(task_distribution.values()))
      weights = weights / weights.sum()

      new_row["Primary Task Type"] = str(rng.choice(
        tasks,
        p=weights
      ))
  
    finalized_rows.append(new_row)

  return finalized_rows


def assign_published_materials_used(
    session_rows: list[dict],
    rng: np.random.Generator,
    cutoff_week: date,
) -> list[dict]:

  finalized_rows = []

  s01_phases = [
    (date(2025, 12, 14), {"MathQuest KA Workbook": 4, "MathQuest KA Textbook": 3, "MathQuest PKA Workbook": 1}),
    (date(2026, 1, 18),  {"MathQuest KB Workbook": 1, "MathQuest KA Textbook": 1, "MathQuest KA Workbook": 1, "MathQuest KB Textbook": 1}),
    (date(2026, 2, 1),   {"MathQuest PKB Workbook": 18, "MathQuest PKB Textbook": 16, "MathQuest KB Workbook": 5, "MathQuest KB Textbook": 1}),
    (date(2026, 6, 7),   {"MathQuest KA Textbook": 3, "MathQuest KA Workbook": 2}),
  ]

  s02_phases = [
    (date(2025, 12, 14), {"MathQuest KA Workbook": 3, "MathQuest KA Textbook": 3}),
    (date(2026, 1, 11),  {"MathQuest KB Textbook": 1, "MathQuest KA Workbook": 1}),
    (date(2026, 1, 18),   {"MathQuest KB Workbook": 25, "MathQuest KB Textbook": 21}),
    (date(2026, 6, 7),   {"MathQuest KB Textbook": 2, "MathQuest 1A Textbook": 1}),
  ]

  level_phases = {
    "S01": s01_phases,
    "S02": s02_phases,
  }

  for row in session_rows:
    new_row = row.copy()

    if (
      new_row["_true_week_ending"] < cutoff_week
      or new_row["_session_category"] != "Enrichment"
    ):
      new_row["Published Materials Used"] = None

    else:
      weights = _find_phase(
        level_phases[new_row["student_id"]], 
        new_row["_true_week_ending"]
      )

      items = list(weights.keys())
      probs = np.array(list(weights.values()))
      probs = probs / probs.sum()

      item_count = int(
        rng.choice(
          [1, 2], 
          p=[0.76, 0.24]
          )
        )

      if item_count == 1:
        value = [str(rng.choice(items, p=probs))]

      elif rng.random() < 0.86:
          level_weights = _level_weights(weights)
          levels = list(level_weights.keys())
          level_probs = np.array(list(level_weights.values()))
          level_probs = level_probs / level_probs.sum()

          level = str(
            rng.choice(
              levels, 
              p=level_probs
              )
            )

          value = [f"MathQuest {level} Textbook", f"MathQuest {level} Workbook"]

      else:
        value = [
          str(v) 
          for v in rng.choice(
            items, 
            size=2, 
            replace=False, 
            p=probs
          )
        ] 

      new_row["Published Materials Used"] = ", ".join(value)

    finalized_rows.append(new_row)

  return finalized_rows


def assign_puzzle_type(
    session_rows: list[dict],
    rng: np.random.Generator,
    cutoff_week: date,
    primary_task_type_cutoff_week: date,
) -> list[dict]:

  finalized_rows = []

  item_distribution = {
    "S01": {
      "items": np.array([
        "CubePix",
        "GeoCrystals",
        "Tetromino Square",
        "Geoboard",
        "Pattern Blocks",
      ]),
      "weights": np.array([7, 5, 3, 2, 1]),
    },
    "S02": {
      "items": np.array([
        "CubePix",
        "GeoCrystals",
        "Tetromino Square",
        "Geoboard",
        "Pattern Blocks",
      ]),
      "weights": np.array([10, 5, 5, 3, 1]),
    },
  }

  null_rates = {
    "Worksheet": 0.75,
    "Mixed": 0.0,
    "Puzzle": 0.0,
  }

  item_counts = {
    "Mixed": {
      "counts": np.array([1, 2, 3]),
      "weights": np.array([8, 12, 1]),
    },
    "Puzzle": {
      "counts": np.array([1, 2, 3]),
      "weights": np.array([8, 12, 1]),
    },
  }

  for row in session_rows:
    new_row = row.copy()
    new_row["Puzzle Type"] = None

    if (
      new_row["_true_week_ending"] >= cutoff_week
      and new_row["_session_category"] == "Enrichment"
    ):
      student_id = new_row["student_id"]
      puzzles = item_distribution[student_id]["items"]
      weights = item_distribution[student_id]["weights"]
      weights = weights / weights.sum()

      if new_row["_true_week_ending"] < primary_task_type_cutoff_week:
        if rng.random() >= 0.5:
          new_row["Puzzle Type"] = str(rng.choice(puzzles, p=weights))

      else:
        task_type = new_row['Primary Task Type']

        if rng.random() >= null_rates[task_type]:
          if task_type == "Worksheet":
            item_count = 1

          else:
            counts = item_counts[task_type]["counts"]
            probs = item_counts[task_type]["weights"]
            probs = probs / probs.sum()

            item_count = int(
              rng.choice(
                counts,
                p=probs,
              )
            )

          selected_puzzles = [
            str(v) 
            for v in rng.choice(
              puzzles,
              size=item_count,
              replace=False,
              p=weights,
            )
          ]

          new_row["Puzzle Type"] = ", ".join(selected_puzzles)

    finalized_rows.append(new_row)

  return finalized_rows


def assign_puzzle_challenge(
    session_rows: list[dict],
    rng: np.random.Generator,
) -> list[dict]:

  finalized_rows = []

  item_weights = {
    "rates": np.arange(1, 6),
    "weights": np.array([5, 2, 7, 9, 5]),
  }

  for row in session_rows:
    new_row = row.copy()

    new_row["Puzzle Challenge or Novelty"] = None

    if new_row["Puzzle Type"] is not None:
      ratings = item_weights["rates"]
      weights = item_weights["weights"]
      weights = weights / weights.sum()

      new_row["Puzzle Challenge or Novelty"] = int(
        rng.choice(
          ratings,
          p=weights
        )
      )

    finalized_rows.append(new_row)

  return finalized_rows


def assign_session_context_fields(
    session_rows: list[dict],
    rng: np.random.Generator,
    cutoff_week: date,
) -> list[dict]:

  finalized_rows = []

  enrichment_weights = {
    "Parent Interaction": {
      "No" : 58,
      "Yes" : 36,
    },
    "Environment or Disruptions": {
      "Quiet": 76,
      "Time Constraints": 8,
      "Distracting": 7,
      "Noisy": 3,
    },
    "Emotional Tone of Teacher": {
      "ratings": np.arange(1, 6),
      "weights": np.array([0, 1, 77, 8, 8]),
    },
  }

  jiu_jitsu_weights = {
    "Parent Interaction": {
      "No": 7,
      "Yes": 5,
    },
    "Environment or Disruptions": {
      "Quiet": 9,
      "Time Constraints": 0,
      "Distracting": 1,
      "Noisy": 2
    },
    "Emotional Tone of Teacher": {
      "ratings": np.arange(1, 6),
      "weights": np.array([0, 0, 9, 3, 0]),
    }
  }

  session_contexts = {
    "Enrichment": enrichment_weights,
    "Jiu-Jitsu": jiu_jitsu_weights,
  }

  for row in session_rows:
    new_row = row.copy()

    if new_row["_true_week_ending"] >= cutoff_week:
      session_context = session_contexts[new_row["_session_category"]]

      for domain, distribution in session_context.items():

        if domain == "Emotional Tone of Teacher":
          ratings = distribution["ratings"]
          weights = distribution["weights"]
          weights = weights / weights.sum()

          new_row[domain] = int(
            rng.choice(
              ratings,
              p=weights,
            )
          )

        else: 
          contexts = list(distribution.keys())
          weights = np.array(list(distribution.values()))
          weights = weights / weights.sum()

          new_row[domain] = str(
            rng.choice(contexts, p=weights)
          )

    else:
      for domain in enrichment_weights:
        new_row[domain] = None

    finalized_rows.append(new_row)

  return finalized_rows


def assign_static_null_fields(
    session_rows: list[dict]
) -> list[dict]:

  finalized_rows = []

  null_fields = [
    "Email Address",
    "Column 23",
    "Column 24",
    "Column 25",
    "Task Difficulty or Novelty.1"
  ]

  for row in session_rows:
    new_row = row.copy()

    for field in null_fields:
      new_row[field] = None

    finalized_rows.append(new_row)

  return finalized_rows


def assign_notes(
    session_rows: list[dict],
    rng: np.random.Generator,
) -> list[dict]:

  finalized_rows = []

  theme_bank = {

    # ============ Correlated themes ============ #

    "familiar": {
      "base_weight": 0.143,
      "correlated_field": "Resilience",
      "fragments": [
        "Approached the more constrained puzzle by placing familiar shapes first before adjusting to the rest.",
        "Recovered quickly from an early misstep by falling back on a familiar strategy used successfully in prior sessions.",
        "Used a completed model from an earlier task as a familiar visual reference point when the new version proved harder.",
        "Returned to a familiar entry point after an initial attempt didn't work, then adjusted from there.",
        "Drew on a familiar shape-manipulation technique to work through the more difficult section.",
      ],
      "fragments_jj": [
        "Recognized the familiar warm-up sequence from a previous class and started right away.",
        "Returned to a familiar move without needing a reminder of the steps.",
      ],
    },

    "flexib": {
      "base_weight": 0.162,
      "correlated_field": "Problem-Solving or Cognitive Flexibility",
      "fragments": [
        "Showed a flexible approach when the first strategy wasn't working, without becoming stuck on it.",
        "Flexibly moved between two different problem-solving approaches within the same task.",
        "Tackled problems using a creative strategy and cognitive flexibility.",
        "Flexibly handled an unexpected change in task rules with minimal disruption to focus.",
      ],
      "fragments_jj": None,
    },

    "independen": {
      "base_weight": 0.318,
      "correlated_field": "Confidence, Autonomy, or Initiative",
      "fragments": [
        "Completed the task independently, checking in only once the section was finished.",
        "Made an independent choice about how to approach the activity before any suggestion was offered.",
        "Worked through a full page independently, referring back to earlier examples when needed.",
        "Independently started the next task before being asked.",
      ],
      "fragments_jj": [
        "Put on and adjusted their own belt independently.",
        "Independently helped gather equipment after the drill.",
      ],
    },

    "engag": {
      "base_weight": 0.481,
      "correlated_field": "Focus or Attention",
      "fragments": [
        "Remained engaged with the task for the full session with only brief attention lapses.",
        "Stayed engaged through a longer task sequence than in recent prior sessions.",
        "Needed one redirect to re-engage after a short distraction, then sustained focus afterward.",
        "Showed sustained engagement during a repetitive portion of the task that has previously been harder to hold interest in.",
      ],
      "fragments_jj": [
        "Remained engaged through the full drill sequence without needing redirection.",
        "Needed one redirect to refocus after becoming distracted, then engaged fully afterward.",
        "Stayed engaged during partner drills despite a livelier-than-usual room.",
      ],
    },

    "motivat": {
      "base_weight": 0.260,
      "correlated_field": "Confidence, Autonomy, or Initiative",
      "fragments": [
        "Was motivated to try the next page before being prompted to move on.",
        "Stayed motivated to work past the point where the session would typically wrap up.",
        "Stayed motivated through a task that had been challenging in earlier sessions.",
        "Was motivated to redo an earlier section without being asked, aiming to improve on the first attempt.",
        "Showed motivation to complete more tasks after finishing one.",
      ],
      "fragments_jj": [
        "Showed motivation to demonstrate when a new drill was introduced.",
        "Was motivated to work on a favorite drill and asked to repeat it.",
      ],
    },

    "structure": {
      "base_weight": 0.247,
      "correlated_field": "Problem-Solving or Cognitive Flexibility",
      "fragments": [
        "Worked through the task in a clear, self-imposed structure rather than jumping between sections.",
        "Structured a multi-part task into clearly ordered pieces and completed them in sequence.",
      ],
      "fragments_jj": [
        "Followed the structured drill in order without needing reminders partway through.",
        "Remembered the structured sequence of steps in the double leg takedown and repeated it without help.",
        "Completed a structured series of movements during the drill with minimal prompting."
      ],
    },
    "spatial_pattern": {
      "base_weight": 0.331,
      "correlated_field": "Abstract Thinking and Pattern Recognition",
      "fragments": [
        "Identified the repeating pattern within the first few pieces and completed the rest with minimal hesitation.",
        "Correctly identified the next element in the spatial sequence before it appeared.",
        "Pointed out that two separate parts of the task followed the same underlying pattern.",
        "Grouped pieces together based on a shared spatial relationship.",
      ],
      "fragments_jj": [
        "Matched the demonstrated position correctly, following the same pattern shown.",
        "Spatially positioned themselves correctly relative to a partner after watching the instructor.",
      ],
    },

    # ============ Flavor themes -- no correlated_field ============ #

    "comparison": {
      "base_weight": 0.155,
      "correlated_field": None,
      "fragments": [
        "Visibly compared themselves to the other student's work partway through the task.",
        "Asked how their result compared to a previous attempt, seeking the instructor's affirmation.",
        "Compared their tasks to the other student's, remarking which ones seemed easier or harder.",
      ],
      "fragments_jj": None,
    },

    "reward": {
      "base_weight": 0.338,
      "correlated_field": None,
      "fragments": [
        "Reacted with visible smile upon receiving a sticker reward for completing the task.",
        "Confirmed how many stickers they would need to earn a reward before starting the activity.",
        "Chose the next activity based on which one had a reward attached.",
      ],
      "fragments_jj": None,
    },

    "novelty": {
      "base_weight": 0.156,
      "correlated_field": None,
      "fragments": [
        "Expressed curiosity toward a novel strategic game.",
        "Responded positively to a novel set of materials introduced partway through the session.",
        "Responded positively to novel rewards and completed additional tasks to earn them.",
      ],
      "fragments_jj": None,
    },

    "scaffold": {
      "base_weight": 0.104,
      "correlated_field": None,
      "fragments": [
        "Completed the first two steps independently, then used them as scaffolds to tackle another problem.",
        "Followed along after the instructor scaffolded the problem.",
        "Used a partially completed example as a scaffolded reference before continuing on their own.",
      ],
      "fragments_jj": None,
    },
  }

  bullet_count = {
   1 : 1, 
   2 : 11, 
   3 : 10,
   4 : 28,
   5 : 19,
   6 : 27,
   7 : 19,
   8 : 12,
   9 : 8,
   10 : 6,
   11 : 5,
   12 : 4,
   13 : 2, 
   14 : 2,
  }

  for row in session_rows:
    new_row = row.copy()

    is_jj = row["_session_category"] == "Jiu-Jitsu"

    eligible = [
      name for name, theme in theme_bank.items()
      if not is_jj or theme["fragments_jj"] is not None
    ]

    weights = []

    for name in eligible:
      theme = theme_bank[name]
      w = theme["base_weight"]
      field = theme["correlated_field"]

      if field is not None:
        rating = row.get(field)

        if rating is not None:
          rating_offset = (rating - 3) / 2
          w = w * max(1 + rating_offset, 0.15)

      weights.append(w)

    weights = np.array(weights)
    weights = weights / weights.sum()

    counts = list(bullet_count.keys())
    count_weights = np.array(list(bullet_count.values()))
    count_weights = count_weights / count_weights.sum()
    n_bullets = int(
      rng.choice(
        counts,
        p=count_weights
      )
    )
    n_bullets = min(n_bullets, len(eligible))

    selected = rng.choice(
      eligible,
      size=n_bullets,
      replace=False,
      p=weights
    )

    new_row["_selected_notes_themes"] = [
      str(t) for t in selected
    ]

    bullets = []
    for theme_name in selected:
      theme = theme_bank[theme_name]
      pool = theme["fragments_jj"] if is_jj else theme["fragments"]
      bullets.append(str(rng.choice(pool)))

    new_row["Notes"] = "* " + "\n* ".join(bullets)
    finalized_rows.append(new_row)

  return finalized_rows