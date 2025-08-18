import arcpy
import os
import subprocess
from datetime import datetime
import arcgis_utils as utils

def make_contractor_bundle(project_name: str, search_area, launch_when_done: bool):
    today = datetime.now().strftime("%Y%m%d")
    full_name = f"{today}_{project_name.strip()}"

    current_aprx = arcpy.mp.ArcGISProject("CURRENT")
    gis_root = utils.get_gis_root_from_aprx(current_aprx.filePath)
    projects_root = os.path.join(gis_root, "Projects")
    template_path = utils.get_template_path("_ContractorTemplate")

    proj_folder = utils.create_project_folders(projects_root, full_name)
    proj_aprx = os.path.join(proj_folder, f"{full_name}.aprx")
    gdb_path = os.path.join(proj_folder, f"{full_name}.gdb")

    arcpy.AddMessage(f"📦 Cloning contractor project: {full_name}")
    aprx = utils.clone_project(template_path, proj_aprx, gdb_path, [proj_folder])

    map_obj = aprx.listMaps()[0]
    feature_layers = utils.get_all_feature_layers(map_obj.listLayers())

    arcpy.AddMessage("✂️ Clipping feature layers...")
    new_paths = []
    for lyr in feature_layers:
        output_fc = os.path.join(gdb_path, lyr.name)
        arcpy.AddMessage(f"  ➤ {lyr.name} → {output_fc}")
        arcpy.analysis.Clip(lyr.dataSource, search_area, output_fc)
        new_paths.append(output_fc)
        map_obj.removeLayer(lyr)

    for path in new_paths:
        map_obj.addDataFromPath(path)

    aprx.save()
    arcpy.AddMessage("✅ Contractor project updated.")

    if launch_when_done:
        subprocess.Popen([r"C:\Program Files\ArcGIS\Pro\bin\ArcGISPro.exe", proj_aprx])

if __name__ == "__main__":
    project_name = arcpy.GetParameterAsText(0)
    search_area = arcpy.GetParameter(1)
    open_after = arcpy.GetParameter(2)
    make_contractor_bundle(project_name, search_area, open_after)
