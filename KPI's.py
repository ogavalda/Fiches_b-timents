#data parquet imported
#Calculation_per_household
import pandas as pd
from Kpi import AnalyseProfil
import glob
import os
from pathlib import Path
import re
from core_2 import get_vintage_column

### This will process only one file
    ## it takes one file at a time
    ## reads its timeseries and generates its kpi's
    ## it then maps its name with corresponding vintage ope time series then generates its kpi's
    ## puts both into a comparison table


#directory for eui files
eui_dir_unsorted = Path("../EUI_weather")
eui_dir= sorted(eui_dir_unsorted.glob("bat*_*.csv"))

i=0
all_kpis = []
for eui_file in eui_dir:

    # Extract building name from the
    match = re.search(r"bat(\d+)_(\d{4})", eui_file.stem)
    if not match:
        continue
    print(f"file number : {i}")
    i+=1
    bat_id = match.group(1)
    year = match.group(2)
    print(f"year : {year}")
    print(f"bat_id : {bat_id}")

    main_df = pd.read_csv(eui_file)
    main_df.rename(columns={'DateInterval': 'dateinterval',  # timestamp as in th eui file
                                            'EUI':"energieactivelivree_kwh",
                                            'DryBulb_C': 'temperatureatmospherique'}, inplace=True)
    InstClsAnalyse = AnalyseProfil()
    Identifiant = f"Bat_{bat_id}"
    InstClsAnalyse.RunAnalyse(Identifiant=Identifiant, file=main_df)
    all_kpis.append(InstClsAnalyse.dict_caracteristiques)



kpi_all_df = pd.DataFrame(all_kpis)

#Create csv file
kpi_all_df.to_csv("All_Bat_KPI.csv",index=False)
