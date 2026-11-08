from pathlib import Path

from src.generator.pipeline import generate_synthetic_logs
from src.generator.bronze_writer import write_session_csv, write_synthesis_csv

SEED = 42

if __name__ == "__main__":
  
  PROJECT_ROOT = Path(__file__).parent.parent
  OUTPUT_DIR = PROJECT_ROOT / "data" / "synthetic"
  OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
  SESSION_PATH = OUTPUT_DIR / f"synthetic_session_log_seed{SEED}.csv"
  SYNTHESIS_PATH = OUTPUT_DIR / f"synthetic_weekly_log_seed{SEED}.csv"

  session_rows, synthesis_rows = generate_synthetic_logs(SEED)

  write_session_csv(session_rows, str(SESSION_PATH))
  write_synthesis_csv(synthesis_rows, str(SYNTHESIS_PATH))
  
  print(f"session rows: {len(session_rows)}")
  print(f"synthesis rows: {len(synthesis_rows)}")