import json
import os
import openstudio
from collections import Counter
from bs4 import BeautifulSoup
import pandas as pd
import re
import matplotlib.pyplot as plt
import numpy as np
from config import team_id

from core_2 import get_vintage_column_KV, get_vintage_column, normalize_time
from Kpi import *
# --------------------------------
# MONTHLY CONSUMPTION PLOT
# --------------------------------

### alternative to current version : use sql results only 
# function relies on a class ReadSimulation which makes querying the sql easier
# requires having the correct meters & variables specified as outputs during simulation (should be OK when running the provided workflow) 
def create_monthly_plot(sim_results, output_path, lang):
    if team_id=='poly':
        df_monthly = sim_results.get_monthly_consumption()
    else:
        # TODO : connect to function that gets HW variable names from the mapping_df
        #mapping_df = get_mappingdf()
        #HW_key_osm = get_varaibles_from_mapping()

        df_monthly = sim_results.get_monthly_consumption()

    df_monthly = df_monthly.sort_values(by=['Month'])


    # reorder columns for plot
    df_monthly = df_monthly[['PlugLoads', 'Other (Fans,...)', 'Lighting', 'DHW', 'Heating', 'Cooling']]
    fig, ax = plt.subplots(1,1, figsize=(9, 5))

    colors = {'Cooling':"#58b3e7", 'DHW':'darkred', 'Heating':"#e95454ff", 'PlugLoads':'gray', 'Lighting':'gold', 'Other (Fans,...)':'lightgrey'}
    df_monthly.plot.bar(stacked=True, color=colors, ax=ax)

    ax.set_xlabel('')

    if lang=="eng":
        ax.set_ylabel("Energy [kWh]")
        #ax.set_title("Monthly Energy Consumption by Type")
        legend_english = {'PlugLoads':'Plug Loads', "DHW":"Domestic/Service Hot Water"}
        h, l = ax.get_legend_handles_labels()
        ax.legend(handles = h[::-1], labels = [legend_english[l_] if l_ in legend_english.keys() else l_ for l_ in l][::-1] )
        ax.set_xticklabels(['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'])
    else:
        ax.set_ylabel("Consommation Mensuel [kWh]")
        #ax.set_title("Consommation mensuelle par usage")
        legend_french = {'PlugLoads':'Charges aux prises', 'Lighting':'Éclairage', 'Other (Fans,...)':'Autres (ventilateurs,...)', 'Heating':"Chauffage", 'Cooling':"Climatisation", "DHW":"Eau Chaude"}
        h, l = ax.get_legend_handles_labels()
        ax.legend(handles = h[::-1], labels = [legend_french[l_] for l_ in l ][::-1])
        ax.set_xticklabels(['Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin', 'Juil', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre'])

    plt.xticks(rotation=45)
    plt.tight_layout()

    figure_path = output_path
    plt.savefig(figure_path)
    return figure_path


# --------------------------------
# DAILY PROFILE PLOT - TYPE 1 : SIMULATION STACKED AREA
# --------------------------------    

def plot_loadprofile_stacked(Simulation, period, output_path, lang='eng'):
    # day is number to represent day of week, picked random weekday here
    df_profile = get_load_profile_typical(period, 2, Simulation=Simulation)

    if period == 'winter':
        # define order of columns
        column_order = ['PlugLoads', 'Other (Fans,...)', 'Lighting', 'DHW', 'Heating']
    else :  
        # define order of columns
        column_order = ['PlugLoads', 'Other (Fans,...)', 'Lighting', 'DHW', 'Heating', 'Cooling']


    ### define associated colors
    # previously used colors 
    #colors = {'PlugLoads':'darkgray', 'Lighting':'gold', 'Other (Fans,...)':'lightgrey', 'Heating':"#e95454ff", 'Cooling':"#58b3e7"}
    
    # colors that match daily profile plot
    colors = {'Cooling':"#58b3e7", 'DHW':'darkred', 'Heating':"#e95454ff", 'PlugLoads':'gray', 'Lighting':'gold', 'Other (Fans,...)':'lightgrey'}
    
    # start figure
    fig, ax = plt.subplots(1,1,figsize=(10,5))

    df_profile[column_order].plot.area(ax=ax, color=colors, 
                                       linewidth = 0)

    ax.set_xlim([0, 24*3600-15*60])

    if lang=="eng":
        ax.set_ylabel("Electric consumption [kWh]")
        ax.set_xlabel('Time of Day')

        legend_english = {'PlugLoads':'Plug Loads', "DHW":"Domestic/Service Hot Water"}
        h, l = ax.get_legend_handles_labels()
        ax.legend(handles = h[::-1], labels = [legend_english[l_] if l_ in legend_english.keys() else l_ for l_ in l][::-1] )
    else:
        ax.set_ylabel('Consommation électrique (khW)')
        ax.set_xlabel('Heure de la journée')

        day_type_french = {'winter':'hiver', 'summer':'été'}
        legend_french = {'PlugLoads':'Charges aux prises', 'Lighting':'Éclairage', 'Other (Fans,...)':'Autres (ventilateurs,...)', 'Heating':"Chauffage", 'Cooling':"Climatisation", "DHW":"Eau Chaude"}
        h, l = ax.get_legend_handles_labels()
        ax.legend(handles = h[::-1], labels = [legend_french[l_] for l_ in l ][::-1])

    xticks = np.arange(0,24,2)   # xticks by hours for starters to use in labels
    xtick_labels = [str(time)+':00' for time in xticks]
    xticks = [x*60*60 for x in xticks] # multiply by 3600 to correspond to scale of x-axis
    
    # set monthly locator
    ax.set_xticks(xticks)
    ax.set_xticklabels(xtick_labels)

    plt.tight_layout()

    figure_path = output_path
    plt.savefig(figure_path)

    return #figure_path

### function to get typical load profile (weekday vs weekend day)
# works on both simulation results or OPE metered data
def get_load_profile_typical(period, day, Simulation=None, OPE_profile = None):
    if team_id != 'poly':
        # TODO : # TODO : connect to function that gets HW variable names from the mapping_df
        #mapping_df = get_mappingdf()
        #HW_key_osm = get_varaibles_from_mapping()
        HW_key_osm = ""
        df_lp = Simulation.get_loadprofile().resample('1h').mean()
    else:
        df_lp = Simulation.get_loadprofile().resample('1h').mean()


    # TODO : coordinate what's winter/mid/summer between the different functions
    if period == "winter":
        months = [11,12,1,2]
    elif period == "summer":
        months = [5,6,7,8]
    elif period == "mid":
        months = [3,4,9,10]
    else:
        raise Exception("Given period not recognized, must be 'winter', 'summer', or 'mid'.")

    # TODO : update to aggregate weekdays or weekends
    if day in range(0,7): # 0 is sunday, 6 is saturday
        # aggregate days using number
        pass
    else:
        raise Exception("Day number not recognized, must be value between 0 and 6")
    
    df_lp_selection = df_lp.loc[(df_lp.index.month.isin(months))&(df_lp.index.dayofweek==day)].copy()

    df_profile = df_lp_selection.groupby(df_lp_selection.index.time).mean()
    df_profile.columns.name = None
    return df_profile/1000 #kwh


# --------------------------------
# DAILY PROFILE PLOT - TYPE 2 : SIMULATION VS. OPE
# --------------------------------


def prepare_profile_data(df):
    dt = pd.to_datetime(df["time_key"], format="%m-%d %H:%M")

    df["date"] = dt.dt.strftime("%m-%d")
    df["hour"] = dt.dt.hour
    df["month"] = dt.dt.month

    # weekday / weekend
    df["day_type"] = dt.dt.weekday.apply(
        lambda x: "weekday" if x < 5 else "weekend"
    )

    return df


def get_season(month):
    if month in [12,1,2,3]:
        return 'winter'
    elif month in [6,7,8]:
        return 'summer'
    else:
        return 'mild'

def plot_daily_profiles_ope_vs_meter(df, season, output_path,lang):

    df = prepare_profile_data(df)

    df["season"] = df["month"].apply(get_season)

    # --- Pivot ---
    daily_profiles = df.pivot_table(
        values=["OPE", "meter"],
        index="date",
        columns="hour",
        aggfunc="mean"
    )

    # Flatten columns
    daily_profiles.columns = [
        f"{var}_{hour}" for var, hour in daily_profiles.columns
    ]

    # Meta info
    meta = df.groupby("date")[["season", "day_type"]].first()
    daily_profiles = daily_profiles.join(meta)

    # --- Plot ---
    fig, axes = plt.subplots(1, 2, figsize=(14,5), sharex=True, sharey=True)

    types = ['weekday','weekend']

    # changed plot to only have one row : i=0
    i=0
    for j, day_type in enumerate(types):

        ax = axes[j]

        subset = daily_profiles[
            (daily_profiles['season'] == season) &
            (daily_profiles['day_type'] == day_type)
        ]

        if len(subset) == 0:
            continue

        # --- Meter: plot ALL (noisy, transparent red) ---
        for _, row in subset.iterrows():

            meter_profile = [row[f"meter_{h}"] for h in range(24)]
            ax.plot(range(24), meter_profile,
                    color="red", alpha=0.15)

        # --- Meter average (dashed red) ---
        meter_mean = [
            subset[f"meter_{h}"].mean() for h in range(24)
        ]

        ax.plot(range(24), meter_mean,
                color="red", linestyle="--", linewidth=2,
                label="Meter Avg" if (i == 0 and j == 0) else "")

        # --- OPE: ONLY average (bold blue) ---
        ope_mean = [
            subset[f"OPE_{h}"].mean() for h in range(24)
        ]

        ax.plot(range(24), ope_mean,
                color="blue", linewidth=3,
                label="OPE Avg" if (i == 0 and j == 0) else "")

        # remove title, html already has title
        #ax.set_title(f"{season} - {day_type}")
        if lang=="eng":
            ax.set_xlabel("Hour of Day")
            ax.set_ylabel("Consumption (kWh)")
        else:
            ax.set_xlabel("Heure du jour")
            ax.set_ylabel("Consommation (kWh)")
        ax.set_xlim(0, 23)
        ax.grid(True)

    plt.tight_layout()
    #plt.legend()
    plt.savefig(output_path)
    plt.close()


# --------------------------------
# BANANA CURVE
# --------------------------------

def process_energy_data(
    building_path,
    households_dict,
    ope_df,
    weather_df, 
    sim_object
):
    folder_name = os.path.basename(building_path)
    run_path = os.path.join(building_path,"run")

    ## replace with poly/conc input variable
    if team_id=='poly' : 
        households = 1 
        vintage_col = get_vintage_column_KV(folder_name)
        building_name = folder_name
    else:
        parts = folder_name.split("_")

        building_id = parts[0]
        building_type = parts[1]
        building_name = parts[2]
        building_vintage = parts[3]


        for temp_name in households_dict:
            if building_name in temp_name:
                households = households_dict[temp_name]

        
        vintage_col = get_vintage_column(building_vintage)



    # --- Load meter data ---
    # !!!! alternative using sql (which also allows getting simulation specific temperature) using the "simulation object"
    # ideally the simulation object would be loaded in the "per_folder" function and passed on to this function as an argument
    # but for testing sake i've put it here for now

    if team_id != 'poly':
        weather_column_name = 'T_drybulb_C'
    else:
        weather_column_name = vintage_col
    

    # get simulation related data
    df_sim_hourly = sim_object.get_electricityprofile_kwh()

    # Add time key
    df_sim_hourly["time_key"] = df_sim_hourly.index.strftime("%m-%d %H:%M")

    # add simulation weather
    # !!! added extra column with simulation temperature because OPE has unique temperature for SFD     
    if team_id == 'poly': 
        df_weather_sim = sim_object.get_outdoor_temperature().resample('1h').mean().iloc[:-1]
        df_sim_hourly = pd.merge(df_weather_sim, df_sim_hourly, left_index=True, right_index=True)
        df_sim_hourly.rename(columns={'Value_x':'temperature_sim', 'Value_y':'meter'}, inplace=True)
    else:
        df_sim_hourly = df_sim_hourly.merge(weather_df.rename(columns={weather_column_name:'temperature_sim'})[["time_key", "temperature_sim"]], on="time_key")
        df_sim_hourly.rename(columns={'Value':'meter'}, inplace=True)
    


    # TODO : check whether we should add normalize time for simulation data! 
    # commented out for now because it raises an error
    df_sim_hourly["time_key"] = normalize_time(df_sim_hourly["time_key"], shift_hours=-1)

    # Normalize per household
    df_sim_hourly["meter"] /= households

    # --- Merge all ---
    df = df_sim_hourly.merge(ope_df.rename(columns={vintage_col:'OPE'})[["time_key", "OPE"]], on="time_key")
    df = df.merge(weather_df.rename(columns={weather_column_name:'temperature_OPE'})[["time_key", "temperature_OPE"]], on="time_key")

    # since every field needed for kpi calculation is ready, kpi function is embedded here

    comparison_table,comparison_table_en =  calculate_kpi_from_df(df, building_name, vintage_col)
    return aggregate_daily(df),df,comparison_table,comparison_table_en

def aggregate_daily(df):
    # Convert back to datetime (we need it for grouping)
    dt = pd.to_datetime(df["time_key"], format="%m-%d %H:%M")

    df["date"] = dt.dt.strftime("%m-%d")

    daily_df = df.groupby("date").agg({
        "OPE": "sum",
        "meter": "sum",
        "temperature_OPE": "mean",
        "temperature_sim": "mean"
    }).reset_index()

    return daily_df

def plot_banana(df, output_path,lang):
    plt.figure(figsize=(8, 6))

    plt.scatter(df["temperature_OPE"], df["OPE"],
                color="blue", alpha=0.5, label="Data")

    plt.scatter(df["temperature_sim"], df["meter"],
                color="red", alpha=0.5, label="Meter")

    if lang=="eng":
        plt.xlabel("Outdoor Temperature (°C)")
        plt.ylabel("Consumption (kWh)")
        #plt.title("PRISM Curve")
    else:
        plt.xlabel("Température Extérieure (°C)")
        plt.ylabel("Consommation (kWh)")
        #plt.title("Curve PRISM")
    plt.legend()

    plt.grid(True)

    plt.savefig(output_path)
    plt.close()


## Function to calculate the KPI's
## it takes df as an argument --> the one returned by the function process_energy_data(),
## because it already processes the required fields.

def calculate_kpi_from_df(
        df,
        building_name,
        vintage_col
):
    # COPY DATAFRAMES
    kpi_df = df.copy()
    ope_df = df.copy()

    # PREPARE BUILDING DATAFRAME

    kpi_df.rename(columns={
            'time_key': 'dateinterval',
            'meter': 'energieactivelivree_kwh',
            'temperature_sim': 'temperatureatmospherique'
        },
        inplace=True)

    # PREPARE OPE DATAFRAME
    ope_df.rename(columns={
            'time_key': 'dateinterval',
            'OPE': 'energieactivelivree_kwh',
            'temperature_OPE': 'temperatureatmospherique'
        },
        inplace=True)

    # KEEP ONLY REQUIRED COLUMNS
    kpi_df = kpi_df[[
            'dateinterval',
            'energieactivelivree_kwh',
            'temperatureatmospherique'
        ]]

    ope_df = ope_df[[
            'dateinterval',
            'energieactivelivree_kwh',
            'temperatureatmospherique'
        ]]

    # RUN KPI ANALYSIS - BUILDING
    building_kpi = AnalyseProfil()

    building_kpi.RunAnalyse(Identifiant=building_name,file=kpi_df)

    # RUN KPI ANALYSIS - OPE
    ope_kpi = AnalyseProfil()

    ope_kpi.RunAnalyse(Identifiant=vintage_col,file=ope_df)

    # to filter the kpi's, a list of needed kpi's
    wanted_kpis = [
        "Conso_annuelle_electricite_kWh",
        "Conso_base_electricite_kWhParJour",
        "Pente_chauffage_electricite_WparK",
        "Pente_climatisation_electricite_WparK",
        "Pointe_hiver_am_kW",
        "Pointe_h_hiver_am",
        "Pointe_hiver_pm_kW",
        "Pointe_h_hiver_pm",
    ]

    # create the dictionary for the values
    building_dict = (building_kpi.dict_caracteristiques)
    building_dict = {k: v        for k, v in building_dict.items()        if k in wanted_kpis    }

    ope_dict = (ope_kpi.dict_caracteristiques)
    ope_dict = {k: v        for k, v in ope_dict.items()        if k in wanted_kpis    }

    # Remove IDENTIFIANT because as a first row, it gives an error in reading
    building_dict.pop("Identifiant",None)
    ope_dict.pop("Identifiant",None)

    # CREATE KPI TABLE
    kpi_table = pd.DataFrame({building_name: building_dict,     vintage_col: ope_dict})

    # create comparison table
    comparison_table = kpi_table.copy() # copies cause it will delete some columns
    comparison_table.columns = ["model","reference"] # keep only these columns
    comparison_table = (comparison_table.reset_index())
    comparison_table = (comparison_table.rename(columns={"index": "indicator"})) # because the column name will show the name of parameter

    # Delta --> calculates the difference between model and reference (error)
    comparison_table["delta"] = (comparison_table["model"]- comparison_table["reference"])

    # ROUNDING
    comparison_table["model"] = (comparison_table["model"].round(2))
    comparison_table["reference"] = (comparison_table["reference"].round(2))
    comparison_table["delta"] = (comparison_table["delta"].round(1))
    comparison_table_en=comparison_table.copy()
    rename_map = {
        "Conso_annuelle_electricite_kWh": "Consommation annuelle électricité (kWh)",
        "Conso_base_electricite_kWhParJour": "Consommation de base électricité (kWh/jour)",
        "Pente_chauffage_electricite_WparK": "Pente chauffage électricité (W/K)",
        "Pente_climatisation_electricite_WparK": "Pente climatisation électricité (W/K)",
        "Pointe_hiver_am_kW": "Pointe hiver AM (kW)",
        "Pointe_h_hiver_am": "Heure pointe hiver AM",
        "Pointe_hiver_pm_kW": "Pointe hiver PM (kW)",
        "Pointe_h_hiver_pm": "Heure pointe hiver PM",
    }
    rename_map_en = {
        "Conso_annuelle_electricite_kWh": "Yearly electricity consumption (kWh)",
        "Conso_base_electricite_kWhParJour": "Yearly baseload consumption (kWh/jour)",
        "Pente_chauffage_electricite_WparK": "Slope electricity heating (W/K)",
        "Pente_climatisation_electricite_WparK": "Slope climatisation cooling (W/K)",
        "Pointe_hiver_am_kW": "Peak winter AM (kW)",
        "Pointe_h_hiver_am": "Hour peak winter AM",
        "Pointe_hiver_pm_kW": "Peak winter PM (kW)",
        "Pointe_h_hiver_pm": "Hour peak winter PM",
    }
    comparison_table["indicator"] = comparison_table["indicator"].replace(rename_map)
    comparison_table_en["indicator"] = comparison_table_en["indicator"].replace(rename_map_en)
    # convert to dictionary --> it prepares the return for a ready to pass to html output
    comparison_table = (comparison_table.to_dict(orient="records"))
    comparison_table_en = (comparison_table_en.to_dict(orient="records"))
    # RETURN
    return comparison_table,comparison_table_en



