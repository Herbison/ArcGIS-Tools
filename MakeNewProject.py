import arcpy
import os
import subprocess
import re
from datetime import datetime
import arcgis_utils as utils

def script_tool(param0: str, open_when_done: bool, use_current_as_template: bool):
    today = datetime.now().strftime("%Y%m%d")
    base_name = re.sub(r'[\\/:*?"<>|]', "", param0.strip())
    full_name = f"{today}_{base_name}"

    current_aprx = arcpy.mp.ArcGISProject("CURRENT")
    gis_root = utils.get_gis_root_from_aprx(current_aprx.filePath)
    projects_root = os.path.join(gis_root, "Projects")

    template_path = current_aprx.filePath if use_current_as_template else utils.get_template_path("_BaseTemplate")
    proj_folder = utils.create_project_folders(projects_root, full_name)
    proj_aprx = os.path.join(proj_folder, f"{full_name}.aprx")
    gdb_path = os.path.join(proj_folder, f"{full_name}.gdb")

    arcpy.AddMessage(f"📁 Creating new project: {full_name}")
    aprx = utils.clone_project(template_path, proj_aprx, gdb_path, [proj_folder, os.path.join(proj_folder, "_Exports")])

    arcpy.AddMessage("✅ Project created successfully.")
    if open_when_done:
        subprocess.Popen([r"C:\Program Files\ArcGIS\Pro\bin\ArcGISPro.exe", proj_aprx])

if __name__ == "__main__":
    param0 = arcpy.GetParameterAsText(0)
    param1 = arcpy.GetParameter(1)
    param2 = arcpy.GetParameter(2)
    script_tool(param0, param1, param2)
