"""
MakeNewProject.py
-----------------
Create a new ArcGIS Pro project (.aprx) from a template, with a prefix + base
name and a new file geodatabase. Optionally launch the project after creation.

Parameters (Script Tool suggestion)
----------------------------------
0: project_name (str)                  # Base name (e.g., "FortHuachuca")
1: launch_when_done (Boolean)          # Default: True
2: use_current_as_template (Boolean)   # If True, use CURRENT; else "_BaseTemplate"
3: custom_prefix (str, optional)       # If blank, default to today's date (YYYYMMDD)

Behavior
--------
- If custom_prefix is blank → prefix = YYYYMMDD
- Else → prefix = custom_prefix (sanitized)
- Final name = "{prefix}_{sanitized_project_name}" (avoids double underscores)
"""

import arcpy
import os
import subprocess
import re
from datetime import datetime
import arctools as tools


def make_new_project(project_name: str,
                     launch_when_done: bool,
                     use_current_as_template: bool,
                     custom_prefix: str = "") -> None:
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
    custom_prefix : str, optional
        Optional prefix for the new project name. If empty/blank, today's date
        (YYYYMMDD) will be used.

    Returns
    -------
    None
    """
    # Sanitizers
    invalid_filename_chars = r'[\\/:*?"<>|]'

    # Determine prefix
    if custom_prefix and custom_prefix.strip():
        raw_prefix = re.sub(invalid_filename_chars, "", custom_prefix.strip())
    else:
        raw_prefix = datetime.now().strftime("%Y%m%d")  # e.g., "20250827"

    # Ensure single underscore separation even if user typed a trailing "_"
    safe_prefix = raw_prefix.rstrip("_")

    # Sanitize the base name
    sanitized_base_name = re.sub(invalid_filename_chars, "", project_name.strip())

    # Compose final name
    full_project_name = f"{safe_prefix}_{sanitized_base_name}"

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
    project_name_param = arcpy.GetParameterAsText(0)         # Required
    launch_when_done_param = arcpy.GetParameter(1)            # Boolean
    use_current_as_template_param = arcpy.GetParameter(2)     # Boolean
    custom_prefix_param = arcpy.GetParameterAsText(3)         # Optional string

    make_new_project(project_name_param,
                     launch_when_done_param,
                     use_current_as_template_param,
                     custom_prefix_param)
