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
from datetime import datetime
from playwright.sync_api import sync_playwright

#paths
weather_df = load_weather(r"MURBS_2026\outdoor_temperature_no_year.csv")
households_dict = load_households(r"MURBS_2026\dadesarquetips.csv")
ope_df = load_ope(r"MURBS_2026\dataOPE.csv")

# --- Translation dictionaries (EN → FR) ---
TRANSLATIONS_FR = {
    # WWR facades
    "North": "Nord",
    "South": "Sud",
    "East": "Est",
    "West": "Ouest",
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
    "Walls Ext [W/m2-K]": "Murs ext. [W/m²·K]",
    "Walls Int [W/m2-K]": "Murs int. [W/m²·K]",
    "Roof [W/m2-K]": "Toit [W/m²·K]",
    "Slabs [W/m2-K]": "Dalles [W/m²·K]",
    "Glazing [W/m2-K]": "Vitrage [W/m²·K]",
    "SHGC": "FCS",
    "Infiltration [m^3/h-m^2]": "Infiltration [m³/h·m²]",
}

def translate_dict(d, translations):
    """Return a new dict with keys translated, falling back to original key if not found."""
    return {translations.get(k, k): v for k, v in d.items()}

def translate_list_of_rows(rows, translations):
    """Translate first element of each [key, value] row."""
    return [[translations.get(row[0], row[0])] + row[1:] for row in rows]

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
    json_path = os.path.join(run_path, "measure_attributes.json")

    model = load_model(osm)

    if os.path.exists(idd_path):
        IDF.setiddname(idd_path)
    idf = IDF(idf_path)

    # --- Geometry ---
    geom_img = os.path.join(output_path, "geometry.png")
    view_geometry(idf, geom_img)

    # --- Building description ---
    floor_area, stories, space_count, climate_zone = building_description(model)

    # --- Energy extraction ---
    energy = extract_energy(html)
    end_uses = extract_end_uses(html)
    wwr = compute_wwr(html).values.tolist()
    construction_data = extract_construction_summary(html, json_path)

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

    # --- Monthly charts ---
    monthly_img    = os.path.join(output_path, "monthly.png")
    monthly_img_fr = os.path.join(output_path, "monthly_fr.png")
    create_monthly_plot(html, monthly_img, "eng")
    create_monthly_plot(html, monthly_img_fr, "fr")

    # --- Banana / PRISM curves ---
    df, df_hourly = process_energy_data(
        f"{building_path}/{folder_name}",
        households_dict, ope_df, weather_df
    )
    Prism_plot_path    = os.path.join(output_path, "banana.png")
    Prism_plot_path_fr = os.path.join(output_path, "banana_fr.png")
    plot_banana(df, Prism_plot_path, "eng")
    plot_banana(df, Prism_plot_path_fr, "fr")

    # --- Daily profiles (combined, one image for now) ---
    Daily_P_plot_path    = os.path.join(output_path, "daily_profiles.png")
    Daily_P_plot_path_fr = os.path.join(output_path, "daily_profiles_fr.png")
    plot_daily_profiles_ope_vs_meter(df_hourly, Daily_P_plot_path,    "eng")
    plot_daily_profiles_ope_vs_meter(df_hourly, Daily_P_plot_path_fr, "fr")

    # TODO: split into separate summer/winter images when the function supports it
    # summer_day_path    = os.path.join(output_path, "daily_summer.png")
    # summer_day_path_fr = os.path.join(output_path, "daily_summer_fr.png")
    # winter_day_path    = os.path.join(output_path, "daily_winter.png")
    # winter_day_path_fr = os.path.join(output_path, "daily_winter_fr.png")
    # plot_daily_profiles_ope_vs_meter(df_hourly, summer_day_path,    "eng", season="summer")
    # plot_daily_profiles_ope_vs_meter(df_hourly, summer_day_path_fr, "fr",  season="summer")
    # plot_daily_profiles_ope_vs_meter(df_hourly, winter_day_path,    "eng", season="winter")
    # plot_daily_profiles_ope_vs_meter(df_hourly, winter_day_path_fr, "fr",  season="winter")

    # TODO: extract glazing properties when function is implemented
    # glazing_data = extract_glazing_data(html, json_path)
    glazing_data = {}

    # TODO: extract mechanical systems when function is implemented
    # mechanical_systems = extract_mechanical_systems(html, json_path)
    mechanical_systems = {}

    # TODO: build comparison table when reference data is available
    # comparison_table = build_comparison_table(energy, energy_intensity, construction_data)
    comparison_table = []

    # --- Logos ---


    # --- Shared render kwargs (EN) ---
    shared_en = dict(
        model_description="Your building description text here.Your building description text here.Your building description text here.Your building description text here.Your building description text here.Your building description text here.Your building description text here.Your building description text here.Your building description text here.Your building description text here.Your building description text here.Your building description text here.Your building description text here.Your building description text here.Your building description text here.Your building description text here.Your building description text here.Your building description text here.Your building description text here.Your building description text here.Your building description text here.Your building description text here.Your building description text here.Your building description text here.",
        building_name=building_name,
        vintage=building_vintage,
        version=version,
        weather_location=weather_location,
        floor_area=floor_area,
        stories=stories,
        climate_zone=climate_zone,
        wwr=wwr,
        construction_data=construction_data,
        glazing_data=glazing_data,
        mechanical_systems=mechanical_systems,
        energy=energy,
        end_uses=end_uses,
        energy_intensity=energy_intensity,
        total_energy=total_energy,
        elec_total=elec_total,
        gas_total=gas_total,
        comparison_table=comparison_table,
        report_date=datetime.today().strftime("%Y-%m-%d"),
        figure3_path="geometry.png",
        figure1_path="banana.png",
        monthly_chart="monthly.png",
        figure_summer_day="daily_profiles.png",   # using combined plot for now
        figure_winter_day="daily_profiles.png",   # using combined plot for now
    )

    # --- Shared render kwargs (FR) ---
    shared_fr = {**shared_en,
                 # translated data
                 "construction_data": translate_dict(construction_data, TRANSLATIONS_FR),
                 "end_uses": translate_dict(end_uses, TRANSLATIONS_FR),
                 "wwr": translate_list_of_rows(wwr, TRANSLATIONS_FR),
                 # FR-specific figure paths
                 "figure1_path": "banana_fr.png",
                 "monthly_chart": "monthly_fr.png",
                 "figure_summer_day": "daily_profiles_fr.png",
                 "figure_winter_day": "daily_profiles_fr.png",
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
    render_and_write("energy_card_en.html", shared_en, "Energy card.html", operation_folder)
    render_and_write("fiche_energie_fr.html", shared_fr, "Fiche energie.html", operation_folder)
    return os.path.join(output_path, "Fiche energie.html")

