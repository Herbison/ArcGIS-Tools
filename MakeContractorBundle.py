import arcpy
import os
import subprocess
from datetime import datetime
import arctools as tools

def make_contractor_bundle(project_name: str, search_area, launch_when_done: bool, use_current_as_template: bool): 
    
    today = datetime.now().strftime("%Y%m%d")
    full_name = f"{today}_{project_name.strip()}"

    current_aprx = arcpy.mp.ArcGISProject("CURRENT")
    gis_root = tools.get_gis_root_from_aprx(current_aprx.filePath)
    projects_root = os.path.join(gis_root, "Projects")
    template_path = current_aprx.filePath if use_current_as_template else tools.get_template_path("_ContractorTemplate")
    proj_folder = tools.create_project_folders(projects_root, full_name)
    proj_aprx = os.path.join(proj_folder, f"{full_name}.aprx")
    gdb_path = os.path.join(proj_folder, f"{full_name}.gdb")

    arcpy.AddMessage(f"📦 Creating new project: {full_name}")
    aprx = tools.clone_project(template_path, proj_aprx, gdb_path, [proj_folder])

    ### Everything up to here is redundant (w/ different Template) to MakeNewProject

    project_map = aprx.listMaps()[0]
    arcpy.AddMessage(f"📁 Creating from map: {project_map}")

    feature_layers = tools.get_all_feature_layers(project_map.listLayers())
    # Add option (and util)

    arcpy.AddMessage("✂️ Clipping feature layers...")
    new_paths = []
    layers_to_remove = []

    for layer in feature_layers:
        output_feature_class = os.path.join(gdb_path, layer.name)
        arcpy.AddMessage(f"  ➤ {layer.name} → {output_feature_class}")

        arcpy.analysis.Clip(
            in_features=layer.dataSource,
            clip_features=search_area,
            out_feature_class=output_feature_class
        )

        # check if clipped output has rows
        feature_count = int(arcpy.management.GetCount(output_feature_class)[0])
        if feature_count > 0:
            new_paths.append(output_feature_class)
        else:
            arcpy.AddMessage(f"  ⚠️ {layer.name} has no features in search area; excluding.")
        layers_to_remove.append(layer)

    for path in new_paths:
        project_map.addDataFromPath(path)

    for layer in layers_to_remove:
        project_map.removeLayer(layer)
    # This while thing could be neater, cleaner logic.

    ### ADD TO GDB

    aprx.save()
    arcpy.AddMessage("✅ Contractor project updated.")

    if launch_when_done:
        subprocess.Popen([r"C:\Program Files\ArcGIS\Pro\bin\ArcGISPro.exe", proj_aprx])

if __name__ == "__main__":
    project_name = arcpy.GetParameterAsText(0)
    search_area = arcpy.GetParameter(1)
    launch_when_done = arcpy.GetParameter(2)
    use_current_as_template = arcpy.GetParameter(3)
    make_contractor_bundle(project_name, search_area, launch_when_done, use_current_as_template)
