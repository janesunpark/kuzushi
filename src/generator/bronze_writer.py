import csv


SESSION_COLUMNS = [
  ("timestamp", "Timestamp"),
  ("observer_id", "Observer ID"),
  ("student_id", "Student ID"),
  ("observation_context", "Observation Context"),
  ("Focus or Attention", "Focus or Attention"),
  ("Coordination and Motor Skills", "Coordination and Motor Skills - may be DELETED"),
  ("Carryover or Retention", "Carryover or Retention"),
  ("Problem-Solving or Cognitive Flexibility", "Problem-Solving or Cognitive Flexibility"),
  ("Resilience", "Resilience (Response to Mistakes or Corrections)"),
  ("Confidence, Autonomy, or Initiative", "Confidence, Autonomy, or Initiative"),
  ("Social Regulation", "Social Regulation - may be DELETED"),
  ("Frustration Tolerance", "Frustration Tolerance"),
  ("Notes", "Notes"),
  ("Email Address", "Email Address"),
  ("Abstract Thinking and Pattern Recognition", "Abstract Thinking and Pattern Recognition"),
  ("Impulse Modulation", "Impulse Modulation"),
  ("Number of Pages Completed", "Number of Pages Completed"),
  ("Published Materials Used", "Published Materials Used"),
  ("Duration in Minutes", "Duration in Minutes"),
  ("Emotional Tone of Teacher", "Emotional Tone of Teacher"),
  ("Parent Interaction", "Parent Interaction"),
  ("Environment or Disruptions", "Environment or Disruptions"),
  ("Task Difficulty or Novelty", "Task Difficulty or Novelty"),
  ("Puzzle Type", "Puzzle Type"),
  ("Puzzle Challenge or Novelty", "Puzzle Challenge or Novelty"),
  ("Primary Task Type", "Primary Task Type"),
  ("Column 24", "Column 24"),
  ("Column 25", "Column 25"),
  ("Task Difficulty or Novelty.1", "Task Difficulty or Novelty"),
  ("Column 23", "Column 23"),
]

SYNTHESIS_COLUMNS = [
  ("timestamp", "Timestamp"),
  ("Observer ID", "Observer ID"),
  ("Student ID", "Student ID"),
  ("week_ending", "Week of "),
  ("num_sessions_reported", "Number of Enrichment Sessions"),
  ("Snapshot", "Snapshot"),
  ("Notable Shifts or Confirmations", "Notable Shifts or Confirmations"),
  ("Learning Mechanisms Observed", "Learning Mechanisms Observed"),
  ("Optional: Data Flags (If Relevant)", "Optional: Data Flags (If Relevant)"),
  ("Are participants siblings?", "Are participants siblings?"),
  ("Dyad ID", "Dyad ID"),
  ("JJ Observed", "If Jiu-Jitsu sessions were observed, for which learner(s)?"),
  ("Private Lessons", "Select any learner(s) that take at least one weekly private lessons in Jiu-Jitsu."),
  ("Column 11", "Column 11"),
  ("Column 12", "Column 12"),
  ("Column 10", "Column 10"),
]


def _write_csv(rows: list[dict], columns: list[tuple[str, str]], path: str) -> None:
  header_row = [real for _, real in columns]
  with open(path, "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(header_row)
    for row in rows:
      value_row = []
      for internal, real in columns:
        if internal not in row:
          raise KeyError(f"Row is missing expected field {internal!r} (needed for header {real!r})")
        value_row.append(row[internal])
      writer.writerow(value_row)


def write_session_csv(rows: list[dict], path: str) -> None:
  _write_csv(rows, SESSION_COLUMNS, path)


def write_synthesis_csv(rows: list[dict], path: str) -> None:
  _write_csv(rows, SYNTHESIS_COLUMNS, path)