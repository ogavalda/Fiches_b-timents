"""
Application
SPDX - License - Identifier: LGPL - 3.0 - or -later
Copyright © 2025-2026 Université Polytechnique
                      Next-Generation Cities Institute, Concordia University
Code contributors: Kato Vanroy, kato.vanroy@polymtl.ca
                   Mahmoud Awad, mahmoud.awad@mail.concordia.ca
                   Oriol Gavalda, oriol.gavalda@concordia.ca
"""
import os

import re
import matplotlib
from config import team_id
from core import *
from jinja2 import Environment, FileSystemLoader
from geomeppy import IDF
from core_2 import (
    load_weather,
    load_households,
    load_ope,
    process_energy_data,
    plot_banana, get_hvac_system, size
)
import shutil
from Daily_profile import *
from cons_data_full import *
from helpers.idf_geoms import view_geometry as view_geometry_KV
from datetime import datetime
from playwright.sync_api import sync_playwright

from helpers.create_plots import (
    process_energy_data as process_energy_data_KV,
    plot_banana as plot_banana_KV, 
    create_monthly_plot as create_monthly_plot_KV, 
    plot_loadprofile_stacked as plot_daily_profiles_sim_KV, 
    plot_daily_profiles_ope_vs_meter as plot_daily_profiles_ope_vs_meter_KV
    )

from helpers.read_simulation import ReadSimulation # class to help load simulation results (query sql)
from helpers.extract_info import (
    extract_construction_summary as extract_construction_summary_KV, 
    get_infiltration, 
    get_building_characteristics, 
    get_folder_structure, 
    get_french_characteristic
    #french_name don't need to translate the buidling name
    )

households_dict = load_households(r"MURBS_2026\dadesarquetips.csv")

if team_id != 'poly':

    #paths : concordia
    weather_df = load_weather(r"MURBS_2026\outdoor_temperature_no_year.csv")
    ope_df = load_ope(r"MURBS_2026\dataOPE.csv")
else:
    #paths : poly
    # SFD
    weather_df = load_weather(r"SFD_2026\OPE_temps_new.csv")
    ope_df = load_ope(r"SFD_2026\dataOPE.csv")

    # Dup/Trip
    #weather_df = load_weather(r"DupTrip_2026\OPE_DupTrip_temps.csv")
    #ope_df = load_ope(r"DupTrip_2026\OPE_DupTrip.csv")

# --- Translation dictionaries (EN → FR) ---
TRANSLATIONS_FR = {
    # WWR facades
    "North": "Nord",
    "South": "Sud",
    "East": "Est",
    "West": "Ouest",
    "Average [%]":"Moyenne [%]",
    # End uses
    "Heating": "Chauffage",
    "Cooling": "Refroidissement",
    "Interior Lighting": "Éclairage intérieur",
    "Exterior Lighting": "Éclairage extérieur",
    "Interior Equipment": "Équipements intérieurs",
    "Exterior Equipment": "Équipements extérieurs",
    "Fans": "Ventilateurs",
    "Pumps": "Pompes",
    "Heat Rejection": "Rejet de chaleur",
    "Humidification": "Humidification",
    "Heat Recovery": "Récupération de chaleur",
    "Water Systems": "Systèmes d'eau chaude",
    "Refrigeration": "Réfrigération",
    "Generators": "Générateurs",
    "Total End Uses": "Total des usages",
    # Construction data
    "Exterior walls [W/m²/K]": "Murs extérieurs [W/m²/K]",
    "Interior walls [W/m²/K]": "Murs intérieurs [W/m²/K]",
    "Roof [W/m²/K]": "Toit [W/m²/K]",
    "Slabs [W/m²/K]": "Dalles [W/m²/K]",
    "Glazing [W/m²/K]": "Vitrage [W/m²/K]",
    "SHGC": "FCS",
    "Infiltration [m³/h/m²]": "Infiltration [m³/h/m²]",
    "Infiltration (ELA @4Pa) [cm²]" :"Infiltration (ELA @4Pa) [cm²]",
    # HVAC systems
    "Cooling system":"Système de climatisation",
    "Heating system":"Système de chauffage", 
    "Ventilation system":"Système de ventilation",
    "Typical COP cooling":"COP typique en climatisation",
    "Air-Source Heat Pump (Mini-Split)":"Thermopompe à air (mini-split)", 
    "Electric Baseboards":"Plinthes électriques", 
    "No central ventilation":"Aucun système de ventilation centrale", 
    "Central Electric Heat Pump System":"Système centrale avec thermopompe", 
    "Central Heat Pump / Boiler":"Système centrale avec thermopompe et chaurière", 
    "Electric Boiler with hydronic baseboard heaters":"Chaudière électrique avec plinthes hydroniques",
    "Electric Boiler with hydronic baseboard heaters for perimeter": "Chaudière électrique avec plinthes hydroniques périphériques",
    "Constant air volume with recirculation and terminal reheat":"Système à volume constant avec recirculation"
}

def translate_dict(d, translations):
    """Return a new dict with keys translated, falling back to original key if not found."""
    return {translations.get(k, k): v for k, v in d.items()}

def translate_dict_values(d, translations):
    """Return a new dict with keys translated, falling back to original key if not found."""
    return {k:translations.get(v, v)for k, v in d.items()}

def translate_list_of_rows(rows, translations):
    """Translate first element of each [key, value] row."""
    return [[translations.get(row[0], row[0])] + row[1:] for row in rows]

def process_building(building_path, template_path, idd_path, operation_folder, view_folder):

    matplotlib.use("agg")

    ############ GENERAL ###############
    
    folder_name = os.path.basename(building_path)
    building_characteristics = get_building_characteristics(folder_name)

    building_sector = building_characteristics["sector"]
    building_type = building_characteristics["building_type"]
    building_subtype = building_characteristics["building_subtype"]
    building_name = building_characteristics["building_name"]
    #building_name_fr = french_name(building_name)
    building_vintage = building_characteristics["vintage"]
    size_of_build = building_characteristics["size"]
    building_shape = building_characteristics["building_shape"]
    print("building characteristics : done")


    run_path = os.path.join(building_path, f"{folder_name}/run")
    output_path = os.path.join(building_path, "output")
    os.makedirs(output_path, exist_ok=True)

    osm = os.path.join(building_path, f"{folder_name}.osm")
    idf_path = os.path.join(run_path, "in.idf")
    html = os.path.join(run_path, "eplustbl.htm")

    model = load_model(osm)

    # NEW : only grab json for concordia models 
    if team_id == 'poly':
        pass
    else:
        json_path = os.path.join(run_path, "measure_attributes.json")

    # NEW : added "simulation object" for easy access to data in sql file
    sim_object = ReadSimulation(run_path) 


    ############ PAGE 1 ###############

    # --------------------------------
    # GEOMETRY FIGURE
    # --------------------------------

    # NEW : modified how geometry is fetched - directly from idf path (not object) - concentrate all eppy related things in seperate file
    geom_img = os.path.join(output_path, "geometry.png")
    view_geometry_KV(idd_path, idf_path, geom_img)

    ### previous method : 
    #if os.path.exists(idd_path):
    #    IDF.setiddname(idd_path)
    #idf = IDF(idf_path)
    #geom_img = os.path.join(output_path, "geometry.png")
    #view_geometry(idf, geom_img)

    # --- Building description ---
    # TODO : remove stories here, since the osm doesn't provide a reliable way of fetching that info, 
    # we got a "size" descriptor from the file name in earlier code 
    floor_area, stories, space_count, climate_zone = building_description(model)
    print("building description : done")

    # --- Energy extraction ---
    energy = extract_energy(html)
    end_uses = extract_end_uses(html)
    wwr = compute_wwr_new(html).values.tolist()
    # TODO : make function compatible with both model structures
    if team_id=='poly':
        # NEW : added different infiltration identifier for SFD since it uses a different approach
        # TODO : figure out way to just have the names/units in one location. Currently need to make modifications in too many places
        construction_data_filter = [
            'Exterior walls [W/m²/K]',
            'Interior walls [W/m²/K]',
            'Roof [W/m²/K]',
            'Slabs [W/m²/K]',
            'Infiltration (ELA @4Pa) [cm²]'
        ]
        glazing_data_filter = [
            'SHGC',
            'Glazing [W/m²/K]'
        ]
        
        if building_sector != "Residential":
            construction_data_filter[-1] = 'Infiltration (I_design) [m³/h/m²]'
        
    else:
        construction_data_filter = [
            'Exterior walls [W/m²/K]',
            'Interior walls [W/m²/K]',
            'Roof [W/m²/K]',
            'Slabs [W/m²/K]',
            'Infiltration [m³/h/m²]'
        ]
        glazing_data_filter = [
            'SHGC',
            'Glazing [W/m²/K]'
        ]


    # TODO : remove interior walls from table?
    if team_id=='poly':
        # interior walls/infiltration cause issues with our models so seperate function
        construction_data_unfiltered, floor_area = extract_construction_summary_KV(html, model)
        construction_data = {k: v for k, v in construction_data_unfiltered.items() if k in construction_data_filter}
        glazing_data = {k: v for k, v in construction_data_unfiltered.items() if k in glazing_data_filter}
        print("building construction : done")
    else:
        # TODO : fix envelope function : tilt for floors = 180, tilt for roof=0 
        construction_data_unfiltered = extract_construction_summary(html, json_path)
        construction_data = {k: v for k, v in construction_data_unfiltered.items() if k in construction_data_filter}
        glazing_data = {k: v for k, v in construction_data_unfiltered.items() if k in glazing_data_filter}

    # --- Scalar KPIs ---
    total_energy = energy.get("Total Energy [kWh]", 0)
    elec_total = end_uses.get("Total End Uses", 0)
    gas_total = 0
    energy_intensity = energy.get("EUI Total Area [kWh/m2]", 0)

    
    # --- Version + weather location ---
    version          = "2026-05"
    weather_location = os.path.splitext(
        os.path.basename(r"MURBS_2026\outdoor_temperature_no_year.csv")
    )[0]

    # NEW : updated layout + add HW to breakdown
    # --- Monthly charts ---
    monthly_img    = os.path.join(output_path, "monthly.png")
    monthly_img_fr = os.path.join(output_path, "monthly_fr.png")
    create_monthly_plot_KV(sim_object, monthly_img, "eng")
    create_monthly_plot_KV(sim_object, monthly_img_fr, "fr")
    
    # NEW : add figure with typical day-stacked area graph of simulation 
    # --- Daily chart : simulation only ---
    # winter
    Daily_P_plot_path    = os.path.join(output_path, "daily_profiles1_winter.png")
    Daily_P_plot_path_fr = os.path.join(output_path, "daily_profiles1_winter_fr.png")
    plot_daily_profiles_sim_KV(sim_object, 'winter', Daily_P_plot_path,    "eng")
    plot_daily_profiles_sim_KV(sim_object, 'winter', Daily_P_plot_path_fr, "fr")
    # summer
    Daily_P_plot_path    = os.path.join(output_path, "daily_profiles1_summer.png")
    Daily_P_plot_path_fr = os.path.join(output_path, "daily_profiles1_summer_fr.png")
    plot_daily_profiles_sim_KV(sim_object, 'summer', Daily_P_plot_path,    "eng")
    plot_daily_profiles_sim_KV(sim_object, 'summer', Daily_P_plot_path_fr, "fr")
    
    
    # --- HVAC systems --- #
    # mapping csv path --currently it is in the SD_2026 folder undr name "hvac_mapping.csv"
    hvac_system_path = r"SFD_2026\hvac_mapping.csv"
    if team_id != "poly":
        hvac_system = get_hvac_system(building_type, building_subtype, hvac_system_path)
        hvac_system = dict(list(hvac_system.items())[1:])
        print("building hvac : done")
    else:
        hvac_system = get_hvac_system(building_type, building_subtype, hvac_system_path)
        hvac_system = dict(list(hvac_system.items())[1:])



    ############ PAGE 2 ###############

    # only add second page if Residential building
    if building_sector == "Residential":

        # NEW : change process energy to use a simulation object (relying on sql) to fetch electricity profile 
        # + added different temperature profiles for OPE 
        # --- Banana / PRISM curves ---
        df, df_hourly, comparison_table,comparison_table_en = process_energy_data_KV(
            f"{building_path}/{folder_name}",
            households_dict, ope_df, weather_df, 
            sim_object
        )


        # NEW : slightly changed to take unique temperature profile for OPE (provided in the df when new process_energy_data is used)
        Prism_plot_path    = os.path.join(output_path, "banana.png")
        Prism_plot_path_fr = os.path.join(output_path, "banana_fr.png")
        plot_banana_KV(df, Prism_plot_path, "eng")
        plot_banana_KV(df, Prism_plot_path_fr, "fr")


        # NEW : create summer/winter plots seperately
        # --- Daily profiles (combined, one image for now) ---
        # summer
        Daily_P_plot_path    = os.path.join(output_path, "daily_profiles_summer.png")
        Daily_P_plot_path_fr = os.path.join(output_path, "daily_profiles_summer_fr.png")
        plot_daily_profiles_ope_vs_meter_KV(df_hourly, "summer", Daily_P_plot_path,    "eng")
        plot_daily_profiles_ope_vs_meter_KV(df_hourly, "summer", Daily_P_plot_path_fr, "fr")
        # winter
        Daily_P_plot_path    = os.path.join(output_path, "daily_profiles_winter.png")
        Daily_P_plot_path_fr = os.path.join(output_path, "daily_profiles_winter_fr.png")
        plot_daily_profiles_ope_vs_meter_KV(df_hourly, "winter", Daily_P_plot_path,    "eng")
        plot_daily_profiles_ope_vs_meter_KV(df_hourly, "winter", Daily_P_plot_path_fr, "fr")

    else:
        # TODO : find proper fix, variables don't exist if second page content not generated
        # it won't be used in the template either, but throws error when dict is set up and variables not initiated
        comparison_table = []
        comparison_table_en = []
        pass



    # --- Logos ---


    # --- Shared render kwargs (EN) ---
    shared_en = dict(
        building_name=building_name,
        building_sector=building_sector,
        building_type=building_type,
        building_subtype=building_subtype,
        vintage=building_vintage,
        version=version,
        weather_location=weather_location,
        floor_area=floor_area,
        stories=stories,
        climate_zone=climate_zone,
        wwr=wwr,
        size_of_build=size_of_build,
        construction_data=construction_data,
        glazing_data=glazing_data,
        hvac_system=hvac_system,
        energy=energy,
        end_uses=end_uses,
        energy_intensity=energy_intensity,
        total_energy=total_energy,
        elec_total=elec_total,
        gas_total=gas_total,
        comparison_table=comparison_table_en,
        report_date=datetime.today().strftime("%Y-%m-%d"),
        data_description="The reference data used for the comparison come from a dataset of more than 60,000 residential electricity meters, combined with metadata. Filters were applied to ensure consistency with the building type and subtype of this card, as well as to exclude end uses such as pool, spa, and electric vehicle charging.",
        figure3_path="geometry.png",
        figure1_path="banana.png",
        monthly_chart="monthly.png",  
        daily_chart1_winter = "daily_profiles1_winter.png",
        daily_chart1_summer = "daily_profiles1_summer.png",   ## TODO : add second fig to daily 1 (seperate figs created for summer/winter under "daily_profiles1_winter(_fr)", "daily_profiles1_summer(_fr)")
        figure_summer_day="daily_profiles.png",   # using combined plot for now
        figure_winter_day="daily_profiles.png",   # using combined plot for now
        daily_chart2_winter = "daily_profiles_winter.png", 
        daily_chart2_summer = "daily_profiles_summer.png"
        
    )

    # TODO : translate new table entries
    # --- Shared render kwargs (FR) ---
    shared_fr = {**shared_en,
                "building_sector":get_french_characteristic(building_sector),
                "building_type":get_french_characteristic(building_type),
                "building_subtype":get_french_characteristic(building_subtype),
                "size_of_build":get_french_characteristic(size_of_build),
                "vintage":get_french_characteristic(building_vintage),
                "comparison_table":comparison_table,
                 # translated data
                 "construction_data": translate_dict(construction_data, TRANSLATIONS_FR),
                 "hvac_system":translate_dict_values(translate_dict(hvac_system, TRANSLATIONS_FR), TRANSLATIONS_FR),
                 "end_uses": translate_dict(end_uses, TRANSLATIONS_FR),
                 "wwr": translate_list_of_rows(wwr, TRANSLATIONS_FR),
                 "data_description": "Les données de référence utilisées pour la comparaison proviennent d’un jeu de données de plus de 60 000 compteurs électriques de clients résidentiels, couplé à des métadonnées. Des filtres ont été appliqués afin de respecter le type et le sous-type de bâtiment de cette fiche, ainsi que pour exclure les usages piscine, spa et recharge de véhicule électrique.", 
                 # FR-specific figure paths
                 "figure1_path": "banana_fr.png",
                 "monthly_chart": "monthly_fr.png",
                 "daily_chart1_winter" : "daily_profiles1_winter_fr.png",
                 "daily_chart1_summer" : "daily_profiles1_summer_fr.png",
                 "figure_summer_day": "daily_profiles_fr.png",
                 "figure_winter_day": "daily_profiles_fr.png",
                 "daily_chart2_winter": "daily_profiles_winter_fr.png",
                 "daily_chart2_summer": "daily_profiles_summer_fr.png"
                 }
  # --- Ensure output folders exist ---
    os.makedirs(operation_folder, exist_ok=True)
    os.makedirs(view_folder, exist_ok=True)

    # --- Render & write ---
    env = Environment(loader=FileSystemLoader(template_path))



    def render_and_write(template_name, kwargs, out_filename, folder_dest):
        content = env.get_template(template_name).render(**kwargs)

        html_path = os.path.join(output_path, out_filename)
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(content)

        with open(os.path.join(folder_dest, f"{folder_name}.html"), "w", encoding="utf-8") as f:
            f.write(content)

        # Convert to PDF using Playwright (headless Chromium)
        pdf_path = html_path.replace(".html", ".pdf")
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.goto(f"file:///{html_path.replace(os.sep, '/')}")
            page.pdf(
                path=pdf_path,
                format="A4",
                margin={"top": "0", "bottom": "0", "left": "0", "right": "0"},
                print_background=True,  # renders background colors
            )
            browser.close()

        pdf_folder_path = os.path.join(folder_dest, f"{folder_name}.pdf")
        shutil.copy(pdf_path, pdf_folder_path)

    # only add second page if Residential building
    if building_sector == "Residential":
        render_and_write("energy_card_en.html", shared_en, "Energy card.html", operation_folder)
        render_and_write("fiche_energie_fr.html", shared_fr, "Fiche energie.html", operation_folder)
    else: # use different template for 1 page only 
        render_and_write("energy_card_1page_en.html", shared_en, "Energy card.html", operation_folder)
        render_and_write("fiche_energie_1page_fr.html", shared_fr, "Fiche energie.html", operation_folder)
        
    return get_folder_structure(building_sector, building_type, building_subtype, size_of_build, building_name,building_shape)



def run_single_building():
    if team_id != "poly":

        return process_building(
        building_path=r"MURBS_2026/ID43_MR_SG_20112020",
        template_path=r"SFD_2026",
        idd_path=r"C:\EnergyPlusV25-2-0\Energy+.idd",
        operation_folder=r"Operation cards",
        view_folder=r"View cards"
                )

    else:
        return process_building(
        building_path=r"SFD_2026/Detached-1Floor-Post1980_1985-2012",
        template_path=r"SFD_2026",
        idd_path=r"C:\EnergyPlusV25-2-0\Energy+.idd",
        operation_folder=r"Operation cards",
        view_folder=r"View cards"
                )


if __name__ == "__main__":
    print(run_single_building())