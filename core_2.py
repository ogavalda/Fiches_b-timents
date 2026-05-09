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
    df = df[["time_key", "T_drybulb_C"]]

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

