import arcpy
import os
import shutil
from datetime import datetime

# ─── PATH HELPERS ─────────────────────────────────────────────────────

def get_current_aprx():
    return arcpy.mp.ArcGISProject("CURRENT")

def get_gis_root_from_aprx(aprx_path: str):
    return os.path.abspath(os.path.join(os.path.dirname(aprx_path), "..", ".."))
# Looks up two folder levels to \GIS

def get_project_folder(aprx_or_path):
    """
    Return the folder that contains the .aprx file.
    Accepts either a string path or an ArcGISProject.
    """
    if hasattr(aprx_or_path, "filePath"):   # ArcGISProject
        return os.path.dirname(aprx_or_path.filePath)
    return os.path.dirname(aprx_or_path)    # plain string path


def get_template_path(base_name: str): #Bad name when I have files named template
    aprx = get_current_aprx()
    gis_root = get_gis_root_from_aprx(aprx.filePath)
    return os.path.join(gis_root, "Projects", base_name, f"{base_name}.aprx")

def create_project_folders(projects_root, name, include_exports=True):
    proj_folder = os.path.join(projects_root, name)
    if os.path.exists(proj_folder):
        raise FileExistsError(f"❌ Project folder already exists: {proj_folder}")
    os.makedirs(proj_folder)
    if include_exports:
        os.makedirs(os.path.join(proj_folder, "_Exports"), exist_ok=True)
    os.makedirs(os.path.join(proj_folder, ".backups"), exist_ok=True)
    return proj_folder

# ─── LAYER FILTERING ──────────────────────────────────────────────────

def get_all_feature_layers(layers, parent_visible=True, visible_only=False, include_groups=False):
    output = []
    for lyr in layers:
        lyr_visible = lyr.visible and parent_visible
        if lyr.isGroupLayer:
            if include_groups and (not visible_only or lyr_visible):
                output.append(lyr)
            output.extend(get_all_feature_layers(lyr.listLayers(), lyr_visible, visible_only, include_groups))
        elif lyr.isFeatureLayer and lyr.supports("dataSource") and not lyr.isBasemapLayer:
            if not visible_only or lyr_visible:
                output.append(lyr)
    return output

# ─── PROJECT CLONING ──────────────────────────────────────────────────

def clone_project(template_path, new_path, gdb_path=None, add_folders=None):
    """
    Create a new project from template_path at new_path.
    - Sets the project's Home Folder to the folder that contains new_path.
    - Optionally creates/sets a default GDB.
    - Replaces folder connections with [Home, ...add_folders].
    """
    if add_folders is None:
        add_folders = []

    # 1) Copy template → new .aprx, then open it
    arcpy.mp.ArcGISProject(template_path).saveACopy(new_path)
    aprx = arcpy.mp.ArcGISProject(new_path)

    # 2) Create/set default GDB (if requested)
    if gdb_path:
        gdb_dir = os.path.dirname(gdb_path)
        gdb_name = os.path.basename(gdb_path)
        if not os.path.exists(gdb_path):
            arcpy.management.CreateFileGDB(gdb_dir, gdb_name)
        aprx.defaultGeodatabase = gdb_path

    # 3) Derive project folder from the path string
    proj_folder = os.path.dirname(new_path)

    # 4) Set Home Folder
    aprx.homeFolder = proj_folder  # must match one folder connection flagged as home

    # 5) Build folder connections from scratch
    def _norm(p): return os.path.normcase(os.path.abspath(p))
    home = _norm(proj_folder)

    folder_list = [{"connectionString": proj_folder, "alias": "", "isHomeFolder": True}]

    for p in add_folders:
        if not p:
            continue
        if _norm(p) == home: # Don't remember this part
            # don't add a duplicate of the home path
            continue
        folder_list.append({"connectionString": p, "alias": "", "isHomeFolder": False})

    aprx.updateFolderConnections(folder_list)  # validate=True by default
    aprx.save()
    return aprx