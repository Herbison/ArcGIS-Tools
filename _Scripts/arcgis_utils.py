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

def get_project_folder(aprx_path: str):
    return os.path.dirname(aprx_path)

def get_template_path(base_name: str):
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

def clone_project(template_path, new_path, gdb_path=None, add_folders=[]):
    aprx_template = arcpy.mp.ArcGISProject(template_path)
    aprx_template.saveACopy(new_path)

    aprx = arcpy.mp.ArcGISProject(new_path)
    proj_folder = get_project_folder(aprx)

    if gdb_path:
        arcpy.management.CreateFileGDB(os.path.dirname(gdb_path), os.path.basename(gdb_path))
        aprx.defaultGeodatabase = gdb_path

    folders = [dict(f, isHomeFolder=False) for f in aprx.folderConnections]
    folders.append({"connectionString": proj_folder, "alias": "", "isHomeFolder": True})
    for path in add_folders:
        folders.append({"connectionString": path, "alias": "", "isHomeFolder": False})
    aprx.updateFolderConnections(folders)
    aprx.save()
    return aprx