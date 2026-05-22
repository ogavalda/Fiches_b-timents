# -*- coding: utf-8 -*-
"""
Created on Wed Jun 14 09:14:30 2023

@author: cv1751
"""

import pandas as pd
import polars as pl
class Read_Parquets():
    #stPath = u'C:\\Brice\\ope\\' #Répertoire contenant les données (parquet)
    #stPath = u'N:\\Mes documents\\Projet\Parc virtuel\\PartageOPE\\Source\\20231218\\'
    stPath = u'C:\\Users\\oriol\\Concordia University - Canada\Archetypes_exchange_MERN - General\\C Electricity data\\OPE HQ survey (residential)\\'
    stfileIMA = u'OPE_Consommation.parquet'
    stFileMeteo = 'OPE_Meteo.parquet'
    stFileStation= 'OPE_Station.parquet'

    def __init__(self):
        pass

    def get_IMA_Identifiant(self, stPath, stFileName, Identifiant):

        dfp = pl.scan_parquet(stPath+stFileName, low_memory=True)
        df = dfp.filter(pl.col("Identifiant") == Identifiant).collect(streaming=True)
        return df.to_pandas()

    def get_Parquet(self, stPath, stFileName):

        dfp = pl.scan_parquet(stPath+stFileName, low_memory=True)
        df = dfp.collect(streaming=True)
        return df.to_pandas()
    
    def get_data(self, Identifiant):
        self.Identifiant = Identifiant
        #Chargement en mémoire des données de consommation aux 15 minutes (1 an)    
        pdIMA = self.get_IMA_Identifiant(self.stPath, self.stfileIMA, self.Identifiant)
        pdIMA["Jourutc"] = pdIMA["dateintervalutc"].dt.date
        pdIMA["Heureutc"] = pdIMA["dateintervalutc"].dt.hour


        #Changement en mémoire des données météorologiques horaire (1 an)
        pdMeteo = self.get_Parquet(self.stPath, self.stFileMeteo)
        pdMeteo["Jourutc"] = pdMeteo["datetemperatureutc"].dt.date
        pdMeteo["Heureutc"] = pdMeteo["datetemperatureutc"].dt.hour
        #Changement en mémoire des stations météorologiques
        pdStation = self.get_Parquet(self.stPath, self.stFileStation)

        #jointure de la Station et de la consommation - puis de la température
        pd_Alldata_id = pd.merge(pdIMA, pdStation, how="left", on="Identifiant")
        pd_Alldata_id = pd.merge(pd_Alldata_id, pdMeteo, on=["CodeStationMeteoHQ", "Jourutc", "Heureutc"], how='left')
        
        return pd_Alldata_id

if __name__ == "__main__":
    
    InstCls_parquet = Read_Parquets()
    pd_Alldata_id = InstCls_parquet.get_data(Identifiant="1") 

    