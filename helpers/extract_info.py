from bs4 import BeautifulSoup
import os
import json
import re
from core_2 import size, get_vintage_column
from config import team_id

def extract_construction_summary(html_input: str, osm) -> dict:

    # -------------------------
    # FINAL AGGREGATION
    # -------------------------
    def avg(values):
        return sum(values) / len(values) if values else None


    # -------------------------
    # Load HTML (file or string)
    # -------------------------
    if os.path.exists(html_input):
        with open(html_input, "r", encoding="utf-8") as f:
            html = f.read()
    else:
        html = html_input

    soup = BeautifulSoup(html, "html.parser")

    # -------------------------
    # STORAGE
    # -------------------------
    data = {
        "Walls Ext": set(),
        "Roof": set(),
        "Slabs": set(),
        "Walls Int": set(),
        "Glazing": set(),
        "SHGC": set(),
    }

    # -------------------------
    # Floor area 
    # -------------------------
    for b in soup.find_all("b"):
        if "Building Area" in b.get_text():

            table = b.find_next("table")
            rows = table.find_all("tr")

            headers = [td.get_text(strip=True) for td in rows[0].find_all("td")]

            area_index = headers.index("Area [m2]")

            for row in rows[1:]:
                cols = [td.get_text(strip=True) for td in row.find_all("td")]
                row_name = cols[0].upper()
                area = float(cols[area_index])

                
                if "NET CONDITIONED BUILDING AREA" == row_name:
                    floor_area = area



    # -------------------------
    # 1. OPAQUE EXTERIOR
    # -------------------------
    for b in soup.find_all("b"):
        if "Opaque Exterior" in b.get_text():

            table = b.find_next("table")
            rows = table.find_all("tr")

            headers = [td.get_text(strip=True) for td in rows[0].find_all("td")]

            u_index = headers.index("U-Factor with Film [W/m2-K]")
            tilt_index = headers.index("Tilt [deg]")

            for row in rows[1:]:
                cols = [td.get_text(strip=True) for td in row.find_all("td")]

                if len(cols) <= max(u_index, tilt_index):
                    continue

                try:
                    u = float(cols[u_index])
                    tilt = float(cols[tilt_index])

                    if tilt == 90:
                        data["Walls Ext"].add(u)

                    elif tilt < 90:
                        data["Roof"].add(u)

                    elif tilt == 180:
                        data["Slabs"].add(u)

                except:
                    continue

    # -------------------------
    # 2. OPAQUE INTERIOR
    # -------------------------
    for b in soup.find_all("b"):
        if "Opaque Interior" in b.get_text():

            table = b.find_next("table")
            rows = table.find_all("tr")

            headers = [td.get_text(strip=True) for td in rows[0].find_all("td")]

            u_index = headers.index("U-Factor with Film [W/m2-K]")
            construction_index = headers.index("Construction")

            roof_done=False

            for row in rows[1:]:
                cols = [td.get_text(strip=True) for td in row.find_all("td")]

                if len(cols) <= max(u_index, construction_index):
                    continue

                try:
                    construction = cols[construction_index].upper()
                    u = float(cols[u_index])

                    if "WALL" in construction:
                        data["Walls Int"].add(u)

                    if "TBD" in construction: # only way to identify internal roof insulation is that it's the only surface undergoing Thermal bridging corrections
                        if not roof_done:
                            Roof_u = avg(data["Roof"])
                            data["Roof"].remove(Roof_u) # remove previous values from set
                            data["Roof"].add(1/(1/Roof_u+1/u))
                            roof_done=True

                except:
                    continue

    # -------------------------
    # 3. WINDOWS (FENESTRATION)
    # -------------------------
    for b in soup.find_all("b"):
        if "Fenestration" in b.get_text():

            table = b.find_next("table")
            rows = table.find_all("tr")

            headers = [td.get_text(strip=True) for td in rows[0].find_all("td")]

            u_index = None
            shgc_index = None

            for i, h in enumerate(headers):
                if "Glass U-Factor" in h:
                    u_index = i
                elif "Glass SHGC" in h:
                    shgc_index = i

            if u_index is None or shgc_index is None:
                continue

            for row in rows[1:]:
                cols = [td.get_text(strip=True) for td in row.find_all("td")]

                if len(cols) <= max(u_index, shgc_index):
                    continue

                try:
                    data["Glazing"].add(float(cols[u_index]))
                    data["SHGC"].add(float(cols[shgc_index]))
                except:
                    continue

            break  # only one fenestration table needed




    return {
        "Exterior walls [W/m²/K]": avg(data["Walls Ext"]),
        "Interior walls [W/m²/K]": 0, ## no int walls
        "Roof [W/m²/K]": avg(data["Roof"]), 
        "Slabs [W/m²/K]": avg(data["Slabs"]), 
        "Glazing [W/m²/K]": avg(data["Glazing"]),
        "SHGC": avg(data["SHGC"]),
        "Infiltration (ELA @4Pa) [cm²]": get_infiltration(osm), 
    }, floor_area



def get_infiltration(osm):
    ELAs = [ELA for ELA in osm.getSpaceInfiltrationEffectiveLeakageAreas()]
    ELA = ELAs[0].effectiveAirLeakageArea()

    return ELA


def get_building_characteristics(folder_name):
    if team_id == 'poly' : 
        parts = re.split(r"[-_]", folder_name)
        # french dict - TODO : move to general translation dict
        category_dict_fr = {'Detached':'Détaché', "Row":"Rangé", "SD":'Semi-Détaché', 'Duplex':'Duplex', 'Triplex':'Triplex'}
        floors_dict_fr = {'2Floor':'2 étages', '1Floor':'1 étage'}


        # english dict
        category_dict = {"SD":'Semi-Detached'}
        floors_dict = {'2Floor':'2 Floors', '1Floor':'1 Floor'}
        building_shape = ""


        if "Ecole" in parts:
            # do casting for schools
            sector = "Commercial-Institutional"
            building_type = "Education"
            building_subtype = "Primary and Secondary school" #TODO
            building_size = "Small"  #TODO
            vintage = ""
        elif ('Duplex' in parts) or ('Triplex' in parts):
            sector = "Residential"
            building_type = "Multi-Unit"
            building_subtype =  parts[0]

            if 'attached' in parts:
                building_size = 'Attached'
            elif 'detached' in parts:
                building_size = 'Detached'

            if 'empty' in parts:
                building_size = building_size + ", unconditioned basement"
            elif 'main' in parts:
                building_size = building_size + ", conditioned basement (with main floor)"
            else:
                building_size = building_size + ", conditioned basement (separate unit)"

            if 'new' in parts:
                vintage = "After 2012"
            elif ('Pre1945' in parts):
                vintage = 'Before 1945'
            else:
                vintage = parts[1]+'-'+parts[2]
        else:
            sector = "Residential"
            building_type = "Single-Family"
            
            category = category_dict.get(parts[0], parts[0]) 
            building_size = floors_dict.get(parts[1])

            if 'Row' in category:
                if 'middle' in parts:
                    building_subtype = category 
                    building_size = 'middle of row'
                elif 'end' in parts:
                    building_subtype = category 
                    building_size = 'end of row'
                else:
                    raise Exception('building type not recognized')
            else:
                building_subtype = category

            if 'new' in parts:
                vintage = "After 2012"
            elif ('Pre1945' in parts):
                vintage = 'Before 1945'
            else:
                vintage = parts[-2]+'-'+parts[-1]


    else:
        # TODO : expand
        parts = folder_name.split("_")
        sector = 'Residential'
        building_type = "Multi-Unit"
        building_subtype = "Apartment"
        building_size = size(parts[1])
        #building_name = parts[2] : TODO : building name will be the abbreviations of all other characteristics collected here, the function below will cast the full names to their abbreviations
        vintage = get_vintage_column(parts[3])
        building_shape = parts[2]

    
    building_name = abbreviate_name(sector, building_type, building_subtype, building_size, vintage,building_shape)
    print(building_name)

    return {"building_shape":building_shape,"building_name":building_name, "sector":sector, "building_type":building_type, "building_subtype":building_subtype, "vintage":vintage, "size":building_size}


def get_abbreviation_dicts():
    # TODO : add abbreviations for MURBS, schools and offices
    sectors = {"Commercial-Institutional":'CI', "Residential":'R'}
    building_types = {"Single-Family":'SF', "Multi-Unit":'MU', "Education":'EDU'}
    building_subtypes = {"Duplex":'Dup', "Triplex":'Trip',"Attached":'Att', "Detached":'Det', "Semi-Detached":'SD', "Row":'Row',"Apartment":"Apt"}
    building_sizes = {"Attached":'Att', "Detached":'Det', "1 Floor":'1fl', "2 Floors":'2fl',"LR":"LR","MR":"MR","HR":"HR", "middle of row":'mid', "end of row":'end', 
                        "Attached, unconditioned basement":'Att-bsmt-empty', "Detached, unconditioned basement":'Det-bsmt-empty', 
                        "Attached, conditioned basement (with main floor)":'Att-bsmt-main', "Detached, conditioned basement (with main floor)":'Det-bsmt-main', 
                        "Attached, conditioned basement (separate unit)":'Att-bsmt-unit', "Detached, conditioned basement (separate unit)":'Det-bsmt-unit'}
    vintages = {"After 2012":'post2012', "Before 1945":'pre1945',"A_Pre1945":"pre1945","B_19461983":"1946-1983","C_19842010":"1984-2010","D_Post2011":"post2011"}
    building_shapes = {"SG":"L-shaped","SJ":"rectangular","HU":"Square","MK":"rectangular"}

    return sectors, building_types, building_subtypes, building_sizes, vintages,building_shapes
def get_french_characteristic(characteristic):
    sectors = {"Commercial-Institutional":'Commerical-Institutionnel', "Residential":'Résidentiel'}
    building_types = {"Single-Family":'Unifamilial', "Multi-Unit":'Multilogement', "Education":'Éducation'}
    building_subtypes = {"Attached":'Attaché', "Detached":'Détaché', "Semi-Detached":'Semi-Détaché', "Row":'Rangé',"Apartment":"Appartement"}
    building_sizes = {"Attached":'Attaché', "Detached":'Détaché', "1 Floor":'1 étage', "2 Floors":'2 étages',"LR":"LR","MR":"MR","HR":"HR",  "middle of row":'unité milieu', "end of row":'unité coin', 
                        "Attached, unconditioned basement":'Attaché, sous-sol non-chauffé', "Detached, unconditioned basement":'Détaché, sous-sol non-chauffé',
                        "Attached, conditioned basement (with main floor)":'Attaché, sous-sol chauffé (avec première étage)', "Detached, conditioned basement (with main floor)":'Détaché, sous-sol chauffé (avec première étage)', 
                        "Attached, conditioned basement (separate unit)":'Attaché, sous-sol chauffé (unité propre)', "Detached, conditioned basement (separate unit)":'Détaché, sous-sol chuaffé (unité propre)'}
    vintages = {"After 2012":'Après 2012', "Before 1945":'Avant 1945',"A_Pre1945":"Avant 1945","B_19461983":"1946-1983","C_19842010":"1984-2010","D_Post2011":"Après 2011"}
    
    if characteristic in sectors.keys():
        return sectors[characteristic]
    elif characteristic in building_types.keys():
        return building_types[characteristic]
    elif characteristic in building_subtypes.keys():
        return building_subtypes[characteristic]
    elif characteristic in building_sizes.keys():
        return building_sizes[characteristic]
    elif characteristic in vintages.keys():
        return vintages[characteristic]
    else:
        print('characteristic not yet in dict, see "get_french_characteristics" function in extract_info')
        return characteristic
    return 


def abbreviate_name(sector, building_type, building_subtype, building_size, vintage,building_shape):
    sectors, building_types, building_subtypes, building_sizes, vintages,building_shapes = get_abbreviation_dicts()

    if building_shapes.get(building_shape,"") != "":
        abbr_name = (sectors.get(sector, sector) + "_" +
                        building_types.get(building_type, building_type) + "_" +
                        building_subtypes.get(building_subtype, building_subtype) + "_" +
                        building_sizes.get(building_size, building_size) + "_" +
                        building_shapes.get(building_shape,"")
                        vintages.get(vintage, vintage) + "_"+
        )
        return abbr_name
    else:
        abbr_name = (sectors.get(sector, sector) + "_" +
                     building_types.get(building_type, building_type) + "_" +
                     building_subtypes.get(building_subtype, building_subtype) + "_" +
                     building_sizes.get(building_size, building_size) + "_" +
                     vintages.get(vintage, vintage) )
        return abbr_name

def get_folder_structure(sector, building_type, building_subtype, building_size, building_name,building_shape):
    sectors, building_types, building_subtypes, building_sizes, vintages,building_shapes = get_abbreviation_dicts()

    folders = [sectors.get(sector, sector),
                    building_types.get(building_type, building_type),
                    building_subtypes.get(building_subtype, building_subtype),
                    building_sizes.get(building_size, building_size), 
                    building_name,
                    building_shapes.get(building_shape,"")
    ]
    if (building_type=='Multi-Unit') and (building_subtype=='Apartment'):
        folders = [sectors.get(sector, sector),
                        building_types.get(building_type, building_type),
                        building_subtypes.get(building_subtype, building_subtype),
                        building_sizes.get(building_size, building_size), 
                        building_name
        ]
    
    else:
        folders = [sectors.get(sector, sector),
                        building_types.get(building_type, building_type),
                        building_subtypes.get(building_subtype, building_subtype),
                        building_name
        ]

    return folders

# a function that translates the name into french e.g. rectangular --> rectangulaire
def french_name(building_name):
    building_name_parts = building_name.split("_") # always hunt for the item number 5 ( the shape )
    building_shapes_fr = {
        "rectangular":"rectangulaire",
        "L-shaped":"en forme de l",
        "Square": "carré"
    }
    if len(building_name_parts)>=6:
        french_name = (
            building_name_parts[0] + "_"+
            building_name_parts[1] + "_" +
            building_name_parts[2] + "_" +
            building_name_parts[3] + "_" +
            building_name_parts[4] + "_" +
            building_shapes_fr[building_name_parts[5]]
        )

        return french_name
    else:
        return building_name



if __name__ == "__main__":

    name = "R_MU_Apt_Hight Rise_1946-1983_L-shaped"

    print(french_name((name)))
