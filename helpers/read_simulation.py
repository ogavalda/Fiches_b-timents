# imports
from sqlite3 import connect
import pandas as pd

import os


# A class which allows easily accessing and retrieving simulation results at a provided file location
class ReadSimulation():
    def __init__(self, run_path):
        results_folder = "eplusout.sql"
        self.set_file_path(run_path+"\\"+results_folder)
        return
        

    def set_file_path(self, path):
        self.path = path
        #print("Good job, you just set the path!")
        return

    def get_file_path(self):
        return self.path

    def query_file(self, query):
        # open file
        conn = connect(self.get_file_path())

        ### read time index : 
        # if design periods are included in results, we have to query as follows : 
        # this query selects the time index for only the period corresponding to the full simulation. 
        # we can then use the time index to slice variables for this period only
        df_time = pd.read_sql('SELECT * FROM Time WHERE EnvironmentPeriodIndex LIKE 3 OR EnvironmentPeriodIndex LIKE 10', conn)
        d = {'TimeIndex': df_time['TimeIndex'], 'DateTime': pd.to_datetime(df_time[['Year', 'Month', 'Day', 'Hour', 'Minute']])}
        time = pd.DataFrame(data=d)
        time.set_index('TimeIndex', inplace=True)

        # read results from sql file
        results_ = pd.read_sql(query, conn)

        # close connection !!! 
        conn.close()

        if results_.empty:
            # return empty dataframe
            return results_
        else:
            # clean up dataframe
            results_.set_index('TimeIndex', inplace=True)
            # Use the timeindex to slice the results of only the simulation period; the first few rows are the results of the design days (when design days are included in simulation results)
            results_ = results_.loc[time.index[0]:].copy()
            results_['DateTime'] = time.loc[results_.index]['DateTime']
            results_.set_index('DateTime', inplace=True)

            return results_


    def get_electricityprofile(self):
        query = """SELECT TimeIndex, Value FROM ReportData WHERE ReportDataDictionaryIndex IN 
                            (SELECT ReportDataDictionaryIndex FROM ReportDataDictionary 
                            WHERE name LIKE "%Facility" AND ReportingFrequency LIKE "%Timestep")"""
        
        electiricty_profile = self.query_file(query)

        # derrive timestep from dataframe length : 
        timestep = self.get_timestep(electiricty_profile)
        
        # convert Joules (sum over timestep in minutes) to Watts
        return electiricty_profile/timestep/60

    def get_electricityprofile_kwh(self):
        electiricty_profile = self.get_electricityprofile()
        return (electiricty_profile.iloc[:-1]).resample('1h').mean()/1000 # kWh



    # function to get timeseries of the different loads
    def get_loadprofile(self, team_id, HW_key=''):
        if team_id=='poly':
            query = """SELECT ReportDataDictionary.ReportDataDictionaryIndex, TimeIndex, Value, KeyValue, name, units 
                    FROM ReportData 
                    FULL OUTER JOIN 
                        ReportDataDictionary ON ReportDataDictionary.ReportDataDictionaryIndex=ReportData.ReportDataDictionaryIndex
                    WHERE ReportDataDictionary.ReportDataDictionaryIndex IN 
                        (SELECT ReportDataDictionary.ReportDataDictionaryIndex 
                        FROM ReportDataDictionary 
                        WHERE (name LIKE "%Facility" AND ReportingFrequency LIKE "%Timestep")
                        OR (name LIKE "Heating%" AND ReportingFrequency LIKE "%Timestep")
                        OR (name LIKE "Cooling%" AND ReportingFrequency LIKE "%Timestep")
                        OR (name LIKE "InteriorLights%" AND ReportingFrequency LIKE "%Timestep")
                        OR (name LIKE "ExteriorLights%" AND ReportingFrequency LIKE "%Timestep")
                        OR (name LIKE "%InteriorEquipment%" AND ReportingFrequency LIKE "%Timestep")
                        OR (name LIKE "%Equipment Electricity%" AND ReportingFrequency LIKE "%Timestep"))
                    """
            
        else:
            # TODO : make sure this works
            query = f"""SELECT ReportDataDictionary.ReportDataDictionaryIndex, TimeIndex, Value, KeyValue, name, units 
                    FROM ReportData 
                    FULL OUTER JOIN 
                        ReportDataDictionary ON ReportDataDictionary.ReportDataDictionaryIndex=ReportData.ReportDataDictionaryIndex
                    WHERE ReportDataDictionary.ReportDataDictionaryIndex IN 
                        (SELECT ReportDataDictionary.ReportDataDictionaryIndex 
                        FROM ReportDataDictionary 
                        WHERE (name LIKE "%Facility" AND ReportingFrequency LIKE "%Hourly")
                        OR (name LIKE "Heating%" AND ReportingFrequency LIKE "%Hourly")
                        OR (name LIKE "Cooling%" AND ReportingFrequency LIKE "%Hourly")
                        OR (name LIKE "InteriorLights%" AND ReportingFrequency LIKE "%Hourly")
                        OR (name LIKE "ExteriorLights%" AND ReportingFrequency LIKE "%Hourly")
                        OR (name LIKE "%InteriorEquipment%" AND ReportingFrequency LIKE "%Hourly")
                        OR (name LIKE "{HW_key}" AND ReportingFrequency LIKE "%Hourly")) 
                    """

        
        raw_load_profile = self.query_file(query) # all data in single column, need to reformat dataframe

        # check units : has to be Joules
        if (len(raw_load_profile['Units'].unique())!=1) | (raw_load_profile['Units'].unique()[0]!='J'):
            raise Exception("Unit of parameter fetched does not correspond to expected Joules. Verify output file.")
    
        load_profile = raw_load_profile.reset_index()[['DateTime', 'KeyValue', 'Name', 'Value']].groupby(['Name', 'DateTime'])['Value'].sum().unstack(level=0)


        # rename columns
        column_names = {'Electricity:Facility':'Total Facility', 'ExteriorLights:Electricity':'ExtLights', 'InteriorLights:Electricity':'IntLights',
                        'InteriorEquipment:Electricity':'PlugLoads', 'Cooling:Electricity':'Cooling', 'Heating:Electricity':'Heating', 'Electric Equipment Electricity Energy':'DHW'}
        load_profile.rename(columns=column_names, inplace=True)

        # add ext and int lighting together
        load_profile['Lighting'] = load_profile['ExtLights'] + load_profile['IntLights']
        load_profile.drop(columns=['ExtLights', 'IntLights'], inplace=True)

        # subtract DHW consumption from plugloads 
        load_profile['PlugLoads'] = load_profile['PlugLoads'] - load_profile['DHW']

        # currenlty column with facility total elec consumption and then all end uses
        # calculate "other" from (tot - end uses)
        load_profile['Other (Fans,...)'] = (load_profile['Total Facility'] - (
            load_profile['Cooling']+load_profile['Heating']+load_profile['Lighting']+load_profile['PlugLoads']+load_profile['DHW'])).clip(lower=0)

        load_profile.drop(columns=['Total Facility'], inplace=True)

        # derrive timestep from simulation length : 
        timestep = self.get_timestep(load_profile)
        
        # convert Joules (sum over timestep in minutes) to Watts
        return load_profile/timestep/60


    
    # calculate timestep used in simulation, based on dataframe length
    def get_timestep(self, df):
        timestep = 60*8760/len(df.index)  # 60 minutes per hour divided by the number of timesteps per hour
        return timestep
    

    def get_outdoor_temperature(self):
        # open file
        conn = connect(self.get_file_path())

        # read time index of results
        # if design periods are included in results, we have to query as follows : 
        df_time = pd.read_sql('SELECT * FROM Time WHERE EnvironmentPeriodIndex LIKE 3', conn)
        d = {'TimeIndex': df_time['TimeIndex'], 'DateTime': pd.to_datetime(df_time[['Year', 'Month', 'Day', 'Hour', 'Minute']])}
        time = pd.DataFrame(data=d)
        time.set_index('TimeIndex', inplace=True)

        ## Read results
        query = """SELECT TimeIndex, Value FROM ReportData WHERE ReportDataDictionaryIndex IN 
                    (SELECT ReportDataDictionaryIndex FROM ReportDataDictionary 
                    WHERE name LIKE "Site Outdoor Air Drybulb Temperature")"""

        # read results from sql file
        results_ = pd.read_sql(query, conn)

        # close connection !!! important to keep file accessible !!!
        conn.close()

        # add treatment results
        try : 
            results_.set_index('TimeIndex', inplace=True)
            # cut off the first few rows, since they are the results of the design days (when design days are included in simulation results)
            results_ = results_.loc[time.index[0]:].copy()
            results_['DateTime'] = time.loc[results_.index]['DateTime']
            results_.set_index('DateTime', inplace=True)
        except :
            print("no outdoor temp registered")
        
        return results_


    def get_monthly_consumption(self, team_id, HW_key=''):
        if team_id == 'poly':
            query = """SELECT ReportDataDictionary.ReportDataDictionaryIndex, TimeIndex, Value, KeyValue, name, units 
                    FROM ReportData 
                    FULL OUTER JOIN 
                        ReportDataDictionary ON ReportDataDictionary.ReportDataDictionaryIndex=ReportData.ReportDataDictionaryIndex
                    WHERE ReportDataDictionary.ReportDataDictionaryIndex IN 
                        (SELECT ReportDataDictionary.ReportDataDictionaryIndex 
                        FROM ReportDataDictionary 
                        WHERE (name LIKE "%Facility" AND ReportingFrequency LIKE "%Timestep")
                        OR (name LIKE "Heating%" AND ReportingFrequency LIKE "%Timestep")
                        OR (name LIKE "Cooling%" AND ReportingFrequency LIKE "%Timestep")
                        OR (name LIKE "InteriorLights%" AND ReportingFrequency LIKE "%Timestep")
                        OR (name LIKE "ExteriorLights%" AND ReportingFrequency LIKE "%Timestep")
                        OR (name LIKE "%InteriorEquipment%" AND ReportingFrequency LIKE "%Timestep")
                        OR (name LIKE "%Equipment Electricity%" AND ReportingFrequency LIKE "%Timestep"))
                    """
        else:
            # TODO : make sure this works
            query = f"""SELECT ReportDataDictionary.ReportDataDictionaryIndex, TimeIndex, Value, KeyValue, name, units 
                    FROM ReportData 
                    FULL OUTER JOIN 
                        ReportDataDictionary ON ReportDataDictionary.ReportDataDictionaryIndex=ReportData.ReportDataDictionaryIndex
                    WHERE ReportDataDictionary.ReportDataDictionaryIndex IN 
                        (SELECT ReportDataDictionary.ReportDataDictionaryIndex 
                        FROM ReportDataDictionary 
                        WHERE (name LIKE "%Facility" AND ReportingFrequency LIKE "%Hourly")
                        OR (name LIKE "Heating%" AND ReportingFrequency LIKE "%Hourly")
                        OR (name LIKE "Cooling%" AND ReportingFrequency LIKE "%Hourly")
                        OR (name LIKE "InteriorLights%" AND ReportingFrequency LIKE "%Hourly")
                        OR (name LIKE "ExteriorLights%" AND ReportingFrequency LIKE "%Hourly")
                        OR (name LIKE "%InteriorEquipment%" AND ReportingFrequency LIKE "%Hourly")
                        OR (name LIKE "{HW_key}" AND ReportingFrequency LIKE "%Hourly")) 
                    """


        raw_load_profile = self.query_file(query) # all data in single column, need to reformat dataframe

        # check units : has to be Joules
        if (len(raw_load_profile['Units'].unique())!=1) | (raw_load_profile['Units'].unique()[0]!='J'):
            raise Exception("Unit of parameter fetched does not correspond to expected Joules. Verify output file.")
        
        
        load_profile = raw_load_profile.reset_index()[['DateTime', 'KeyValue', 'Name', 'Value']].groupby(['Name', 'DateTime'])['Value'].sum().unstack(level=0)
        # rename columns
        column_names = {'Electricity:Facility':'Total Facility', 'ExteriorLights:Electricity':'ExtLights', 'InteriorLights:Electricity':'IntLights',
                        'InteriorEquipment:Electricity':'PlugLoads', 'Cooling:Electricity':'Cooling', 'Heating:Electricity':'Heating', 'Electric Equipment Electricity Energy':'DHW'}

        load_profile.rename(columns=column_names, inplace=True)

        # add ext and int lighting together
        load_profile['Lighting'] = load_profile['ExtLights'] + load_profile['IntLights']
        load_profile.drop(columns=['ExtLights', 'IntLights'], inplace=True)

        # subtract DHW consumption from plugloads 
        load_profile['PlugLoads'] = load_profile['PlugLoads'] - load_profile['DHW']

        # currenlty column with facility total elec consumption and then all end uses
        # calculate "other" from (tot - end uses)
        load_profile['Other (Fans,...)'] = (load_profile['Total Facility'] - (
            load_profile['Cooling']+load_profile['Heating']+load_profile['Lighting']+load_profile['PlugLoads']+load_profile['DHW'])).clip(lower=0)

        load_profile.drop(columns=['Total Facility'], inplace=True)

        # derrive timestep from simulation length : 
        timestep = self.get_timestep(load_profile)
        
        # convert Joules to kWh
        monthly_consumption = load_profile.resample('ME').sum().iloc[:-1,:] # en Joules
        return monthly_consumption/(3600*1000) # en kWh
