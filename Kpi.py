from Lit_IMA_METEO import Read_Parquets
from prism import Prism
import statsmodels.api as sm
import pandas as pd
from timeit import default_timer as timer
import glob
import os

###### Display elapsed time #######################
def printTime(stTexte, liTime):
    liTime.append(timer())
    return print(str(round(liTime[-1] - liTime[-2], 1)) + ' s =>' + stTexte)


class AnalyseProfil():
    def __init__(self):
        pass

    def getDataset(self, Identifiant, file):
        InstCls_parquet = Read_Parquets()
        return InstCls_parquet.get_data(Identifiant=Identifiant)

    def RunAnalyse(self, Identifiant, file):

        # Get data
        self.Identifiant = Identifiant
        pd_Alldata_id = file
        pd_Alldata_id['dateinterval'] = pd.to_datetime(pd_Alldata_id['dateinterval'])
        pd_Alldata_id["Jourlocal"] = pd_Alldata_id["dateinterval"].dt.date
        pd_Alldata_id["Heurelocal"] = pd_Alldata_id["dateinterval"].dt.hour

        # Prism analysis
        pd_Alldata_id_Quo = pd_Alldata_id.groupby(pd_Alldata_id['dateinterval'].dt.date).agg(
            {"energieactivelivree_kwh": 'sum',
             "temperatureatmospherique": 'mean'}).reset_index()

        list_P = pd_Alldata_id_Quo["energieactivelivree_kwh"].to_list()  # daily sum of delivered active energy
        list_T = pd_Alldata_id_Quo["temperatureatmospherique"].to_list()  # daily mean of 15‑min temperature (source data are hourly)

        InstClsPrism = Prism(QuotikWh=list_P, QuotiTemp=list_T)
        res = InstClsPrism.calcul()
        # print(InstClsPrism.param) # dict of results
        # InstClsPrism.trace(Identifiant) # plot the graph

        dict_caracteristiques = {}
        dict_caracteristiques["Identifiant"] = self.Identifiant

        '''
        The suggested list of quantities of interest addresses the following characteristics:

        - Annual data:
        (1) Annual electricity consumption [kWh];
        (2) Annual gas consumption [kWh or m³];
        (3) Annual oil consumption [kWh or m³];
        (4) Annual wood or pellet consumption [kWh];
        (5) Daily base electric consumption [kWh/day]
            (days where the daily mean temperature is between 8 and 15°C) – see Figure 1;
        (6) Heating slope (electricity) [W/K]
            (days where the daily mean temperature is ≤ 8°C) (electric profile) – see Figure 1;
        (7) Cooling slope (electricity) [W/K]
            (days where the daily mean temperature is ≥ 15°C) (electric profile) – see Figure 1;
        (8) Heating slope (gas – if monthly data are available) [W/K] – see Figure 2;

        - Electric load profile:
        (9) Morning winter electric peak [kW], i.e. the maximum average power over one time step
            (ideally max 1 h) for days where the daily mean temperature is ≤ 8°C;
        (10) Time of morning winter peak (integer from 0 to 11 inclusive)
             – to be evaluated against the average winter profile;
        (11) Evening winter electric peak [kW], i.e. the maximum average power over one time step
             (ideally max 1 h) for days where the daily mean temperature is ≤ 8°C;
        (12) Time of evening winter peak (integer from 12 to 23 inclusive)
             – to be evaluated against the average winter profile;
        (13) Morning summer electric peak [kW], i.e. the maximum average power over one time step
             (ideally max 1 h) for days where the daily mean temperature is ≥ 15°C;
        (14) Time of morning summer peak (integer from 0 to 11 inclusive)
             – to be evaluated against the average summer profile;
        (15) Evening summer electric peak [kW], i.e. the maximum average power over one time step
             (ideally max 1 h) for days where the daily mean temperature is ≥ 15°C;
        (16) Time of evening summer peak (integer from 12 to 23 inclusive)
             – to be evaluated against the average summer profile;
        (17) Average daily standard deviation of electric consumption during winter days
             where the daily mean temperature is ≤ 8°C [kWh] (ideally time step ≤ 1 h);
        (18) Average daily standard deviation of electric consumption during summer days
             where the daily mean temperature is ≥ 15°C [kWh] (ideally time step ≤ 1 h);
        (19) Average daily standard deviation of electric consumption during shoulder‑season days
             where the daily mean temperature is between 8 and 15°C [kWh] (ideally time step ≤ 1 h);
        (20) Load factor during winter where the daily mean temperature is ≤ 8°C [%].
             The load factor is the ratio between the mean step consumption and
             the maximum step consumption. Ideally, the time step is ≤ 1 h.
        (21) Load factor during summer where the daily mean temperature is ≥ 15°C [%];
        (22) Load factor during shoulder seasons where the daily mean temperature
             is between 8 and 15°C [%];
        (23) Ratio between mean daytime consumption (6 h to 22 h) and nighttime consumption
             during winter days where the daily mean temperature is ≤ 8°C [-];
        (24) Ratio between mean daytime consumption (6 h to 22 h) and nighttime consumption
             during summer days where the daily mean temperature is ≥ 15°C [-];
        (25) Ratio between mean daytime consumption (6 h to 22 h) and nighttime consumption
             during shoulder‑season days where the daily mean temperature is between 8 and 15°C [-].
        '''

        # Data for winter days
        filter_h_T = (pd_Alldata_id_Quo["temperatureatmospherique"] <= 8)
        tempopd_Alldata_id_Quo_h = pd_Alldata_id_Quo[filter_h_T][["dateinterval"]].drop_duplicates()
        tempopd_Alldata_id_Quo_h = tempopd_Alldata_id_Quo_h.rename(columns={"dateinterval": "Jourlocal"})

        filter_h_d = ((pd_Alldata_id["dateinterval"].dt.month >= 12) |
                      (pd_Alldata_id["dateinterval"].dt.month <= 4))
        tempo_pd_Alldata_id_h = pd_Alldata_id[filter_h_d]

        pd_Alldata_id_h = pd.merge(tempo_pd_Alldata_id_h, tempopd_Alldata_id_Quo_h,
                                   on="Jourlocal", how='inner').reset_index()

        # Data for summer days
        filter_e_T = (pd_Alldata_id_Quo["temperatureatmospherique"] >= 15)
        tempopd_Alldata_id_Quo_e = pd_Alldata_id_Quo[filter_e_T][["dateinterval"]].drop_duplicates()
        tempopd_Alldata_id_Quo_e = tempopd_Alldata_id_Quo_e.rename(columns={"dateinterval": "Jourlocal"})

        filter_e_d = ((pd_Alldata_id["dateinterval"].dt.month >= 5) &
                      (pd_Alldata_id["dateinterval"].dt.month <= 11))
        tempo_pd_Alldata_id_e = pd_Alldata_id[filter_e_d]

        pd_Alldata_id_e = pd.merge(tempo_pd_Alldata_id_e, tempopd_Alldata_id_Quo_e,
                                   on="Jourlocal", how='inner').reset_index()

        # Data for shoulder‑season days
        filter_ms_T = ((pd_Alldata_id_Quo["temperatureatmospherique"] > 8) &
                       (pd_Alldata_id_Quo["temperatureatmospherique"] < 15))
        tempopd_Alldata_id_Quo_ms = pd_Alldata_id_Quo[filter_ms_T][["dateinterval"]].drop_duplicates()
        tempopd_Alldata_id_Quo_ms = tempopd_Alldata_id_Quo_ms.rename(columns={"dateinterval": "Jourlocal"})

        filter_ms_d = (((pd_Alldata_id["dateinterval"].dt.month >= 4) &
                        (pd_Alldata_id["dateinterval"].dt.month <= 6)) |
                       ((pd_Alldata_id["dateinterval"].dt.month >= 9) &
                        (pd_Alldata_id["dateinterval"].dt.month <= 10)))
        tempo_pd_Alldata_id_ms = pd_Alldata_id[filter_ms_d]

        pd_Alldata_id_ms = pd.merge(tempo_pd_Alldata_id_ms, tempopd_Alldata_id_Quo_ms,
                                    on="Jourlocal", how='inner').reset_index()

        # _______________________________
        # (1) Annual electricity consumption [kWh]
        dict_caracteristiques["Conso_annuelle_electricite_kWh"] = pd_Alldata_id_Quo["energieactivelivree_kwh"].sum()

        # _______________________________
        # (2) Annual gas consumption [kWh or m³]
        dict_caracteristiques["Conso_annuelle_gaz_kWh"] = None

        # _______________________________
        # (3) Annual oil consumption [kWh or m³]
        dict_caracteristiques["Conso_annuelle_mazout_kWh"] = None

        # _______________________________
        # (4) Annual wood or pellet consumption [kWh]
        dict_caracteristiques["Conso_annuelle_bois_granules_kWh"] = None

        # _______________________________
        # (5) Daily base electric consumption [kWh/day]
        # (days where daily mean temperature is between 8 and 15°C)
        # dict_caracteristiques["Conso_base_electricite"] = ...
        dict_caracteristiques["Conso_base_electricite_kWhParJour"] = InstClsPrism.param["Base [kW]"]

        # _______________________________
        # (6) Heating slope (electricity) [W/K]
        # (days where daily mean temperature is ≤ 8°C)
        # dict_caracteristiques["Pente_chauffage_electricite"] = sm.WLS(...)
        dict_caracteristiques["Pente_chauffage_electricite_WparK"] = \
            InstClsPrism.param["kch [kW/°C]"] * 1000 / 24

        # _______________________________
        # (7) Cooling slope (electricity) [W/K]
        # (days where daily mean temperature is ≥ 15°C)
        dict_caracteristiques["Pente_climatisation_electricite_WparK"] = \
            InstClsPrism.param["kcl [kW/°C]"] * 1000 / 24

        # _______________________________
        # (8) Heating slope (gas) [W/K] – if monthly gas data are available
        dict_caracteristiques["Pente_chauffage_gaz_WparK"] = None

        # _______________________________
        # (9) Morning winter electric peak [kW]
        #   max average power over one time step (ideally ≤ 1 h)
        #   during days with daily mean temperature ≤ 8°C
        # Filter winter data for morning hours
        tempo_pd_Alldata_id = pd_Alldata_id_h[pd_Alldata_id_h["Heurelocal"] <= 11].reset_index()

        # Select highest value
        dict_caracteristiques["Pointe_hiver_am_kW"] = \
            tempo_pd_Alldata_id.iloc[tempo_pd_Alldata_id['energieactivelivree_kwh'].idxmax()][
                "energieactivelivree_kwh"]  # [kWh/1h] to kW

        # _______________________________
        # (10) Time of morning winter electric peak [0–11]
        dict_caracteristiques["Pointe_h_hiver_am"] = \
            tempo_pd_Alldata_id.iloc[tempo_pd_Alldata_id['energieactivelivree_kwh'].idxmax()]["Heurelocal"]

        # _______________________________
        # (11) Evening winter electric peak [kW]
        tempo_pd_Alldata_id = pd_Alldata_id_h[pd_Alldata_id_h["Heurelocal"] >= 12].reset_index()

        dict_caracteristiques["Pointe_hiver_pm_kW"] = \
            tempo_pd_Alldata_id.iloc[tempo_pd_Alldata_id['energieactivelivree_kwh'].idxmax()][
                "energieactivelivree_kwh"]  # [kWh/1h] to kW

        # _______________________________
        # (12) Time of evening winter electric peak [12–23]
        dict_caracteristiques["Pointe_h_hiver_pm"] = \
            tempo_pd_Alldata_id.iloc[tempo_pd_Alldata_id['energieactivelivree_kwh'].idxmax()]["Heurelocal"]

        # _______________________________
        # (13) Morning summer electric peak [kW]
        tempo_pd_Alldata_id = pd_Alldata_id_e[pd_Alldata_id_e["Heurelocal"] <= 11].reset_index()

        dict_caracteristiques["Pointe_ete_am_kW"] = \
            tempo_pd_Alldata_id.iloc[tempo_pd_Alldata_id['energieactivelivree_kwh'].idxmax()][
                "energieactivelivree_kwh"]  # [kWh/1h] to kW

        # _______________________________
        # (14) Time of morning summer electric peak [0–11]
        dict_caracteristiques["Pointe_h_ete_am"] = \
            tempo_pd_Alldata_id.iloc[tempo_pd_Alldata_id['energieactivelivree_kwh'].idxmax()]["Heurelocal"]

        # _______________________________
        # (15) Evening summer electric peak [kW]
        tempo_pd_Alldata_id = pd_Alldata_id_e[pd_Alldata_id_e["Heurelocal"] >= 12].reset_index()

        dict_caracteristiques["Pointe_ete_pm_kW"] = \
            tempo_pd_Alldata_id.iloc[tempo_pd_Alldata_id['energieactivelivree_kwh'].idxmax()][
                "energieactivelivree_kwh"]  # [kWh/1h] to kW

        # _______________________________
        # (16) Time of evening summer electric peak [12–23]
        dict_caracteristiques["Pointe_h_ete_pm"] = \
            tempo_pd_Alldata_id.iloc[tempo_pd_Alldata_id['energieactivelivree_kwh'].idxmax()]["Heurelocal"]

        # _______________________________
        # (17) Average daily standard deviation of winter electric consumption [kWh]
        #   (days where daily mean temperature ≤ 8°C)
        #   Compute std per day then mean of these values (kWh/15min)
        dict_caracteristiques["EcartType_Quotidien_hiver"] = \
            pd_Alldata_id_h[["Jourlocal", "energieactivelivree_kwh"]].groupby("Jourlocal").std()[
                "energieactivelivree_kwh"].mean()

        # _______________________________
        # (18) Average daily standard deviation of summer electric consumption [kWh]
        dict_caracteristiques["EcartType_Quotidien_ete"] = \
            pd_Alldata_id_e[["Jourlocal", "energieactivelivree_kwh"]].groupby("Jourlocal").std()[
                "energieactivelivree_kwh"].mean()

        # _______________________________
        # (19) Average daily standard deviation of shoulder‑season electric consumption [kWh]
        dict_caracteristiques["EcartType_Quotidien_misaison"] = \
            pd_Alldata_id_ms[["Jourlocal", "energieactivelivree_kwh"]].groupby("Jourlocal").std()[
                "energieactivelivree_kwh"].mean()

        # _______________________________
        # (20) Winter load factor [%] (daily mean step consumption / max step consumption)
        #   Average of daily load factors
        tempo_dfFU = pd_Alldata_id_h[["Jourlocal", "energieactivelivree_kwh"]].groupby("Jourlocal").agg(
            {'energieactivelivree_kwh': ['mean', 'min', 'max']})

        tempo_dfFU["FU"] = tempo_dfFU["energieactivelivree_kwh"]["mean"] / \
                           tempo_dfFU["energieactivelivree_kwh"]["max"]

        dict_caracteristiques["FU_Quotidien_hiver_%"] = tempo_dfFU["FU"].mean() * 100

        # _______________________________
        # (21) Summer load factor [%]
        tempo_dfFU = pd_Alldata_id_e[["Jourlocal", "energieactivelivree_kwh"]].groupby("Jourlocal").agg(
            {'energieactivelivree_kwh': ['mean', 'min', 'max']})

        tempo_dfFU["FU"] = tempo_dfFU["energieactivelivree_kwh"]["mean"] / \
                           tempo_dfFU["energieactivelivree_kwh"]["max"]

        dict_caracteristiques["FU_Quotidien_ete_%"] = tempo_dfFU["FU"].mean() * 100

        # _______________________________
        # (22) Shoulder‑season load factor [%]
        tempo_dfFU = pd_Alldata_id_ms[["Jourlocal", "energieactivelivree_kwh"]].groupby("Jourlocal").agg(
            {'energieactivelivree_kwh': ['mean', 'min', 'max']})

        tempo_dfFU["FU"] = tempo_dfFU["energieactivelivree_kwh"]["mean"] / \
                           tempo_dfFU["energieactivelivree_kwh"]["max"]

        dict_caracteristiques["FU_Quotidien_misaison_%"] = tempo_dfFU["FU"].mean() * 100

        # _______________________________
        # (23) Ratio of mean day (6–22 h) to night consumption during winter days
        # Compute day and night consumptions
        filter_23_J_d = (pd_Alldata_id_h["Heurelocal"] >= 6) & (pd_Alldata_id_h["Heurelocal"] <= 21)
        tempo_pd_Alldata_id_J = pd_Alldata_id_h[filter_23_J_d][["Jourlocal", "energieactivelivree_kwh"]].groupby(
            "Jourlocal").mean()
        tempo_pd_Alldata_id_J = tempo_pd_Alldata_id_J.rename(
            columns={"energieactivelivree_kwh": "energieactivelivree_kwh_J"})

        filter_23_N_d = (pd_Alldata_id_h["Heurelocal"] <= 5) | (pd_Alldata_id_h["Heurelocal"] >= 22)
        tempo_pd_Alldata_id_N = pd_Alldata_id_h[filter_23_N_d][["Jourlocal", "energieactivelivree_kwh"]].groupby(
            "Jourlocal").mean()
        tempo_pd_Alldata_id_N = tempo_pd_Alldata_id_N.rename(
            columns={"energieactivelivree_kwh": "energieactivelivree_kwh_N"})

        tempo_dfRatio = pd.merge(tempo_pd_Alldata_id_N, tempo_pd_Alldata_id_J,
                                 on="Jourlocal", how='inner')

        dict_caracteristiques["RatioJN_Quotidien_hiver"] = \
            (tempo_dfRatio["energieactivelivree_kwh_J"] /
             tempo_dfRatio["energieactivelivree_kwh_N"]).mean()

        # _______________________________
        # (24) Ratio of mean day (6–22 h) to night consumption during summer days
        filter_23_J_d = (pd_Alldata_id_e["Heurelocal"] >= 6) & (pd_Alldata_id_e["Heurelocal"] <= 21)
        tempo_pd_Alldata_id_J = pd_Alldata_id_e[filter_23_J_d][["Jourlocal", "energieactivelivree_kwh"]].groupby(
            "Jourlocal").mean()
        tempo_pd_Alldata_id_J = tempo_pd_Alldata_id_J.rename(
            columns={"energieactivelivree_kwh": "energieactivelivree_kwh_J"})

        filter_23_N_d = (pd_Alldata_id_e["Heurelocal"] <= 5) | (pd_Alldata_id_e["Heurelocal"] >= 22)
        tempo_pd_Alldata_id_N = pd_Alldata_id_e[filter_23_N_d][["Jourlocal", "energieactivelivree_kwh"]].groupby(
            "Jourlocal").mean()
        tempo_pd_Alldata_id_N = tempo_pd_Alldata_id_N.rename(
            columns={"energieactivelivree_kwh": "energieactivelivree_kwh_N"})

        tempo_dfRatio = pd.merge(tempo_pd_Alldata_id_N, tempo_pd_Alldata_id_J,
                                 on="Jourlocal", how='inner')

        dict_caracteristiques["RatioJN_Quotidien_ete"] = \
            (tempo_dfRatio["energieactivelivree_kwh_J"] /
             tempo_dfRatio["energieactivelivree_kwh_N"]).mean()

        # _______________________________
        # (25) Ratio of mean day (6–22 h) to night consumption during shoulder‑season days
        filter_23_J_d = (pd_Alldata_id_ms["Heurelocal"] >= 6) & (pd_Alldata_id_ms["Heurelocal"] <= 21)
        tempo_pd_Alldata_id_J = pd_Alldata_id_ms[filter_23_J_d][["Jourlocal", "energieactivelivree_kwh"]].groupby(
            "Jourlocal").mean()
        tempo_pd_Alldata_id_J = tempo_pd_Alldata_id_J.rename(
            columns={"energieactivelivree_kwh": "energieactivelivree_kwh_J"})

        filter_23_N_d = (pd_Alldata_id_ms["Heurelocal"] <= 5) | (pd_Alldata_id_ms["Heurelocal"] >= 22)
        tempo_pd_Alldata_id_N = pd_Alldata_id_ms[filter_23_N_d][["Jourlocal", "energieactivelivree_kwh"]].groupby(
            "Jourlocal").mean()
        tempo_pd_Alldata_id_N = tempo_pd_Alldata_id_N.rename(
            columns={"energieactivelivree_kwh": "energieactivelivree_kwh_N"})

        tempo_dfRatio = pd.merge(tempo_pd_Alldata_id_N, tempo_pd_Alldata_id_J,
                                 on="Jourlocal", how='inner')

        dict_caracteristiques["RatioJN_Quotidien_misaison"] = \
            (tempo_dfRatio["energieactivelivree_kwh_J"] /
             tempo_dfRatio["energieactivelivree_kwh_N"]).mean()

        self.InstClsPrism = InstClsPrism
        self.pd_Alldata_id = pd_Alldata_id
        self.pd_Alldata_id_Quo = pd_Alldata_id_Quo
        self.dict_caracteristiques = dict_caracteristiques

        return dict_caracteristiques
