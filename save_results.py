import os
import shutil

def save_files(building_path, root, dest_folders):
    folder_name = os.path.basename(building_path)
    
    ### source locations
    # same as in "per_folder"
    run_path = os.path.join(building_path, f"{folder_name}/run")
    osm = os.path.join(building_path, f"{folder_name}.osm")
    idf_path = os.path.join(run_path, "in.idf")
    html = os.path.join(run_path, "eplustbl.htm")

    # reports generated from "per_folder" 
    output_path = os.path.join(building_path, "output")
    report_fr = os.path.join(output_path, "Fiche energie.pdf")
    report_en = os.path.join(output_path, "Energy card.pdf")



    ### destination locations
    # create directory for model results
    dest_path = root
    for folder in dest_folders:
        dest_path = dest_path + "\\" + folder
    os.makedirs(dest_path, exist_ok=True)

    # define all output locations
    path_results_osm = dest_path+"\\"+folder_name +".osm"
    path_results_html = dest_path+"\\eplustbl.htm" # simulation results summary
    path_results_idf = dest_path+"\\in.idf" # idf (for geometry)
    path_results_pdf_en = dest_path+"\\Energy card.pdf" # English pdf 
    path_results_pdf_fr = dest_path+"\\Fiche energie.pdf" # French pdf 


    # copy files to directory
    shutil.copyfile(osm, path_results_osm)
    shutil.copyfile(html, path_results_html)
    shutil.copyfile(idf_path, path_results_idf)
    shutil.copyfile(report_en, path_results_pdf_en)
    shutil.copyfile(report_fr, path_results_pdf_fr)

    return 0