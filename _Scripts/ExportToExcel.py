import arcpy
import pandas as pd
import os

def get_visible_feature_layers(layers, parent_visible=True):
    """
    Recursively traverse the given list of layers and return only those
    that are feature layers and effectively visible (i.e., they are visible
    *and* all their parent group layers are visible).
    """
    visible_layers = []
    for lyr in layers:
        lyr_visible = bool(lyr.visible) and parent_visible
        if lyr.isGroupLayer:
            # Descend into group, inheriting visibility from parent
            sublayers = lyr.listLayers()
            visible_layers.extend(
                get_visible_feature_layers(sublayers, parent_visible=lyr_visible)
            )
        else:
            # Include if it's a feature layer, supports dataSource, and effectively visible
            if lyr_visible and lyr.isFeatureLayer and lyr.supports("dataSource"):
                visible_layers.append(lyr)
    return visible_layers


def export_tables_to_excel(output_excel_path):
    aprx = arcpy.mp.ArcGISProject("CURRENT")
    map_obj = aprx.activeMap  # or aprx.listMaps()[0]

    all_layers = map_obj.listLayers()
    visible_layers = get_visible_feature_layers(all_layers)

    writer = pd.ExcelWriter(output_excel_path, engine='openpyxl')
    row_position = 0

    for layer in visible_layers:
        try:
            dataset_name = os.path.basename(layer.dataSource)
            fields = [f.name for f in arcpy.ListFields(layer.dataSource)]
            rows = arcpy.da.SearchCursor(layer.dataSource, fields)
            df = pd.DataFrame(data=[list(r) for r in rows], columns=fields)

            df_header = pd.DataFrame({df.columns[0]: [dataset_name]})
            df_header.to_excel(writer, startrow=row_position, index=False, header=False)
            row_position += 1

            df.to_excel(writer, startrow=row_position, index=False)
            row_position += len(df) + 1

        except Exception as e:
            arcpy.AddWarning(f"⚠️ Failed to export layer: {layer.name}\n{e}")

    writer.close()
    arcpy.AddMessage(f"✅ Exported tables to: {output_excel_path}")

# ─── Entry Point ─────────────────────────────────────────────────────
if __name__ == "__main__":
    # Get base filename (no path or extension expected)
    base_name = arcpy.GetParameterAsText(0).strip()
    if not base_name:
        base_name = "KMZ Excel"

    if not base_name.lower().endswith(".xlsx"):
        base_name += ".xlsx"

    aprx = arcpy.mp.ArcGISProject("CURRENT")
    project_folder = os.path.dirname(aprx.filePath)
    output_excel_path = os.path.join(project_folder, base_name)

    export_tables_to_excel(output_excel_path)
