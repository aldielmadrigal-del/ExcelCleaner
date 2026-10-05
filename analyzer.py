import pandas as pd
from pandas.api.types import is_string_dtype


def calculate_price(total_changes):
    if total_changes == 0:
        return 0

    if total_changes <= 10:
        return 5

    if total_changes <= 25:
        return 10

    if total_changes <= 50:
        return 15

    if total_changes <= 100:
        return 25

    extra_changes = total_changes - 100
    extra_blocks = (extra_changes + 49) // 50

    return 25 + (extra_blocks * 5)


def column_letter(number):
    result = ""

    while number > 0:
        number, remainder = divmod(number - 1, 26)
        result = chr(65 + remainder) + result

    return result


def analyze_sheet(df, sheet_name):

    total_rows = len(df)
    total_columns = len(df.columns)

    whitespace_cells = 0
    duplicate_rows = 0
    empty_rows = 0

    changed_cells = []
    removed_rows = []

    whitespace_examples = []
    duplicate_examples = []
    empty_examples = []

    simulated_df = df.copy()

    # ---------------------------------------------------------
    # ESPACIOS
    # ---------------------------------------------------------

    for column_index, column in enumerate(simulated_df.columns):

        if is_string_dtype(simulated_df[column]):

            values = simulated_df[column].dropna().astype(str)

            different = values != values.str.strip()

            indexes = values.index[different]

            whitespace_cells += int(different.sum())

            for index in indexes:

                original = values.loc[index]
                cleaned = original.strip()

                change = {
                    "sheet": sheet_name,
                    "row": int(index) + 2,
                    "column": str(column),
                    "column_letter": column_letter(column_index + 1),
                    "before": original,
                    "after": cleaned
                }

                changed_cells.append(change)

                if len(whitespace_examples) < 5:
                    whitespace_examples.append(change)

            simulated_df[column] = simulated_df[column].str.strip()

    # ---------------------------------------------------------
    # FILAS VACÍAS
    # ---------------------------------------------------------

    empty_mask = simulated_df.isna().all(axis=1)

    empty_indexes = simulated_df.index[empty_mask]

    empty_rows = int(empty_mask.sum())

    for index in empty_indexes:

        item = {
            "sheet": sheet_name,
            "row": int(index) + 2,
            "reason": "Fila completamente vacía"
        }

        removed_rows.append(item)

        if len(empty_examples) < 5:
            empty_examples.append(item)

    simulated_df = simulated_df.loc[~empty_mask].copy()

    # ---------------------------------------------------------
    # DUPLICADOS
    # ---------------------------------------------------------

    duplicate_mask = simulated_df.duplicated(keep="first")

    duplicate_indexes = simulated_df.index[duplicate_mask]

    duplicate_rows = int(duplicate_mask.sum())

    for index in duplicate_indexes:

        item = {
            "sheet": sheet_name,
            "row": int(index) + 2,
            "reason": "Fila duplicada"
        }

        removed_rows.append(item)

        if len(duplicate_examples) < 5:
            duplicate_examples.append(item)

    simulated_df = simulated_df.loc[~duplicate_mask].copy()

    # ---------------------------------------------------------
    # TOTAL
    # ---------------------------------------------------------

    total_changes = (
        whitespace_cells
        + duplicate_rows
        + empty_rows
    )

    problems = []

    if empty_rows > 0:

        problems.append({
            "type": "empty_rows",
            "count": empty_rows,
            "description": (
                f"{empty_rows} filas completamente vacías"
            ),
            "examples": empty_examples
        })

    if duplicate_rows > 0:

        problems.append({
            "type": "duplicates",
            "count": duplicate_rows,
            "description": (
                f"{duplicate_rows} filas duplicadas"
            ),
            "examples": duplicate_examples
        })

    if whitespace_cells > 0:

        problems.append({
            "type": "whitespace",
            "count": whitespace_cells,
            "description": (
                f"{whitespace_cells} "
                "celdas con espacios innecesarios"
            ),
            "examples": whitespace_examples
        })

    # ---------------------------------------------------------
    # COLUMNAS
    # ---------------------------------------------------------

    preview_columns = [
        {
            "name": str(column),
            "letter": column_letter(index + 1)
        }
        for index, column in enumerate(df.columns)
    ]

    # ---------------------------------------------------------
    # VISTA ORIGINAL
    # ---------------------------------------------------------

    original_preview_df = df.fillna("")

    original_preview = []

    for index, row in original_preview_df.iterrows():

        cells = []

        for column_index, column in enumerate(df.columns):

            cells.append({
                "value": str(row[column]),
                "column": str(column),
                "letter": column_letter(column_index + 1)
            })

        original_preview.append({
            "row": int(index) + 2,
            "cells": cells
        })

    # ---------------------------------------------------------
    # VISTA LIMPIA
    # ---------------------------------------------------------

    cleaned_preview_df = simulated_df.fillna("")

    cleaned_preview = []

    for row_index, (_, row) in enumerate(
        cleaned_preview_df.iterrows()
    ):

        cells = []

        for column_index, column in enumerate(
            simulated_df.columns
        ):

            cells.append({
                "value": str(row[column]),
                "column": str(column),
                "letter": column_letter(column_index + 1)
            })

        cleaned_preview.append({
            "row": row_index + 2,
            "cells": cells
        })

    return {
        "name": sheet_name,

        "rows": total_rows,
        "columns": total_columns,

        "total_changes": total_changes,

        "whitespace_cells": whitespace_cells,
        "duplicate_rows": duplicate_rows,
        "empty_rows": empty_rows,

        "problems": problems,

        "preview_columns": preview_columns,

        "original_preview": original_preview,
        "cleaned_preview": cleaned_preview,

        "changed_cells": changed_cells,
        "removed_rows": removed_rows
    }


def analyze_file(file_path):

    # ---------------------------------------------------------
    # CARGAR TODAS LAS HOJAS
    # ---------------------------------------------------------

    if file_path.lower().endswith(".csv"):

        sheets = {
            "CSV": pd.read_csv(file_path)
        }

    elif file_path.lower().endswith((".xlsx", ".xls")):

        sheets = pd.read_excel(
            file_path,
            sheet_name=None
        )

    else:

        raise ValueError(
            "Formato no compatible. Usa CSV o Excel."
        )

    # ---------------------------------------------------------
    # ANALIZAR CADA HOJA
    # ---------------------------------------------------------

    analyzed_sheets = []

    for sheet_name, df in sheets.items():

        result = analyze_sheet(
            df,
            str(sheet_name)
        )

        analyzed_sheets.append(result)

    # ---------------------------------------------------------
    # RESUMEN GENERAL
    # ---------------------------------------------------------

    total_rows = sum(
        sheet["rows"]
        for sheet in analyzed_sheets
    )

    total_columns = max(
        [sheet["columns"] for sheet in analyzed_sheets],
        default=0
    )

    total_changes = sum(
        sheet["total_changes"]
        for sheet in analyzed_sheets
    )

    price = calculate_price(total_changes)

    return {
        "sheet_count": len(analyzed_sheets),

        "sheet_names": [
            sheet["name"]
            for sheet in analyzed_sheets
        ],

        "sheets": analyzed_sheets,

        "rows": total_rows,
        "columns": total_columns,

        "total_changes": total_changes,

        "price": price
    }


if __name__ == "__main__":

    result = analyze_file(
        "examples/test.xlsx"
    )

    print(result)

    print()
    print("Hojas:", result["sheet_names"])
    print("Cantidad de hojas:", result["sheet_count"])
    print("Cambios totales:", result["total_changes"])
