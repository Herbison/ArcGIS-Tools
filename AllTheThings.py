
import preferences
import arcpy
import os
import re
from datetime import datetime

def do_all_the_things(prefix: str, 
                      include_prefix: bool, 
                      base_project_name: str, 
                      search_area,
                      layers_to_clip,
                      export_to_kmz: bool,
                      export_to_excel: bool,
                      print_landscape: bool,
                      print_portrait: bool,
                      map_name: str,
                      apply_styling: bool):
    pass

def make_new_project(prefix: str,
                     base_project_name: str,
                     include_prefix: bool, 
                     launch_when_done: bool) -> None:

    project_name = make_project_name(prefix, include_prefix, base_project_name)
        # Need to rename this. base vs full name, changing it for below

    project_folder = create_project_folders(project_name)[0]

    """
 
    if len(project_folder) > 1:
        other_folders = create_project_folders(project_name)[1:]

    Done for now. Making connections twice, inefficiently
    """
    new_aprx = create_aprx(project_folder)
    _ = set_connections(new_aprx, project_folder, project_name)
    _ = rename_map(base_project_name, new_aprx)
    _ = make_connections(other_folders)



# Sanitize and create full project name
def make_project_name(prefix, include_prefix, project_name):
    invalid_filename_chars = r'[\\/:*?"<>|]'     
    valid_base_name = re.sub(invalid_filename_chars, "", project_name.strip())

    if include_prefix:
        valid_prefix = re.sub(invalid_filename_chars, "", prefix.strip())
        full_project_name = f"{valid_prefix}_{valid_base_name}"
    else:
        full_project_name = valid_base_name
    return full_project_name

def create_project_folders(project_name: str) -> list:
    project_folder = os.path.join(preferences.projects_folder, project_name)
    if os.path.exists(project_folder):
        raise FileExistsError(f"❌ Project folder already exists: {project_folder}")
    else:
        os.makedirs(project_folder)
    
    folder_list = [project_folder]
    for folder in preferences.folders_to_make:
        path = os.path.join(project_folder, folder)
        os.makedirs(path, exist_ok=True)
        folder_list.append

    return folder_list

def create_aprx(project_folder, template):
    """
    Make sure I'm keeping string/aprx straight
    """
    arcpy.mp.ArcGISProject(template).saveACopy(project_folder)
    new_project = arcpy.mp.ArcGISProject(project_folder)
    return new_project

def set_connections(new_aprx, project_folder, project_name):
    project_geodatabase = os.path.join(project_folder, f"{project_name}.gdb")
    if not os.path.exists(project_geodatabase):
        arcpy.management.CreateFileGDB(project_folder, project_name)
        new_aprx.defaultGeodatabase = project_geodatabase
    new_aprx.homeFolder = project_folder

def rename_map(base_project_name, new_aprx):
    for map in new_aprx.listMaps():
        if map.name == "_BaseTemplateMap":
            map.name = base_project_name

def make_connections(other_folders):
    pass


# 5) Build folder connections from scratch
def _normalized(path: str) -> str:
    """Return a normalized absolute path for equality checks (case-insensitive on Windows)."""
    return os.path.normcase(os.path.abspath(path))

normalized_home = _normalized(project_folder)
folder_connections = [{
    "connectionString": project_folder,
    "alias": "",
    "isHomeFolder": True
}]

for candidate_path in additional_folder_connections:
    if not candidate_path:
        continue
    if _normalized(candidate_path) == normalized_home:
        # Skip adding a duplicate of the home folder as a separate connection
        continue
    folder_connections.append({
        "connectionString": candidate_path,
        "alias": "",
        "isHomeFolder": False
    })