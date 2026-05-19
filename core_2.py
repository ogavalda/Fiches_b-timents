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
import pandas as pd
import matplotlib.pyplot as plt

def normalize_time(series, shift_hours=0):
    dt = pd.to_datetime(series)

    if shift_hours != 0:
        dt = dt + pd.Timedelta(hours=shift_hours)

    return dt.dt.strftime("%m-%d %H:%M")

def load_weather(weather_csv):
    df = pd.read_csv(weather_csv)

    df["time_key"] = normalize_time(df["timestamp"])
    #df = df[["time_key", "T_drybulb_C"]]  # removed this line because we need access to multiple columns, not just the one

    return df

def load_households(source_a_csv):
    df = pd.read_csv(source_a_csv)

    # Clean names just in case
    df["Name"] = df["Name"].str.strip()

    households_dict = dict(zip(df["Name"], df["Number of apartments"]))

    return households_dict

def load_ope(source_b_csv):
    df = pd.read_csv(source_b_csv)

    df["time_key"] = normalize_time(df["timestamp"])

    # Keep only time + vintage columns
    df = df.drop(columns=["timestamp"])

    return df


def get_vintage_column(vintage):
    v = vintage.lower()

    if "1945" in v:
        return "A_Pre1945"

    elif any(x in v for x in ["1946", "1950", "1960", "1970", "1980"]) and "2010" not in v:
        return "B_19461983"

    elif any(x in v for x in ["1984", "1980", "1990", "2000", "2010"]) and "2011" not in v:
        return "C_19842010"

    elif any(x in v for x in ["2011", "2012", "2015", "2020"]):
        return "D_Post2011"

    else:
        raise ValueError(f"Unknown vintage format: {vintage}")


# new function to get archetype key for different model names
def get_vintage_column_KV(folder_name):

    archetypekeys_modelnames = dict()
    archetypekeys_modelnames["Detached-1Floor-Pre1980_1946-1970"] = "detached, '[1946 , 1983]', 1"
    archetypekeys_modelnames["Detached-1Floor-Pre1980_1971-1985"] = "detached, '[1946 , 1983]', 1"
    archetypekeys_modelnames["Detached-1Floor-Post1980_1985-2012"] = "detached, '[1984 , 2011]', 1"
    archetypekeys_modelnames["Detached-1Floor-Pre1980_Pre1945"] = "detached, '<1946', 1"
    archetypekeys_modelnames["Detached-1Floor-Post1980_new-construction"] = "detached, '>2011', 1"
    archetypekeys_modelnames["Detached-2Floor-Pre1980_1945-1970"] = "detached, '[1946 , 1983]', 2"
    archetypekeys_modelnames["Detached-2Floor-Pre1980_1971-1985"] = "detached, '[1946 , 1983]', 2"
    archetypekeys_modelnames["Detached-2Floor-Post1980_1985-2012"] = "detached, '[1984 , 2011]', 2"
    archetypekeys_modelnames["Detached-2Floor-Pre1980_Pre1945"] = "detached, '<1946', 2"
    archetypekeys_modelnames["Detached-2Floor-Post1980_new-construction"] = "detached, '>2011', 2"
    archetypekeys_modelnames["SD-1Floor_1946-1970"] = "semi-detached, '[1946 , 1983]', 1"
    archetypekeys_modelnames["SD-1Floor_1971-1985"] = "semi-detached, '[1946 , 1983]', 1"
    archetypekeys_modelnames["SD-1Floor_1986-2012"] = "semi-detached, '[1984 , 2011]', 1"
    archetypekeys_modelnames["SD-1Floor_Pre1945"] = "semi-detached, '<1946', 1"
    archetypekeys_modelnames["SD-1Floor_new-construction"] = "semi-detached, '>2011', 1"
    archetypekeys_modelnames["SD-2Floor_1946-1970"] = "semi-detached, '[1946 , 1983]', 2"
    archetypekeys_modelnames["SD-2Floor_1971-1985"] = "semi-detached, '[1946 , 1983]', 2"
    archetypekeys_modelnames["SD-2Floor_1986-2012"] = "semi-detached, '[1984 , 2011]', 2"
    archetypekeys_modelnames["SD-2Floor_Pre1945"] = "semi-detached, '<1946', 2"
    archetypekeys_modelnames["SD-2Floor_new-construction"] = "semi-detached, '>2011', 2"
    archetypekeys_modelnames["Row-2Floor-end_1946-1970"] = "semi-detached, '[1946 , 1983]', 2"
    archetypekeys_modelnames["Row-2Floor-end_1971-1985"] = "semi-detached, '[1946 , 1983]', 2"
    archetypekeys_modelnames["Row-2Floor-end_1986-2012"] = "semi-detached, '[1984 , 2011]', 2"
    archetypekeys_modelnames["Row-2Floor-end_Pre1945"] = "semi-detached, '<1946', 2"
    archetypekeys_modelnames["Row-2Floor-end_new-construction"] = "semi-detached, '>2011', 2"
    archetypekeys_modelnames["Row-2Floor-middle_1946-1970"] = "row, '[1946 , 1983]', 2"
    archetypekeys_modelnames["Row-2Floor-middle_1971-1985"] = "row, '[1946 , 1983]', 2"
    archetypekeys_modelnames["Row-2Floor-middle_1985-2012"] = "row, '[1984 , 2011]', 2"
    archetypekeys_modelnames["Row-2Floor-middle_Pre1945"] = "row, '<1946', 2"
    archetypekeys_modelnames["Row-2Floor-middle_new-construction"] = "row, '>2011', 2"

    if folder_name in archetypekeys_modelnames.keys():
        return archetypekeys_modelnames[folder_name]
    else:
        raise Exception("archetype not found in vintages")
       

def find_meter_csv(building_path):
    for root, dirs, files in os.walk(building_path):

        # Check if current folder is the Export folder
        if "Export" in os.path.basename(root):

            csv_files = [f for f in files if f.lower().endswith(".csv")]

            if len(csv_files) == 0:
                raise FileNotFoundError(f"No CSV found in {root}")

            if len(csv_files) > 1:
                raise ValueError(f"Multiple CSV files found in {root}: {csv_files}")

            return os.path.join(root, csv_files[0])

    raise FileNotFoundError("Export folder with CSV not found")


def aggregate_daily(df):
    # Convert back to datetime (we need it for grouping)
    dt = pd.to_datetime(df["time_key"], format="%m-%d %H:%M")

    df["date"] = dt.dt.strftime("%m-%d")

    daily_df = df.groupby("date").agg({
        "OPE": "sum",
        "meter": "sum",
        "temperature": "mean"
    }).reset_index()

    return daily_df


#-----------------------------------------------------------------------
def process_energy_data(
    building_path,
    households_dict,
    ope_df,
    weather_df
):
    folder_name = os.path.basename(building_path)
    run_path = os.path.join(building_path,"run")
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
    meter_csv = find_meter_csv(run_path)
    meter_df = pd.read_csv(meter_csv)

    meter_df["time_key"] = normalize_time(meter_df["Hourly"], shift_hours=-1)

    # Convert J → kWh
    meter_df["meter_kwh"] = meter_df["Electricity:Facility[J]"] / 3.6e6

    # Normalize per household
    meter_df["meter_kwh"] /= households

    meter_df = meter_df[["time_key", "meter_kwh"]]

    # --- Merge all ---
    df = meter_df.merge(ope_df[["time_key", vintage_col]], on="time_key")
    df = df.merge(weather_df, on="time_key")

    df = df.rename(columns={
        vintage_col: "OPE",
        "T_drybulb_C": "temperature",
        "meter_kwh": "meter"
    })

    return aggregate_daily(df),df

def plot_banana(df, output_path,lang):
    plt.figure(figsize=(8, 6))

    plt.scatter(df["temperature"], df["OPE"],
                color="blue", alpha=0.5, label="OPE")

    plt.scatter(df["temperature"], df["meter"],
                color="red", alpha=0.5, label="Meter")

    if lang=="eng":
        plt.xlabel("Outdoor Temperature (°C)")
        plt.ylabel("Consumption (kWh)")
        plt.title("PRISM Curve")
    else:
        plt.xlabel("Température Extérieure (°C)")
        plt.ylabel("Consommation (kWh)")
        plt.title("Curve PRISM")
    plt.legend()

    plt.grid(True)

    plt.savefig(output_path)
    plt.close()

