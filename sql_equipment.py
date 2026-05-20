import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
import re

# ============================================================
# INPUTS
# ============================================================

sql_path = r"MURBS_2026\ID39_MR_ND_1945\ID39_MR_ND_1945\run\eplusout.sql"

mapping_csv = r"D:\git\electric_equipment_mapping.csv"

variable_name = "Electric Equipment Electricity Energy"

# ============================================================
# LOAD EQUIPMENT MAPPING
# ============================================================

mapping_df = pd.read_csv(mapping_csv)

equipment_map = {}

for _, row in mapping_df.iterrows():

    instance_name = str(row["Equipment_Instance"])
    definition = str(row["Definition"])

    match = re.search(
        r'Electric Equipment (\d+)',
        instance_name
    )

    if match:

        equipment_id = match.group(1)

        equipment_map[equipment_id] = definition

# ============================================================
# PRINT MAPPING
# ============================================================

print("\nEQUIPMENT ID MAPPING:\n")

for k, v in equipment_map.items():
    print(k, " --> ", v)

# ============================================================
# CONNECT TO SQL
# ============================================================

conn = sqlite3.connect(sql_path)

# ============================================================
# LOAD APPLIANCE DATA
# ============================================================

query = f"""
SELECT
    rdd.KeyValue,
    rd.TimeIndex,
    rd.Value

FROM ReportData rd

JOIN ReportDataDictionary rdd
ON rd.ReportDataDictionaryIndex =
   rdd.ReportDataDictionaryIndex

WHERE rdd.Name = '{variable_name}'
"""

df_raw = pd.read_sql_query(query, conn)

# ============================================================
# BUILD APPLIANCE DATAFRAME
# ============================================================

equipment_data = {}

for key, group in df_raw.groupby("KeyValue"):

    try:

        # ----------------------------------------------------
        # EXTRACT EQUIPMENT ID
        # ----------------------------------------------------

        match = re.search(
            r'EQUIPMENT (\d+)',
            key.upper()
        )

        if not match:
            continue

        equipment_id = match.group(1)

        # ----------------------------------------------------
        # GET APPLIANCE TYPE
        # ----------------------------------------------------

        if equipment_id not in equipment_map:
            continue

        definition_name = equipment_map[equipment_id]

        # ----------------------------------------------------
        # SORT TIME
        # ----------------------------------------------------

        group = group.sort_values("TimeIndex")

        # ----------------------------------------------------
        # JOULES → KWH
        # ----------------------------------------------------

        values_kwh = (
            group["Value"] / 3.6e6
        ).tolist()

        # ----------------------------------------------------
        # AGGREGATE BY APPLIANCE TYPE
        # ----------------------------------------------------

        if definition_name not in equipment_data:

            equipment_data[definition_name] = values_kwh

        else:

            equipment_data[definition_name] = [

                a + b

                for a, b in zip(
                    equipment_data[definition_name],
                    values_kwh
                )
            ]

        print(f"Loaded: {key} --> {definition_name}")

    except Exception as e:

        print(f"FAILED: {key}")
        print(e)

# ============================================================
# CREATE INITIAL DATAFRAME
# ============================================================

df = pd.DataFrame(equipment_data)

# ============================================================
# LOAD SYSTEM METERS
# ============================================================

meter_names = {

    "InteriorLights": "InteriorLights:Electricity",
    "Heating": "Heating:Electricity",
    "Cooling": "Cooling:Electricity",
    "Fans": "Fans:Electricity",
    "Pumps": "Pumps:Electricity"

}

for label, meter_name in meter_names.items():

    try:

        query = f"""
        SELECT
            rd.TimeIndex,
            rd.VariableValue

        FROM ReportMeterData rd

        JOIN ReportMeterDataDictionary rmd
        ON rd.ReportMeterDataDictionaryIndex =
           rmd.ReportMeterDataDictionaryIndex

        WHERE rmd.VariableName = '{meter_name}'
        """

        meter_df = pd.read_sql_query(query, conn)

        if meter_df.empty:

            print(f"Meter not found: {meter_name}")
            continue

        meter_df = meter_df.sort_values("TimeIndex")

        values_kwh = (
            meter_df["VariableValue"] / 3.6e6
        ).tolist()

        df[label] = values_kwh

        print(f"Loaded meter: {meter_name}")

    except Exception as e:

        print(f"FAILED meter: {meter_name}")
        print(e)

# ============================================================
# CLOSE SQL CONNECTION
# ============================================================

conn.close()

# ============================================================
# RENAME DHW
# ============================================================

df.rename(
    columns={"Chauffeau": "DHW"},
    inplace=True
)

# ============================================================
# CREATE HIGH-LEVEL CATEGORIES
# ============================================================

df_final = pd.DataFrame(index=df.index)

# ------------------------------------------------------------
# DHW
# ------------------------------------------------------------

if "DHW" in df.columns:

    df_final["DHW"] = df["DHW"]

# ------------------------------------------------------------
# PLUG LOADS
# ------------------------------------------------------------

excluded_columns = [

    "DHW",
    "InteriorLights",
    "Heating",
    "Cooling",
    "Fans",
    "Pumps"

]

plug_columns = [

    c for c in df.columns
    if c not in excluded_columns

]

df_final["Charges aux prises"] = df[plug_columns].sum(axis=1)

# ------------------------------------------------------------
# LIGHTING
# ------------------------------------------------------------

if "InteriorLights" in df.columns:

    df_final["Éclairage"] = df["InteriorLights"]

# ------------------------------------------------------------
# HEATING
# ------------------------------------------------------------

if "Heating" in df.columns:

    df_final["Chauffage"] = df["Heating"]

# ------------------------------------------------------------
# COOLING
# ------------------------------------------------------------

if "Cooling" in df.columns:

    df_final["Climatisation"] = df["Cooling"]

# ------------------------------------------------------------
# OTHER
# ------------------------------------------------------------

other_columns = []

if "Fans" in df.columns:
    other_columns.append("Fans")

if "Pumps" in df.columns:
    other_columns.append("Pumps")

if len(other_columns) > 0:

    df_final["Autre"] = df[other_columns].sum(axis=1)

# ============================================================
# REPLACE MAIN DATAFRAME
# ============================================================

df = df_final

# ============================================================
# CREATE TIME INDEX
# ============================================================

n = len(df)

df.index = pd.date_range(
    start="2024-01-01",
    periods=n,
    freq="h"
)

# Remove visible year
df.index = df.index.strftime('%m-%d %H:%M')

# ============================================================
# SELECT ONE DAY
# ============================================================

selected_day = "08-15"

df_day = df[df.index.str.startswith(selected_day)]

# ============================================================
# EXPORT CSV
# ============================================================

df.to_csv("hourly_electricity_breakdown.csv")

print("\nCSV exported successfully.")

# ============================================================
# PLOT STACKED AREA CHART
# ============================================================

plt.figure(figsize=(18, 8))

plt.stackplot(
    range(len(df_day)),
    df_day.T,
    labels=df_day.columns
)

plt.xticks(
    ticks=range(len(df_day)),
    labels=df_day.index,
    rotation=45
)

plt.legend(
    loc='upper left',
    bbox_to_anchor=(1.02, 1)
)

plt.title(
    f"Hourly Electricity Breakdown - {selected_day}"
)

plt.xlabel("Hour")

plt.ylabel("Electricity Consumption (kWh)")

plt.tight_layout()

plt.show()