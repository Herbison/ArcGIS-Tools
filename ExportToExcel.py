import arcpy
import os
import pandas as pd
import arctools as tools

def export_tables_to_excel(output_excel_path):
    aprx = arcpy.mp.ArcGISProject("CURRENT")
    map_obj = aprx.activeMap
    layers = tools.get_all_feature_layers(map_obj.listLayers(), visible_only=True)

    writer = pd.ExcelWriter(output_excel_path, engine="openpyxl")
    row_position = 0

    for lyr in layers:
        try:
            dataset_name = os.path.basename(lyr.dataSource)
            fields = [f.name for f in arcpy.ListFields(lyr.dataSource)]
            rows = arcpy.da.SearchCursor(lyr.dataSource, fields)
            df = pd.DataFrame(data=[list(r) for r in rows], columns=fields)

            pd.DataFrame({df.columns[0]: [dataset_name]}).to_excel(writer, startrow=row_position, index=False, header=False)
            row_position += 1
            df.to_excel(writer, startrow=row_position, index=False)
            row_position += len(df) + 1

        except Exception as e:
            arcpy.AddWarning(f"⚠️ Failed to export: {lyr.name}\n{e}")

    writer.close()
    arcpy.AddMessage(f"✅ Exported to Excel: {output_excel_path}")

if __name__ == "__main__":
    base_name = arcpy.GetParameterAsText(0).strip() or "KMZ Excel"
    if not base_name.lower().endswith(".xlsx"):
        base_name += ".xlsx"

    aprx = arcpy.mp.ArcGISProject("CURRENT")
    proj_folder = os.path.dirname(aprx.filePath)
    full_path = os.path.join(proj_folder, base_name)

    export_tables_to_excel(full_path)
