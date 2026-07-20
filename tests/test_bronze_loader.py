import pytest
import pandas as pd
from datetime import datetime, timezone

from bronze_loader import load_bronze_csv
from bronze_loader import save_bronze_snapshot


def test_load_bronze_csv_raises_not_found_error(tmp_path):
  missing_csv = tmp_path / "missing.csv"

  with pytest.raises(
    FileNotFoundError,
    match="Bronze source file not found",
  ):
    load_bronze_csv(missing_csv)


def test_save_bronze_snapshot_raises_on_empty_dataframe(tmp_path):

  empty_df = pd.DataFrame()

  with pytest.raises(
    ValueError,
    match="Cannot save an empty Bronze DataFrame."
  ):
    save_bronze_snapshot(
      empty_df,
      "dataset_name",
      tmp_path,
    )


def test_save_bronze_snapshot_raises_on_duplicate_save(tmp_path):

  ingestion_ts = datetime(
    2026, 7, 20, 12, 0, tzinfo=timezone.utc
  )
  tmp_df = pd.DataFrame(
    {
      "value": ["test"],
      "ingestion_ts": [ingestion_ts],
    }
  )
  dataset_name = "dataset_name"

  save_bronze_snapshot(
    tmp_df,
    dataset_name,
    tmp_path,
  )

  with pytest.raises(
    FileExistsError,
    match="Bronze snapshot already exists"
    ):
    save_bronze_snapshot(
      tmp_df,
      dataset_name,
      tmp_path,
    )
  

def test_save_bronze_snapshot_produces_unique_filenames_across_runs(tmp_path):

  ingestion_ts_1 = datetime(
    2026, 7, 20, 8, 0, tzinfo=timezone.utc
  )
  ingestion_ts_2 = datetime(
    2026, 7, 20, 12, 0, tzinfo=timezone.utc
  )
  tmp_df_1 = pd.DataFrame(
    {
      "value": ["test"],
      "ingestion_ts": [ingestion_ts_1],
    }
  )
  tmp_df_2 = pd.DataFrame(
    {
      "value": ["test"],
      "ingestion_ts": [ingestion_ts_2],
    }
  )
  dataset_name = "dataset_name"

  snapshot_path_1 = save_bronze_snapshot(
    tmp_df_1,
    dataset_name,
    tmp_path,
  )

  snapshot_path_2 = save_bronze_snapshot(
    tmp_df_2,
    dataset_name,
    tmp_path,
  )

  assert snapshot_path_1 != snapshot_path_2
  assert snapshot_path_1.exists()
  assert snapshot_path_2.exists()
  

