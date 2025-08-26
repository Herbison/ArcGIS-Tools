"""
MakeContractorBundle.py
-----------------------
Create a contractor-ready project by cloning a template and clipping all feature
layers in the first map to the provided search area. Empty clip results are removed.

Parameters (Script Tool suggestion)
----------------------------------
0: project_name (str)
1: search_area (Feature Set / Feature Layer)
2: launch_when_done (Boolean)
3: use_current_as_template (Boolean)
4: include_search_area (Boolean)  # currently not used to exclude it from clipping

Workflow
--------
1) Derive GIS root from CURRENT .aprx to find Projects root.
2) Create dated project folder and .gdb.
3) Clone template .aprx → new .aprx; set default GDB and folder connections.
4) For each feature layer in the first map:
   - Clip to `search_area` → new feature class in the new .gdb.
   - If result has features, add to the map; else delete the empty class.
   - Remove the original layer from the map.
5) Save and optionally launch ArcGIS Pro with the new project.

Notes
-----
- Layer names are used as output feature class names (must be valid in a file gdb).
- If name conflicts are possible, consider sanitizing or uniquifying names.
"""

import arcpy
import os
import subprocess
from datetime import datetime
import arctools as tools


def make_contractor_bundle(project_name: str,
                           search_area,
                           launch_when_done: bool,
                           use_current_as_template: bool,
                           include_search_area: bool):
    """
    Build a contractor bundle project, clipping all feature layers to `search_area`.

    Parameters
    ----------
    project_name : str
        A base name (without date prefix). The function prepends YYYYMMDD_.
    search_area : arcpy.FeatureSet | arcpy._mp.Layer | str
        The polygon(s) to clip to. Must be a valid feature input for arcpy.analysis.Clip.
    launch_when_done : bool
        If True, launch ArcGIS Pro with the new .aprx after building.
    use_current_as_template : bool
        If True, use the CURRENT project as the template; otherwise use "_ContractorTemplate".
    include_search_area : bool
        Reserved for logic to exclude the search layer from being clipped (not active).

    Returns
    -------
    None
    """
    # Build a dated project name to enforce uniqueness
    today_str = datetime.now().strftime("%Y%m%d")
    dated_project_name = f"{today_str}_{project_name.strip()}"

    current_project = arcpy.mp.ArcGISProject("CURRENT")
    gis_root = tools.get_gis_root_from_aprx(current_project.filePath)
    projects_root = os.path.join(gis_root, "Projects")

    # Choose template .aprx path
    template_path = (current_project.filePath
                     if use_current_as_template
                     else tools.get_template_path("_ContractorTemplate"))

    # Create folder structure
    project_folder = tools.create_project_folders(projects_root, dated_project_name)
    new_aprx_path = os.path.join(project_folder, f"{dated_project_name}.aprx")
    new_geodatabase_path = os.path.join(project_folder, f"{dated_project_name}.gdb")

    arcpy.AddMessage(f"📦 Creating new project: {dated_project_name}")

    # Clone project from template and set environment
    # Add a folder connection back to the project folder so relative adds work smoothly
    new_project = tools.clone_project(
        template_path=template_path,
        new_project_path=new_aprx_path,
        geodatabase_path=new_geodatabase_path,
        additional_folder_connections=[project_folder]
    )

    # Use the first map in the project (by convention)
    project_map = new_project.listMaps()[0]
    arcpy.AddMessage(f"📁 Creating from map: {project_map}")

    # Collect all feature layers (not filtered by visibility here)
    feature_layers = tools.get_all_feature_layers(
        project_map.listLayers(),
        visible_only=False,
        include_groups=False
    )

    # If later you want to exclude the search area layer itself from clipping,
    # you could compare dataSources or use a unique layer name tag and filter.

    arcpy.AddMessage("✂️ Clipping feature layers...")
    output_paths_to_add = []
    original_layers_to_remove = []

    for feature_layer in feature_layers:
        output_feature_class_path = os.path.join(new_geodatabase_path, feature_layer.name)
        arcpy.AddMessage(f"  ➤ {feature_layer.name} → {output_feature_class_path}")

        # Perform the clip
        arcpy.analysis.Clip(
            in_features=feature_layer.dataSource,
            clip_features=search_area,
            out_feature_class=output_feature_class_path
        )

        # Always mark original for removal; we'll re-add only non-empty outputs
        original_layers_to_remove.append(feature_layer)

        # Keep only non-empty results
        feature_count = int(arcpy.management.GetCount(output_feature_class_path)[0])
        if feature_count > 0:
            output_paths_to_add.append(output_feature_class_path)
        else:
            arcpy.AddMessage(f"  ⚠️ {feature_layer.name} has no features in search area; deleting.")
            arcpy.management.Delete(output_feature_class_path)

    # Add successful outputs to the map
    for dataset_path in output_paths_to_add:
        project_map.addDataFromPath(dataset_path)

    # Remove the originals from the map
    for feature_layer in original_layers_to_remove:
        project_map.removeLayer(feature_layer)

    # Persist changes
    new_project.save()
    arcpy.AddMessage("✅ Contractor project updated.")

    # Optionally launch the new project in ArcGIS Pro
    if launch_when_done:
        subprocess.Popen([r"C:\Program Files\ArcGIS\Pro\bin\ArcGISPro.exe", new_aprx_path])


if __name__ == "__main__":
    # Script tool parameter bindings
    project_name_param = arcpy.GetParameterAsText(0)
    search_area_param = arcpy.GetParameter(1)
    launch_when_done_param = arcpy.GetParameter(2)
    use_current_as_template_param = arcpy.GetParameter(3)
    include_search_area_param = arcpy.GetParameter(4)

    make_contractor_bundle(project_name_param,
                           search_area_param,
                           launch_when_done_param,
                           use_current_as_template_param,
                           include_search_area_param)
