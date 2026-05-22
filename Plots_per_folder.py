def generate_energy_plots(path,households_dict,lang="eng"):

    import sqlite3
    import pandas as pd
    import matplotlib.pyplot as plt
    import openstudio
    import re
    from pathlib import Path
    import os

    # ========================================================
    # EXTRACT BUILDING NAME
    # ========================================================

    folder_name = os.path.basename(path)
    parts = folder_name.split("_")
    building_id = parts[0]
    building_type = parts[1]
    building_name = parts[2]
    building_vintage = parts[3]

    households = None

    for temp_name in households_dict:

        if building_name in temp_name:

            households = households_dict[temp_name]

            break

    if households is None:
        raise Exception(
            f"Could not find households for {building_name}"
        )

    # ========================================================
    # PATHS
    # ========================================================

    base_dir = Path("MURBS_2026")

    osm_path = (
        base_dir /
        folder_name /
        f"{folder_name}.osm"
    )

    sql_path = (
        base_dir /
        folder_name /
        folder_name /
        "run" /
        "eplusout.sql"
    )

    output_folder = (
        base_dir /
        folder_name /
        "output"
    )

    output_folder.mkdir(exist_ok=True)

    # ========================================================
    # LOAD OSM MODEL
    # ========================================================

    translator = openstudio.osversion.VersionTranslator()

    osm = translator.loadModel(
        openstudio.path(str(osm_path))
    )

    if osm.empty():
        raise Exception("Failed to load model")

    model = osm.get()

    # ========================================================
    # BUILD EQUIPMENT MAP
    # ========================================================

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

    # ========================================================
    # CONNECT TO SQL
    # ========================================================

    conn = sqlite3.connect(str(sql_path))

    # ========================================================
    # LOAD ELECTRIC EQUIPMENT DATA
    # ========================================================

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

    # ========================================================
    # EXTRACT DHW
    # ========================================================

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

        except Exception as e:

            print(f"FAILED: {key}")
            print(e)

    # ========================================================
    # MAIN DATAFRAME
    # ========================================================

    df = pd.DataFrame()

    df["DHW"] = dhw_values

    # ========================================================
    # LOAD METERS
    # ========================================================

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
                continue

            meter_df = meter_df.sort_values("TimeIndex")

            values_kwh = (
                meter_df["VariableValue"] / 3.6e6
            ).tolist()

            df[label] = values_kwh

        except Exception as e:

            print(f"FAILED meter: {meter_name}")
            print(e)

    conn.close()

    # ========================================================
    # DATETIME INDEX
    # ========================================================

    df.index = pd.date_range(
        start="2024-01-01",
        periods=len(df),
        freq="h"
    )

    # ========================================================
    # CREATE CATEGORIES
    # ========================================================

    df["Lighting"] = (

        df.get("InteriorLights", 0)

        + df.get("ExteriorLights", 0)

    )

    df["PlugLoads"] = (

        df["InteriorEquipment"]

        - df["DHW"]

    ).clip(lower=0)

    df["Other (Fans,...)"] = (

        df.get("Fans", 0)

        + df.get("Pumps", 0)

    )

    # ========================================================
    # NORMALIZE PER HOUSEHOLD
    # ========================================================

    df = df / households

    # ========================================================
    # MONTHLY AGGREGATION
    # ========================================================

    df_monthly = (
        df
        .resample("ME")
        .sum()
    )

    df_monthly = df_monthly[[

        'PlugLoads',
        'Other (Fans,...)',
        'Lighting',
        'DHW',
        'Heating',
        'Cooling'

    ]]

    # ========================================================
    # COLORS
    # ========================================================

    colors = {

        'Cooling': "#58b3e7",
        'DHW': 'darkred',
        'Heating': "#e95454ff",
        'PlugLoads': 'gray',
        'Lighting': 'gold',
        'Other (Fans,...)': 'lightgrey'

    }

    # ========================================================
    # MONTHLY BAR CHART
    # ========================================================

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

    ax.set_ylabel("Energy [kWh / household]")

    plt.xticks(rotation=45)

    plt.tight_layout()

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

    # ========================================================
    # DAILY PROFILE FUNCTION
    # ========================================================

    def plot_daily_profile(selected_day,
                           columns_to_plot,
                           title,
                           output_name):

        df_day = df[
            df.index.strftime('%m-%d') == selected_day
        ]

        df_day = df_day[columns_to_plot]

        fig, ax = plt.subplots(
            1,
            1,
            figsize=(10, 5)
        )

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

        ax.set_xticks(range(0, 24, 2))

        ax.set_xticklabels([

            f"{h}:00"

            for h in range(0, 24, 2)

        ])

        ax.set_ylabel(
            "Electric Consumption [kWh / household]"
        )

        ax.set_title(title)

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

    # ========================================================
    # SUMMER PROFILE
    # ========================================================

    plot_daily_profile(

        selected_day="08-15",

        columns_to_plot=[

            'PlugLoads',
            'Other (Fans,...)',
            'Lighting',
            'DHW',
            'Cooling'

        ],

        title="Summer Daily Electricity Profile",

        output_name="summer_daily_profile.png"

    )

    # ========================================================
    # WINTER PROFILE
    # ========================================================

    plot_daily_profile(

        selected_day="02-15",

        columns_to_plot=[

            'PlugLoads',
            'Other (Fans,...)',
            'Lighting',
            'DHW',
            'Heating'

        ],

        title="Winter Daily Electricity Profile",

        output_name="winter_daily_profile.png"

    )

    del model
    del osm

    print(f"\nFinished processing {folder_name}")

    return monthly_output, output_folder /"summer_daily_profile.png" , output_folder /"winter_daily_profile.png"