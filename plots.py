import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
import openstudio
import re
from pathlib import Path
from core_2_MH import load_households

# ============================================================
# USER INPUT
# ============================================================

model_name = "ID39_MR_ND_1945"
building_name = "MR_ND_1945"
households_dict = load_households(r"MURBS_2026\dadesarquetips.csv")

for temp_name in households_dict:
    if building_name in temp_name:
        households = households_dict[temp_name]

lang = "eng"   # "eng" or "fr"

# ============================================================
# PATHS
# ============================================================

base_dir = Path("MURBS_2026")

osm_path = (
    base_dir /
    model_name /
    f"{model_name}.osm"
)

sql_path = (
    base_dir /
    model_name /
    model_name /
    "run" /
    "eplusout.sql"
)

output_folder = (
    base_dir /
    model_name /
    "output"
)

output_folder.mkdir(exist_ok=True)

# ============================================================
# LOAD OSM MODEL
# ============================================================

translator = openstudio.osversion.VersionTranslator()

osm = translator.loadModel(
    openstudio.path(str(osm_path))
)

if osm.empty():
    raise Exception("Failed to load model")

model = osm.get()

# ============================================================
# BUILD EQUIPMENT ID → DEFINITION MAP
# ============================================================

equipment_map = {}

for eq in model.getElectricEquipments():

    instance_name = eq.nameString()

    definition_name = (
        eq.electricEquipmentDefinition()
        .nameString()
    )

    match = re.search(
        r'Electric Equipment (\d+)',
        instance_name
    )

    if match:

        equipment_id = match.group(1)

        equipment_map[equipment_id] = definition_name

# ============================================================
# PRINT MAPPING
# ============================================================

print("\nEQUIPMENT ID MAPPING:\n")

for k, v in equipment_map.items():

    print(f"{k} --> {v}")

# ============================================================
# CONNECT TO SQL
# ============================================================

conn = sqlite3.connect(str(sql_path))

# ============================================================
# LOAD DHW / APPLIANCE DATA
# ============================================================

variable_name = "Electric Equipment Electricity Energy"

query = f"""
SELECT
    rdd.KeyValue,
    rd.TimeIndex,
    rd.Value

FROM ReportData rd

JOIN ReportDataDictionary rdd
ON rd.ReportDataDictionaryIndex =
   rdd.ReportDataDictionaryIndex

JOIN Time t
ON rd.TimeIndex = t.TimeIndex

JOIN EnvironmentPeriods ep
ON t.EnvironmentPeriodIndex =
   ep.EnvironmentPeriodIndex

WHERE rdd.Name = '{variable_name}'

AND ep.EnvironmentName = 'RUN PERIOD 1'
"""

df_raw = pd.read_sql_query(query, conn)

# ============================================================
# EXTRACT ONLY DHW (CHAUFFEAU)
# ============================================================

dhw_values = None

for key, group in df_raw.groupby("KeyValue"):

    try:

        match = re.search(
            r'EQUIPMENT (\d+)',
            key.upper()
        )

        if not match:
            continue

        equipment_id = match.group(1)

        if equipment_id not in equipment_map:
            continue

        definition_name = equipment_map[equipment_id]

        # ----------------------------------------------------
        # KEEP ONLY DHW
        # ----------------------------------------------------

        if definition_name.lower() != "chauffeau":
            continue

        group = group.sort_values("TimeIndex")

        values_kwh = (
            group["Value"] / 3.6e6
        ).tolist()

        if dhw_values is None:

            dhw_values = values_kwh

        else:

            dhw_values = [

                a + b

                for a, b in zip(
                    dhw_values,
                    values_kwh
                )
            ]

        print(f"Loaded DHW: {key}")

    except Exception as e:

        print(f"FAILED: {key}")
        print(e)

# ============================================================
# CREATE MAIN DATAFRAME
# ============================================================

df = pd.DataFrame()

df["DHW"] = dhw_values

# ============================================================
# LOAD SYSTEM METERS
# ============================================================

meter_names = {

    "InteriorLights": "InteriorLights:Electricity",

    "ExteriorLights": "ExteriorLights:Electricity",

    "InteriorEquipment": "InteriorEquipment:Electricity",

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

        JOIN Time t
        ON rd.TimeIndex = t.TimeIndex

        JOIN EnvironmentPeriods ep
        ON t.EnvironmentPeriodIndex =
           ep.EnvironmentPeriodIndex

        WHERE rmd.VariableName = '{meter_name}'

        AND ep.EnvironmentName = 'RUN PERIOD 1'
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
# CLOSE CONNECTION
# ============================================================

conn.close()

# ============================================================
# CREATE DATETIME INDEX
# ============================================================

df.index = pd.date_range(
    start="2024-01-01",
    periods=len(df),
    freq="h"
)

# ============================================================
# CREATE LIGHTING
# ============================================================

df["Lighting"] = (

    df.get("InteriorLights", 0)

    + df.get("ExteriorLights", 0)

)

# ============================================================
# CREATE PLUG LOADS
# ============================================================

df["PlugLoads"] = (

    df["InteriorEquipment"]

    - df["DHW"]

).clip(lower=0)

# ============================================================
# CREATE OTHER CATEGORY
# ============================================================

df["Other (Fans,...)"] = (

    df.get("Fans", 0)

    + df.get("Pumps", 0)

)

# ============================================================
# Per Household --> EUI
# ============================================================
df = df / households


# ============================================================
# MONTHLY AGGREGATION
# ============================================================

df_monthly = (
    df
    .resample("ME")
    .sum()
)

# ============================================================
# KEEP ONLY FINAL COLUMNS
# ============================================================

df_monthly = df_monthly[[

    'PlugLoads',
    'Other (Fans,...)',
    'Lighting',
    'DHW',
    'Heating',
    'Cooling'

]]

# ============================================================
# COLORS
# ============================================================

colors = {

    'Cooling': "#58b3e7",
    'DHW': 'darkred',
    'Heating': "#e95454ff",
    'PlugLoads': 'gray',
    'Lighting': 'gold',
    'Other (Fans,...)': 'lightgrey'

}

# ============================================================
# MONTHLY BAR CHART
# ============================================================

fig, ax = plt.subplots(
    1,
    1,
    figsize=(9, 5)
)

df_monthly.plot.bar(
    stacked=True,
    color=colors,
    ax=ax
)

ax.set_xlabel('')

if lang == "eng":

    ax.set_ylabel("Energy [kWh]")

    legend_english = {

        'PlugLoads': 'Plug Loads',
        "DHW": "Domestic/Service Hot Water",
        'Other (Fans,...)': 'Other (Fans,...)'

    }

    h, l = ax.get_legend_handles_labels()

    ax.legend(

        handles=h[::-1],

        labels=[

            legend_english[l_]
            if l_ in legend_english.keys()
            else l_

            for l_ in l

        ][::-1]

    )

    ax.set_xticklabels([

        'January',
        'February',
        'March',
        'April',
        'May',
        'June',
        'July',
        'August',
        'September',
        'October',
        'November',
        'December'

    ])

else:

    ax.set_ylabel("Consommation Mensuel [kWh]")

    legend_french = {

        'PlugLoads': 'Charges aux prises',
        'Lighting': 'Éclairage',
        'Other (Fans,...)': 'Autres (ventilateurs,...)',
        'Heating': "Chauffage",
        'Cooling': "Climatisation",
        "DHW": "Eau Chaude"

    }

    h, l = ax.get_legend_handles_labels()

    ax.legend(

        handles=h[::-1],

        labels=[

            legend_french[l_]
            for l_ in l

        ][::-1]

    )

    ax.set_xticklabels([

        'Janvier',
        'Février',
        'Mars',
        'Avril',
        'Mai',
        'Juin',
        'Juil',
        'Août',
        'Septembre',
        'Octobre',
        'Novembre',
        'Décembre'

    ])

plt.xticks(rotation=45)

plt.tight_layout()

# ============================================================
# SAVE MONTHLY BAR CHART
# ============================================================

monthly_output = (
    output_folder /
    "monthly_end_use_breakdown.png"
)

plt.savefig(
    monthly_output,
    dpi=300,
    bbox_inches="tight"
)

plt.close()

print(f"\nSaved:\n{monthly_output}")

# ============================================================
# DAILY STACKED AREA PLOTS
# ============================================================

def plot_daily_profile(df,
                       selected_day,
                       columns_to_plot,
                       title,
                       output_name):

    # --------------------------------------------------------
    # SELECT DAY
    # --------------------------------------------------------

    df_day = df[
        df.index.strftime('%m-%d') == selected_day
    ]

    # --------------------------------------------------------
    # KEEP ONLY REQUIRED COLUMNS
    # --------------------------------------------------------

    df_day = df_day[columns_to_plot]

    # --------------------------------------------------------
    # CREATE FIGURE
    # --------------------------------------------------------

    fig, ax = plt.subplots(
        1,
        1,
        figsize=(10, 5)
    )

    # --------------------------------------------------------
    # STACKPLOT
    # --------------------------------------------------------

    ax.stackplot(

        range(len(df_day)),

        *[
            df_day[col]
            for col in columns_to_plot
        ],

        labels=columns_to_plot,

        colors=[
            colors[col]
            for col in columns_to_plot
        ]

    )

    # --------------------------------------------------------
    # X AXIS
    # --------------------------------------------------------

    ax.set_xticks(range(0, 24, 2))

    ax.set_xticklabels([

        f"{h}:00"

        for h in range(0, 24, 2)

    ])

    # --------------------------------------------------------
    # LABELS
    # --------------------------------------------------------

    ax.set_xlabel("Time of Day")

    ax.set_ylabel("Electric Consumption [kWh]")

    ax.set_title(title)

    # --------------------------------------------------------
    # LEGEND
    # --------------------------------------------------------

    legend_english = {

        'PlugLoads': 'Plug Loads',
        "DHW": "Domestic/Service Hot Water",
        'Other (Fans,...)': 'Other (Fans,...)'

    }

    h, l = ax.get_legend_handles_labels()

    ax.legend(

        handles=h[::-1],

        labels=[

            legend_english[x]
            if x in legend_english
            else x

            for x in l

        ][::-1]

    )

    # --------------------------------------------------------
    # SAVE
    # --------------------------------------------------------

    plt.tight_layout()

    output_path = (
        output_folder /
        output_name
    )

    plt.savefig(
        output_path,
        dpi=300,
        bbox_inches="tight"
    )

    plt.close()

    print(f"\nSaved:\n{output_path}")

# ============================================================
# SUMMER PROFILE
# ============================================================

summer_columns = [

    'PlugLoads',
    'Other (Fans,...)',
    'Lighting',
    'DHW',
    'Cooling'

]

plot_daily_profile(

    df=df,

    selected_day="08-15",

    columns_to_plot=summer_columns,

    title="Summer Daily Electricity Profile",

    output_name="summer_daily_profile.png"

)

# ============================================================
# WINTER PROFILE
# ============================================================

winter_columns = [

    'PlugLoads',
    'Other (Fans,...)',
    'Lighting',
    'DHW',
    'Heating'

]

plot_daily_profile(

    df=df,

    selected_day="02-15",

    columns_to_plot=winter_columns,

    title="Winter Daily Electricity Profile",

    output_name="winter_daily_profile.png"

)

print("\nAll plots generated successfully.")

del model
del osm
