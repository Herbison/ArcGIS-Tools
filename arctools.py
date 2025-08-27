"""
arctools.py
-----------
Utilities for working with ArcGIS Pro projects and layers.

Design goals:
- Extremely explicit naming (no ambiguous abbreviations).
- Clear documentation of side effects and assumptions.
- Functions are small, single-purpose, and easy to test.
"""

import arcpy
import os
from typing import Dict, Any
import shutil  # NOTE: currently unused; kept in case future file ops are added
from datetime import datetime  # NOTE: currently unused; kept for symmetry with other scripts


# ───────────────────────────────────────────────────────────────────────────────
# PATH HELPERS
# ───────────────────────────────────────────────────────────────────────────────

"""
TODO: Return Current project as .aprx/string, project folder as path (string, yeah?), above that to _Projects folder, and above that to GIS
Each of those as clearly labeled:
- get_current_aprx
- get_current_aprx_path
- get_current_folder_path
- get_Projects_path
- get_GIS_path
TODO: Once that's done, update references in other scripts
What's the best way to do so quickly?
- Think about reference passing
TODO: Find a way to generalize further, away from my folder layout
- Make a Class to set folder structure once 
"""

def get_current_aprx():
    """
    Return
    ------
    arcpy.mp.ArcGISProject
        The ArcGISProject object for the *currently open* .aprx in ArcGIS Pro.

    Notes
    -----
    - This returns an object, not a string path.
    - Use `.filePath` to get the full path to the .aprx file, and `.homeFolder`
      to get the designated home folder.
    """
    return arcpy.mp.ArcGISProject("CURRENT")


def get_gis_root_from_aprx(aprx_path: str) -> str:
    """
    Infer the GIS root folder by walking up two directories from an .aprx path.

    Parameters
    ----------
    aprx_path : str
        Full path to a .aprx file, e.g., r"C:\GIS\Projects\MyProj\MyProj.aprx".

    Returns
    -------
    str
        Absolute path to the inferred GIS root folder, e.g., r"C:\GIS".

    Assumptions
    -----------
    - Your project path structure is ...\GIS\Projects\<ProjectName>\<ProjectName>.aprx
      This climbs up two levels from the .aprx file:
        <aprx>\..  → <ProjectName> folder
        <aprx>\..\.. → "Projects" folder's parent (expected to be "GIS")
    """
    return os.path.abspath(os.path.join(os.path.dirname(aprx_path), "..", ".."))


# Could add this check for aprx/path in others, like get GIS folder
def get_project_folder(aprx_or_path):
    """
    Get the folder that contains a given ArcGIS Pro project (.aprx).

    Parameters
    ----------
    aprx_or_path : arcpy.mp.ArcGISProject | str
        Either an ArcGISProject object or a string path to an .aprx.

    Returns
    -------
    str
        The directory containing the .aprx file.

    Notes
    -----
    - If an ArcGISProject is provided, we read `.filePath`.
    - If a string path is provided, we take its directory.
    """
    if hasattr(aprx_or_path, "filePath"):   # ArcGISProject instance
        return os.path.dirname(aprx_or_path.filePath)
    return os.path.dirname(aprx_or_path)    # Plain string path


def get_template_path(base_name: str) -> str:
    """
    Resolve an .aprx template path under <GIS root>\\Projects\\<base_name>\\<base_name>.aprx.

    Parameters
    ----------
    base_name : str
        The folder and file stem (e.g., "_BaseTemplate", "_ContractorTemplate").

    Returns
    -------
    str
        Full path to the target template .aprx.

    Implementation detail
    ---------------------
    - Uses the CURRENT project to infer <GIS root>.
    """
    current_project = get_current_aprx()
    gis_root = get_gis_root_from_aprx(current_project.filePath)
    return os.path.join(gis_root, "Projects", base_name, f"{base_name}.aprx")

# Taking out optional folders for now. Everyone gets Export.
# Taking out backup folder, but I'll leave the lines. Look into what it does more.
def create_project_folders(projects_root: str,
                           project_name: str,) -> str:
    """
    Create the on-disk folder structure for a new project.

    Parameters
    ----------
    projects_root : str
        Path to the Projects root (e.g., r"C:\GIS\Projects").
    project_name : str
        Name for the new project folder (e.g., "20250826_FortHuachuca").
    include_exports : bool, optional
        If True, create an "_Exports" subfolder, by default True.

    Returns
    -------
    str
        Full path to the newly created project folder.

    Raises
    ------
    FileExistsError
        If the project folder already exists.

    Side Effects
    ------------
    - Creates:
        <projects_root>\<project_name>\
        <projects_root>\<project_name>\_Exports   (optional)
        <projects_root>\<project_name>\.backups   (Commented out)
    """
    project_folder = os.path.join(projects_root, project_name)

    if os.path.exists(project_folder):
        raise FileExistsError(f"❌ Project folder already exists: {project_folder}")

    os.makedirs(project_folder)
    os.makedirs(os.path.join(project_folder, "_Exports"), exist_ok=True)
    # os.makedirs(os.path.join(project_folder, ".backups"), exist_ok=True)

    return project_folder


# ───────────────────────────────────────────────────────────────────────────────
# LAYER FILTERING
# ───────────────────────────────────────────────────────────────────────────────

def get_all_feature_layers(layers,
                           parent_visible: bool = True,
                           visible_only: bool = False,
                           include_groups: bool = False):
    """
    Recursively collect feature layers from a list of layers (including groups).

    Parameters
    ----------
    layers : list[arcpy.mapping.Layer | arcpy._mp.LayerFile]
        A list from Map.listLayers() or GroupLayer.listLayers().
    parent_visible : bool, optional
        Visibility state inherited from parent group(s); do not set directly.
    visible_only : bool, optional
        If True, only return layers that are *effectively visible*, i.e.,
        they and all parents are visible.
    include_groups : bool, optional
        If True, include group layers themselves in the output (when visible).

    Returns
    -------
    list
        Flattened list of layers that pass the filters.

    Behavior
    --------
    - Traverses group layers recursively.
    - Skips basemap layers.
    - For feature layers, checks for "dataSource" support before collecting.
    """
    collected_layers = []

    for layer in layers:
        effective_visibility = layer.visible and parent_visible

        if layer.isGroupLayer:
            # Optionally include the group layer itself
            if include_groups and (not visible_only or effective_visibility):
                collected_layers.append(layer)

            # Recurse into the group's children
            child_layers = layer.listLayers()
            collected_layers.extend(
                get_all_feature_layers(
                    child_layers,
                    parent_visible=effective_visibility,
                    visible_only=visible_only,
                    include_groups=include_groups
                )
            )
        elif layer.isFeatureLayer and layer.supports("dataSource") and not layer.isBasemapLayer:
            if not visible_only or effective_visibility:
                collected_layers.append(layer)

    return collected_layers


# ───────────────────────────────────────────────────────────────────────────────
# PROJECT CLONING
# ───────────────────────────────────────────────────────────────────────────────

def clone_project(template_path: str,
                  new_project_path: str,
                  geodatabase_path: str | None = None,
                  additional_folder_connections: list[str] | None = None):
    """
    Create a new .aprx from a template and configure its environment.

    Parameters
    ----------
    template_path : str
        Full path to the source .aprx template.
    new_project_path : str
        Full path to the destination .aprx to create.
    geodatabase_path : str | None, optional
        If provided, create (if missing) and set as the default file geodatabase.
    additional_folder_connections : list[str] | None, optional
        Extra folder connections to add (besides the home folder).

    Returns
    -------
    arcpy.mp.ArcGISProject
        The opened ArcGISProject pointing at `new_project_path`.

    Side Effects
    ------------
    - Saves a copy of the template .aprx to `new_project_path`.
    - Sets the project's home folder to the folder containing `new_project_path`.
    - Optionally creates and assigns a default file geodatabase.
    - Replaces folder connections with:
        [ {home folder, isHomeFolder=True}, *additional_folder_connections ]

    Notes
    -----
    - This function opens the newly created project and returns it; callers can
      then list maps, add layers, etc., and finally call `aprx.save()`.
    """
    if additional_folder_connections is None:
        additional_folder_connections = []

    # 1) Copy template → new .aprx, then open it
    arcpy.mp.ArcGISProject(template_path).saveACopy(new_project_path)
    new_project = arcpy.mp.ArcGISProject(new_project_path)

    # 2) Create/set default GDB (if requested)
    if geodatabase_path:
        geodatabase_directory = os.path.dirname(geodatabase_path)
        geodatabase_name = os.path.basename(geodatabase_path)
        if not os.path.exists(geodatabase_path):
            arcpy.management.CreateFileGDB(geodatabase_directory, geodatabase_name)
        new_project.defaultGeodatabase = geodatabase_path

    # 3) Derive project folder from the path string
    project_folder = os.path.dirname(new_project_path)

    # 4) Set Home Folder (must also exist as a connection flagged as home)
    new_project.homeFolder = project_folder

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

    # new_project.defaultToolbox = os.path.join(project_folder, "ArcTools.atbx")
    new_project.updateToolboxes([{"toolboxPath": new_project.defaultToolbox, "isDefaultToolbox": True}])
    new_project.updateFolderConnections(folder_connections)  # validate=True by default
    new_project.save()
    return new_project


# ───────────────────────────────────────────────────────────────────────────────
# PROJECT ENVIRONMENT INFO
# ───────────────────────────────────────────────────────────────────────────────

def describe_current_project_environment() -> Dict[str, Any]:
    """
    Return a comprehensive description of the CURRENT ArcGIS Pro project's environment.

    This function does NOT mutate the project. It only reads properties and performs
    filesystem checks for existence. Everything is spelled out explicitly; no abbreviated
    variable names are used.

    Returns
    -------
    Dict[str, Any]
        A dictionary with the following keys:

        Core project identity
        ---------------------
        - "project_file_path" : str
              Full path to the .aprx file on disk, including the filename.
              Example: r"C:\\GIS\\Projects\\FortHuachuca\\FortHuachuca.aprx"

        - "project_file_name" : str
              The .aprx filename only (basename).
              Example: "FortHuachuca.aprx"

        - "project_folder" : str
              The folder that physically contains the .aprx file (derived with dirname).
              Often, but not always, the same as the home folder.

        - "project_home_folder" : str
              The project's designated "Home Folder" (working directory) from ArcGIS Pro.
              This is a logical setting in the .aprx and may be different from the folder
              that contains the .aprx file.

        Defaults configured in the project
        ----------------------------------
        - "project_default_geodatabase" : str
              Path to the default file geodatabase set for this project.
              Example: r"C:\\GIS\\Projects\\FortHuachuca\\FortHuachuca.gdb"

        - "project_default_toolbox" : str
              Path to the default toolbox (.atbx or .tbx) set for this project.
              Example: r"C:\\GIS\\Projects\\FortHuachuca\\FortHuachuca.atbx"

        Resolved checks and convenience flags
        -------------------------------------
        - "exists_project_file_path" : bool
        - "exists_project_folder" : bool
        - "exists_project_home_folder" : bool
        - "exists_project_default_geodatabase" : bool
        - "exists_project_default_toolbox" : bool

        Additional context (non-exhaustive)
        -----------------------------------
        - "map_names" : list[str]
              Names of maps in the project (in order returned by ArcGIS).

        - "layout_names" : list[str]
              Names of layouts in the project.

        - "folder_connections" : list[dict]
              Raw folder connection entries as returned by ArcGIS Pro. Each entry is a
              dictionary with keys such as "connectionString", "alias", "isHomeFolder".
              The entry with isHomeFolder=True should correspond to the "project_home_folder".

    Notes
    -----
    - The "default" properties (`project_default_geodatabase` and `project_default_toolbox`)
      are *project-level settings* that ArcGIS Pro uses as defaults for tools and outputs.
      They do not have to live in the same directory as the .aprx file.
    - The "home folder" is a logical working directory for the project and may be set to
      any accessible path; it is not required to match the physical location of the .aprx.
    """
    current_project = arcpy.mp.ArcGISProject("CURRENT")

    # Core identity
    project_file_path = current_project.filePath                         # full path to .aprx
    project_file_name = current_project.fileName                         # just the file name
    project_folder = os.path.dirname(project_file_path)                  # folder containing .aprx
    project_home_folder = current_project.homeFolder                     # ArcGIS Pro "Home" folder

    # Defaults (project-level)
    project_default_geodatabase = current_project.defaultGeodatabase     # path to .gdb
    project_default_toolbox = current_project.defaultToolbox             # path to .atbx or .tbx

    # Existence checks (best-effort sanity signals; not authoritative for permissions)
    exists_project_file_path = os.path.exists(project_file_path)
    exists_project_folder = os.path.isdir(project_folder)
    exists_project_home_folder = os.path.isdir(project_home_folder) if project_home_folder else False
    exists_project_default_geodatabase = os.path.isdir(project_default_geodatabase) if project_default_geodatabase else False
    exists_project_default_toolbox = os.path.isfile(project_default_toolbox) if project_default_toolbox else False

    # Additional context
    map_names = [map_object.name for map_object in current_project.listMaps()]
    layout_names = [layout_object.name for layout_object in current_project.listLayouts()]

    # Folder connections as stored in the project (home should appear here with isHomeFolder=True)
    # Example entry: {"connectionString": r"C:\GIS\Projects\MyProj", "alias": "", "isHomeFolder": True}
    folder_connections = current_project.folderConnections

    return {
        # Core project identity
        "project_file_path": project_file_path,
        "project_file_name": project_file_name,
        "project_folder": project_folder,
        "project_home_folder": project_home_folder,

        # Defaults configured in the project
        "project_default_geodatabase": project_default_geodatabase,
        "project_default_toolbox": project_default_toolbox,

        # Resolved checks and convenience flags
        "exists_project_file_path": exists_project_file_path,
        "exists_project_folder": exists_project_folder,
        "exists_project_home_folder": exists_project_home_folder,
        "exists_project_default_geodatabase": exists_project_default_geodatabase,
        "exists_project_default_toolbox": exists_project_default_toolbox,

        # Additional context
        "map_names": map_names,
        "layout_names": layout_names,
        "folder_connections": folder_connections,
    }

def print_current_project_environment() -> None:
    project_info = describe_current_project_environment()
    for key_name, value in project_info.items():
        arcpy.AddMessage(f"{key_name}: {value}")
