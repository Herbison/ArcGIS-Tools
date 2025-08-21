import arcpy
import os
import subprocess
from datetime import datetime

def get_all_feature_layers(layers):
    """
    Recursively collect all operational (non-basemap) feature layers
    from a list of layers, including inside group layers.
    """
    result = []
    for layer in layers:
        if layer.isGroupLayer:
            result.extend(get_all_feature_layers(layer.listLayers()))
        elif layer.isFeatureLayer and layer.supports("dataSource") and layer.supports("NAME") and not layer.isBasemapLayer:
            result.append(layer)
    return result

def make_contractor_bundle(project_name: str, search_area, launch_when_done: bool) -> None:
    """
    Generates a clipped subset project bundle for a contractor using a defined search area.
    
    Steps:
    1. Creates a dated project folder.
    2. Copies the Contractor Template APRX into it.
    3. Creates a new GDB inside the project folder.
    4. Clips all operational feature layers to the search area.
    5. Saves the results into the new GDB.
    6. Removes original layers and adds the clipped layers to the map.
    7. Optionally opens the project in ArcGIS Pro.
    """

    contractor_template_aprx = r"C:\GIS\Projects\_ContractorTemplate\_ContractorTemplate.aprx"
    projects_root_directory = r"C:\GIS\Projects"
    today = datetime.now().strftime("%Y%m%d")
    full_project_name = f"{today}_{project_name}"
    project_folder = os.path.join(projects_root_directory, full_project_name)
    project_aprx_path = os.path.join(project_folder, f"{full_project_name}.aprx")
    project_gdb_name = f"{full_project_name}.gdb"
    project_gdb_path = os.path.join(project_folder, project_gdb_name)

    if os.path.exists(project_folder):
        arcpy.AddError(f"❌ Project folder already exists: {project_folder}")
        raise FileExistsError(f"Folder exists: {project_folder}")
    os.makedirs(project_folder)

    arcpy.AddMessage(f"📁 Creating project from template: {full_project_name}")
    aprx = arcpy.mp.ArcGISProject(contractor_template_aprx)
    aprx.saveACopy(project_aprx_path)

    arcpy.AddMessage("🗃️ Creating project geodatabase...")
    arcpy.management.CreateFileGDB(project_folder, project_gdb_name)

    aprx = arcpy.mp.ArcGISProject(project_aprx_path)
    aprx.defaultGeodatabase = project_gdb_path
    project_map = aprx.listMaps()[0]

    arcpy.AddMessage("✂️ Clipping feature layers...")
    feature_layers_to_clip = get_all_feature_layers(project_map.listLayers())

    layers_to_remove = []

    for layer in feature_layers_to_clip:
        base_name = os.path.splitext(os.path.basename(layer.dataSource))[0]
        output_feature_class = arcpy.CreateUniqueName(base_name, project_gdb_path) # Automatically appends a suffix (_1, _2, etc.) until the name is unique. No suffix if unique.

        arcpy.AddMessage(f"  ➤ {layer.name} → {output_feature_class}")

        arcpy.analysis.Clip(
            in_features=layer.dataSource,
            clip_features=search_area,
            out_feature_class=output_feature_class
        )

        layers_to_remove.append(layer)
        project_map.addDataFromPath(output_feature_class)


    for layer in layers_to_remove:
        project_map.removeLayer(layer)

    aprx.save()
    arcpy.AddMessage("✅ Clipped layers saved and project updated.")

    if launch_when_done:
        arcpy.AddMessage("🚀 Launching ArcGIS Pro...")
        subprocess.Popen([r"C:\Program Files\ArcGIS\Pro\bin\ArcGISPro.exe", project_aprx_path])

if __name__ == "__main__":
    user_project_name = arcpy.GetParameterAsText(0)
    search_area_layer = arcpy.GetParameter(1)
    open_when_done = arcpy.GetParameter(2)
    make_contractor_bundle(user_project_name, search_area_layer, open_when_done)