import pandas as pd
from pandas.api.types import is_string_dtype


def clean_file(input_path, output_path):
    if input_path.lower().endswith(".csv"):
        df = pd.read_csv(input_path)
    elif input_path.lower().endswith((".xlsx", ".xls")):
        df = pd.read_excel(input_path)
    else:
        raise ValueError("Formato no compatible. Usa CSV o Excel.")

    changes = {
        "whitespace_cells": 0,
        "duplicate_rows": 0,
        "empty_rows": 0
    }

    for column in df.columns:
        if is_string_dtype(df[column]):
            values = df[column].dropna().astype(str)

            changes["whitespace_cells"] += int(
                (values != values.str.strip()).sum()
            )

            df[column] = df[column].str.strip()

    empty_rows = df.isna().all(axis=1)
    changes["empty_rows"] = int(empty_rows.sum())
    df = df.loc[~empty_rows].copy()

    changes["duplicate_rows"] = int(df.duplicated().sum())
    df = df.drop_duplicates().copy()

    if output_path.lower().endswith(".csv"):
        df.to_csv(output_path, index=False)
    else:
        df.to_excel(output_path, index=False)

    return changes


if __name__ == "__main__":
    result = clean_file(
        "examples/test.xlsx",
        "examples/test_cleaned.xlsx"
    )
    print(result)
