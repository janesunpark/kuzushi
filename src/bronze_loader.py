from datetime import datetime, timezone
from pathlib import Path
import pandas as pd


def load_bronze_csv(filepath: str | Path) -> pd.DataFrame: 

  filepath = Path(filepath)

  if not filepath.exists():
    raise FileNotFoundError(f"Bronze source file not found: {filepath}")
  
  ingestion_ts = datetime.now(timezone.utc)

  dataframe = pd.read_csv(filepath, dtype = "string")

  dataframe["source_file"] = filepath.name
  dataframe["ingestion_ts"] = ingestion_ts

  return dataframe


def save_bronze_snapshot(dataframe: pd.DataFrame, dataset_name: str, output_dir: str | Path) -> Path:
  output_dir = Path(output_dir)

  if dataframe.empty:
    raise ValueError("Cannot save an empty Bronze DataFrame.")
  
  output_dir.mkdir(parents=True, exist_ok=True)
  ingestion_ts = dataframe["ingestion_ts"].iloc[0]
  clean_timestamp = ingestion_ts.strftime("%Y%m%dT%H%M%S%f")
  output_path = output_dir / f"{dataset_name}_{clean_timestamp}.parquet"

  if output_path.exists():
    raise FileExistsError(
      f"Bronze snapshot already exists at {output_path} — Bronze snapshots are immutable "
      f"and are never overwritten. This usually means save_bronze_snapshot() was called "
      f"twice without a fresh call to load_bronze_csv() in between."
    )
  
  dataframe.to_parquet(output_path, index=False)
  
  return output_path


def load_bronze(raw_dir: str | Path, bronze_dir: str | Path) -> dict[str, pd.DataFrame]:

  raw_path = Path(raw_dir)
  bronze_path = Path(bronze_dir)
 
  bronze_dict: dict[str, pd.DataFrame] = {}
  DATASETS = {
    "session_observations": "session_observation_log_2025–2026.csv",
    "weekly_syntheses": "weekly_synthesis_log_2025–2026.csv",
  }

  for dataset_name, filename in DATASETS.items(): 
    filepath = raw_path / filename
    df = load_bronze_csv(filepath)
    bronze_dict[dataset_name] = df

  saved_paths: list[Path] = []

  try:
    for dataset_name, df in bronze_dict.items():
      snapshot_path = save_bronze_snapshot(
        df,
        dataset_name,
        bronze_path
      )
      saved_paths.append(snapshot_path)
  except Exception:
    for path in saved_paths:
      path.unlink(missing_ok=True)
    raise
  
  return bronze_dict


if __name__ == "__main__":
  
  PROJECT_ROOT = Path(__file__).parent.parent

  bronze = load_bronze(
    PROJECT_ROOT / "data" / "raw",
    PROJECT_ROOT / "data" / "bronze"
    )
  
  print(bronze)
  

