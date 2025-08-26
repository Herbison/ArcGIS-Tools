"""
MakeNewProject.py
-----------------
Create a new ArcGIS Pro project (.aprx) from a template, with a dated name
and a new file geodatabase. Optionally launch the project after creation.

Parameters (Script Tool suggestion)
----------------------------------
0: project_name (str)                  # Base name (e.g., "FortHuachuca")
1: launch_when_done (Boolean)          # Default: True
2: use_current_as_template (Boolean)   # If True, use CURRENT as template; else "_BaseTemplate"

Workflow
--------
1) Sanitize the provided base name and prepend today's date (YYYYMMDD_).
2) Resolve GIS root via CURRENT .aprx to find Projects root.
3) Create the project folder (and _Exports, .backups).
4) Clone template .aprx → new .aprx; create and set default .gdb.
5) Add folder connections (project folder and _Exports).
6) Optionally launch ArcGIS Pro with the new .aprx.

Notes
-----
- Name sanitization removes characters invalid for Windows filenames.
- If you want to optionally omit the date prefix, add a new parameter and branch.
"""

import arcpy
import os
import subprocess
import re
from datetime import datetime
import arctools as tools


def make_new_project(project_name: str,
                     launch_when_done: bool,
                     use_current_as_template: bool) -> None:
    """
    Create a new project from a template and configure default paths.

    Parameters
    ----------
    project_name : str
        Human-friendly base name; invalid characters will be stripped.
    launch_when_done : bool
        If True, open the project in ArcGIS Pro after creation.
    use_current_as_template : bool
        If True, clone from CURRENT .aprx; else use "_BaseTemplate".

    Returns
    -------
    None
    """
    # Date prefix (YYYYMMDD) for uniqueness and chronological ordering
    today_str = datetime.now().strftime("%Y%m%d")  # e.g., "20250826"

    # Sanitize the input name to remove characters disallowed in Windows filenames
    invalid_filename_chars = r'[\\/:*?"<>|]'
    sanitized_base_name = re.sub(invalid_filename_chars, "", project_name.strip())

    full_project_name = f"{today_str}_{sanitized_base_name}"

    # Derive project roots based on the CURRENT .aprx location
    current_project = arcpy.mp.ArcGISProject("CURRENT")
    gis_root = tools.get_gis_root_from_aprx(current_project.filePath)
    projects_root = os.path.join(gis_root, "Projects")

    # Choose template path
    template_path = (current_project.filePath
                     if use_current_as_template
                     else tools.get_template_path("_BaseTemplate"))

    # Create folder structure and paths
    project_folder = tools.create_project_folders(projects_root, full_project_name)
    new_aprx_path = os.path.join(project_folder, f"{full_project_name}.aprx")
    new_geodatabase_path = os.path.join(project_folder, f"{full_project_name}.gdb")
    exports_folder = os.path.join(project_folder, "_Exports")

    arcpy.AddMessage(f"📁 Creating new project: {full_project_name}")

    # Clone template and configure: default GDB + folder connections (home + _Exports)
    new_project = tools.clone_project(
        template_path=template_path,
        new_project_path=new_aprx_path,
        geodatabase_path=new_geodatabase_path,
        additional_folder_connections=[exports_folder]
    )

    arcpy.AddMessage("✅ Project created successfully.")

    # Optional launch
    if launch_when_done:
        subprocess.Popen([r"C:\Program Files\ArcGIS\Pro\bin\ArcGISPro.exe", new_aprx_path])


if __name__ == "__main__":
    # Script tool parameter bindings
    project_name_param = arcpy.GetParameterAsText(0)
    launch_when_done_param = arcpy.GetParameter(1)
    use_current_as_template_param = arcpy.GetParameter(2)

    make_new_project(project_name_param,
                     launch_when_done_param,
                     use_current_as_template_param)
