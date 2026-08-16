def assign_synthesis_static_fields(
    synthesis_rows: list[dict],
) -> list[dict]:

  finalized_rows = []

  for row in synthesis_rows:
    new_row = row.copy()
    new_row["Observer ID"] = "T01"
    new_row["Student ID"] = "S01, S02"
    new_row["Are participants siblings?"] = "Yes"
    new_row["Dyad ID"] = "A"
    new_row["Column 10"] = None
    new_row["Column 11"] = None
    new_row["Column 12"] = None

    finalized_rows.append(new_row)

  return finalized_rows