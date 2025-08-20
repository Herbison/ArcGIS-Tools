"""
ArcGIS Pro Project Initializer Script Tool
------------------------------------------
This script automates the creation of a new ArcGIS Pro project (.aprx) using a predefined template.
It performs the following steps:
1. Accepts a user-provided project base name (e.g., "FortHuachuca").
2. Prefixes that name with the current date (e.g., "20250723_") to create a unique project name.
3. Creates a new folder under ~\GIS\Projects\ using the full name.
4. Copies the base template .aprx into the new folder and renames it.
5. Creates a new File Geodatabase (.gdb) with the same name inside the folder.
6. Sets that geodatabase as the default for the new project.
7. Adds both the project folder and a newly created "_Exports" folder to the ArcGIS Pro Catalog.
8. Saves the project.
9. Launches ArcGIS Pro with the new project, if chosen.
Parameters:
    project_name (str): The user-provided base project name (e.g., "FortHuachuca").
    param1 (bool): Checkbox. Default is checked, and opens the new project when the tool is run.
This script is intended to be run as an ArcGIS Pro Script Tool, with `param0` set via the tool UI.
"""

"""
ADD
- Option to leave date off name
- Fail more verbosely/completely -Avoid making new project then failing, requiring deleting the folder before retry
"""

import arcpy
import os
import subprocess
import re
from datetime import datetime
import arcgis_utils as utils

def make_new_project(project_name: str, open_when_done: bool, use_current_as_template: bool):
    today = datetime.now().strftime("%Y%m%d")  # "18760213" for 13 June 1876"
    base_name = re.sub(r'[\\/:*?"<>|]', "", project_name.strip())
    full_name = f"{today}_{base_name}"
    """ option to not auto-strip
    if re.search(invalid_chars, proj_name):
        arcpy.AddError(f"❌ Project name contains invalid characters: {proj_name}")
        raise ValueError("Invalid project name")
    """

    current_aprx = arcpy.mp.ArcGISProject("CURRENT")
    gis_root = utils.get_gis_root_from_aprx(current_aprx.filePath)
    projects_root = os.path.join(gis_root, "Projects")

    template_path = current_aprx.filePath if use_current_as_template else utils.get_template_path("_BaseTemplate")
    proj_folder = utils.create_project_folders(projects_root, full_name)
    proj_aprx = os.path.join(proj_folder, f"{full_name}.aprx")
    gdb_path = os.path.join(proj_folder, f"{full_name}.gdb")

    arcpy.AddMessage(f"📁 Creating new project: {full_name}")
    aprx = utils.clone_project(template_path, proj_aprx, gdb_path, [os.path.join(proj_folder, "_Exports")])

    arcpy.AddMessage("✅ Project created successfully.")
    if open_when_done:
        subprocess.Popen([r"C:\Program Files\ArcGIS\Pro\bin\ArcGISPro.exe", proj_aprx])

if __name__ == "__main__":
    param0 = arcpy.GetParameterAsText(0)
    param1 = arcpy.GetParameter(1)
    param2 = arcpy.GetParameter(2)
    make_new_project(param0, param1, param2)
