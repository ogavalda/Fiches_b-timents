import os
from core import *
from jinja2 import Environment, FileSystemLoader
from geomeppy import IDF
from core_2 import (
    load_weather,
    load_households,
    load_ope,
    process_energy_data,
    plot_banana
)
import shutil
from Daily_profile import *
from cons_data_full import *

weather_df = load_weather(r"MURBS_2026\outdoor_temperature_no_year.csv")
households_dict = load_households(r"MURBS_2026\dadesarquetips.csv")
ope_df = load_ope(r"MURBS_2026\dataOPE.csv")

def process_building(building_path, template_path, idd_path, operation_folder, view_folder):

    folder_name = os.path.basename(building_path)
    parts = folder_name.split("_")

    building_id = parts[0]
    building_type = parts[1]
    building_name = parts[2]
    building_vintage = parts[3]

    run_path = os.path.join(building_path, f"{folder_name}/run")
    output_path = os.path.join(building_path, "output")
    os.makedirs(output_path, exist_ok=True)

    osm = os.path.join(building_path, f"{folder_name}.osm")
    idf_path = os.path.join(run_path, "in.idf")
    html = os.path.join(run_path, "eplustbl.htm")

    model = load_model(osm)

    if os.path.exists(idd_path):
        IDF.setiddname(idd_path)

    idf = IDF(idf_path)

    geom_img = os.path.join(output_path, "geometry.png")
    view_geometry(idf, geom_img)

    floor_area, stories, space_count, climate_zone = building_description(model)
    energy = extract_energy(html)
    end_uses = extract_end_uses(html)
    wwr = compute_wwr(html).values.tolist()

    monthly_img = os.path.join(output_path, "monthly.png")
    monthly_img_fr = os.path.join(output_path, "monthly_fr.png")
    json_path = os.path.join(run_path, "measure_attributes.json")

    construction_data = extract_construction_summary(html,json_path)




    create_monthly_plot(html, monthly_img, "eng")
    create_monthly_plot(html, monthly_img_fr, "fr")


    # for Banana Curve----------------------
    df,df_hourly = process_energy_data(
        f"{building_path}/{folder_name}",
        households_dict,
        ope_df,
        weather_df
    )
    Prism_plot_path = os.path.join(output_path, "banana.png")
    Prism_plot_path_fr = os.path.join(output_path, "banana_fr.png")
    plot_banana(df, Prism_plot_path,"eng")
    plot_banana(df, Prism_plot_path_fr, "fr")

    #for Daily profile
    Daily_P_plot_path = os.path.join(output_path, "daily_profiles.png")
    Daily_P_plot_path_fr = os.path.join(output_path, "daily_profiles_fr.png")
    plot_daily_profiles_ope_vs_meter(df_hourly, Daily_P_plot_path,"eng")
    plot_daily_profiles_ope_vs_meter(df_hourly, Daily_P_plot_path_fr, "eng")
    shutil.copy("MURBS_2026/logo_min.png", os.path.join(output_path, "logo_min.png"))
    shutil.copy("MURBS_2026/logo_hq.png", os.path.join(output_path, "logo_hq.png"))
    shutil.copy("MURBS_2026/logo_pm.png", os.path.join(output_path, "logo_pm.png"))
    shutil.copy("MURBS_2026/logo_conc.png", os.path.join(output_path, "logo_conc.png"))
    # Operation Report--------------------------------------------------------------------------------
    env = Environment(loader=FileSystemLoader(template_path))
    template = env.get_template("operation report.html")
    template_fr=env.get_template("operation report_fr.html")
    html_out = template.render(
        energy=energy,
        logo_min="logo_min.png",
        logo_hq="logo_hq.png",
        logo_pm="logo_pm.png",
        logo_conc="logo_conc.png",
        figure1_path="banana.png",
        figure2_path="daily_profiles.png",
        figure3_path = "geometry.png",
        building_name = building_name,
        vintage = building_vintage,
        construction_data=construction_data,
        floor_area=floor_area,
        stories=stories,
        climate_zone=climate_zone,
        wwr=wwr,
        end_uses=end_uses,

    )

    output_html = os.path.join(output_path, "Operation report.html")

    with open(output_html, "w", encoding="utf-8") as f:
        f.write(html_out)

    operation_folder_path = os.path.join(operation_folder, f"{folder_name}.html")

    with open(operation_folder_path, "w", encoding="utf-8") as f:
        f.write(html_out)
    html_out_fr = template_fr.render(
        energy=energy,
        logo_min="logo_min.png",
        logo_hq="logo_hq.png",
        logo_pm="logo_pm.png",
        logo_conc="logo_conc.png",
        figure1_path="banana_fr.png",
        figure2_path="daily_profiles_fr.png",
        figure3_path="geometry.png",
        building_name=building_name,
        vintage=building_vintage,
        construction_data=construction_data,
        floor_area=floor_area,
        stories=stories,
        climate_zone=climate_zone,
        wwr=wwr,
        end_uses=end_uses,

    )

    output_html_fr = os.path.join(output_path, "Operation report_fr.html")

    with open(output_html_fr, "w", encoding="utf-8") as f:
        f.write(html_out_fr)

    operation_folder_path = os.path.join(operation_folder, f"{folder_name}.html")

    with open(operation_folder_path, "w", encoding="utf-8") as f:
        f.write(html_out_fr)

    #----------------------------------------------------------------------------------------------------

    # View Report ---------------------------------------------------------------------------------------
    env = Environment(loader=FileSystemLoader(template_path))
    template = env.get_template("view report.html")
    template_fr = env.get_template("view report_fr.html")

    html_out = template.render(
        building_name=building_name,
        vintage=building_vintage,
        logo_min="logo_min.png",
        logo_hq="logo_hq.png",
        logo_pm="logo_pm.png",
        logo_conc="logo_conc.png",
        floor_area=floor_area,
        stories=stories,
        climate_zone=climate_zone,
        construction_data=construction_data,
        energy=energy,
        wwr=wwr,
        end_uses=end_uses,
        figure3_path="geometry.png",
        monthly_chart="monthly.png"
    )

    output_html = os.path.join(output_path, "View report.html")

    with open(output_html, "w", encoding="utf-8") as f:
        f.write(html_out)

    view_folder_path = os.path.join(view_folder, f"{folder_name}.html")

    with open(view_folder_path, "w", encoding="utf-8") as f:
        f.write(html_out)

    html_out_fr = template_fr.render(
        building_name=building_name,
        vintage=building_vintage,
        logo_min="logo_min.png",
        logo_hq="logo_hq.png",
        logo_pm="logo_pm.png",
        logo_conc="logo_conc.png",
        floor_area=floor_area,
        stories=stories,
        climate_zone=climate_zone,
        construction_data=construction_data,
        energy=energy,
        wwr=wwr,
        end_uses=end_uses,
        figure3_path="geometry.png",
        monthly_chart="monthly_fr.png"
    )

    output_html_fr = os.path.join(output_path, "View report_fr.html")

    with open(output_html_fr, "w", encoding="utf-8") as f:
        f.write(html_out_fr)

    view_folder_path = os.path.join(view_folder, f"{folder_name}.html")

    with open(view_folder_path, "w", encoding="utf-8") as f:
        f.write(html_out_fr)

    return output_html_fr



# =========================
# SINGLE TEST RUN  Just for testing just ignore
# =========================
if __name__ == "__main__":

    # 🔹 FULL path to ONE building folder (must contain .osm + run/)
    building_path = r"C:\Users\Mahmoud\OneDrive - Concordia University - Canada\Phase 2 Office Buildings\cards\Trial single\ID47_HR_AJ_19802010"

    # 🔹 Folder containing report.html
    template_path = r"C:\Users\Mahmoud\OneDrive - Concordia University - Canada\Phase 2 Office Buildings\cards\Trial single"

    operation_folder = r"C:\Users\Mahmoud\OneDrive - Concordia University - Canada\Phase 2 Office Buildings\cards\Trial single\ID47_HR_AJ_19802010\operation"
    view_folder = r"C:\Users\Mahmoud\OneDrive - Concordia University - Canada\Phase 2 Office Buildings\cards\Trial single\ID47_HR_AJ_19802010\view"

    # 🔹 EnergyPlus IDD (must exist if using geomeppy)
    idd_path = r"C:\EnergyPlusV25-2-0\Energy+.idd"

    print("=== TEST RUN START ===")

    try:
        output = process_building(building_path, template_path, idd_path,operation_folder, view_folder)
        print("✅ SUCCESS")
        print("Generated file:", output)

    except Exception as e:
        print("❌ ERROR DURING TEST RUN")
        print(e)

    print("=== TEST RUN END ===")