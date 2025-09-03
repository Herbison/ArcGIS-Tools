"""
ExportToExcel.py 
----------------
Export attribute tables from *visible* feature layers in the active map
to a single Excel workbook. Each layer is preceded by a one-row label
containing the dataset (feature class) name.

Behavior:
- Iterates only layers that are effectively visible (respects group visibility).
- Writes each layer's full table to a single sheet (default sheet 'Sheet1'),
  stacked vertically: [label row] + [table], repeated for each layer.

Dependencies:
- pandas (with openpyxl engine)
- arcpy
- arctools.get_all_feature_layers for visibility-aware traversal
"""

import arcpy
import os
import pandas as pd
import re as re
import arctools as tools


def export_tables_to_excel(output_excel_path: str) -> None:
    """
    Export visible feature-layer attribute tables in the active map to an Excel file.

    Parameters
    ----------
    output_excel_path : str
        Full path to the Excel workbook to create (e.g., r"C:\...\KMZ Excel.xlsx").

    Notes
    -----
    - Overwrites if the file already exists.
    - Uses a single worksheet; layers are stacked with a dataset-name header row.
    - For very large tables, this will be memory- and time-intensive (pandas).
    """
    current_project = arcpy.mp.ArcGISProject("CURRENT")
    active_map = current_project.activeMap

    # Collect only effectively visible feature layers (respects group visibility)
    feature_layers = tools.get_all_feature_layers(
        active_map.listLayers(),
        visible_only=True,
        include_groups=False
    )

    # Create an Excel writer
    writer = pd.ExcelWriter(output_excel_path, engine="openpyxl")
    next_row_index = 0

    # Create an Excel writer
    writer = pd.ExcelWriter(output_excel_path, engine="openpyxl")

    for feature_layer in feature_layers:
        try:
            dataset_path = feature_layer.dataSource
            dataset_name = os.path.basename(dataset_path)

            # Build fields & dataframe
            field_names = [f.name for f in arcpy.ListFields(dataset_path)]
            with arcpy.da.SearchCursor(dataset_path, field_names) as cursor:
                rows = [list(row) for row in cursor]
            df = pd.DataFrame(rows, columns=field_names)

            # If the dataframe is empty, add a dummy blank row
            if df.empty:
                df = pd.DataFrame([{field_names[0]: ""}], columns=field_names)

            # Use layer name as sheet/tab name (Excel-safe)
            sheet_name = re.sub(r'[\[\]\:\*\?\/\\]', '', feature_layer.name)[:31]

            # Write one sheet per layer
            df.to_excel(
                writer,
                sheet_name=sheet_name,
                index=False
            )


        except Exception as exc:
            arcpy.AddWarning(f"⚠️ Failed to export: {feature_layer.name}\n{exc}")

    writer.close()
    arcpy.AddMessage(f"✅ Exported to Excel (one sheet per layer): {output_excel_path}")



if __name__ == "__main__":
    # Parameter 0: desired base filename (default "KMZ Excel")
    base_file_name = arcpy.GetParameterAsText(0).strip() or "KMZExcel"

    # Ensure .xlsx extension
    if not base_file_name.lower().endswith(".xlsx"):
        base_file_name += ".xlsx"

    current_project = arcpy.mp.ArcGISProject("CURRENT")
    project_folder = os.path.dirname(current_project.filePath)

    # Save into the current project's folder by default
    # Point specifically into the _Exports subfolder
    exports_folder = os.path.join(project_folder, "_Exports")
    os.makedirs(exports_folder, exist_ok=True)  # safety check

    full_output_path = os.path.join(exports_folder, base_file_name)

    export_tables_to_excel(full_output_path)