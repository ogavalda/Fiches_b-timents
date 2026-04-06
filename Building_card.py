import json
import openstudio
import matplotlib.pyplot as plt
from geomeppy import IDF
from eppy.function_helpers import getcoords
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import matplotlib.pyplot as plt
from collections import Counter
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    Image
)

from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import pagesizes
from reportlab.platypus import TableStyle
from reportlab.lib import colors
from bs4 import BeautifulSoup
import pandas as pd
import os

# =====================================================
# USER INPUT
# =====================================================

OSM_PATH = r'C:\Users\oriol\PycharmProjects\Buildingcards\HR_AJ_19802010.osm'
RESULT_JSON = r'C:\Users\oriol\PycharmProjects\Buildingcards\HR_AJ_19802010\run\results.json'
eplustbl_file = r'C:\Users\oriol\PycharmProjects\Buildingcards\HR_AJ_19802010\run\eplustbl.htm'  # summary table
# paths :
base_path = r'C:\Users\oriol\PycharmProjects\Buildingcards\HR_AJ_19802010\run'
IDF_name = r'C:\Users\oriol\PycharmProjects\Buildingcards\HR_AJ_19802010\run\in.idf'
# IDD file from E+ installation (needed to import IDF with geomeppy)
iddfile = r"C:\EnergyPlusV25-2-0\Energy+.idd"
fname1 = IDF.setiddname(iddfile)
idf1 = IDF(base_path+"\\"+IDF_name)
# =====================================================
# LOAD OPENSTUDIO MODEL
# =====================================================

def load_model():

    model = openstudio.model.Model.load(OSM_PATH)

    if model.is_initialized():
        return model.get()

    raise Exception("Could not load OSM model")

# =====================================================
# CREATE GEOMETRY IMAGE
# =====================================================

### Functions for creating geometry image

# gets all surfaces to be plotted (windows & doors included)
def get_surfaces(idf):
    """Get the surfaces from the IDF.
    """
    surface_types = ["BUILDINGSURFACE:DETAILED", "FENESTRATIONSURFACE:DETAILED"]
    surfaces = []
    for surface_type in surface_types:
        if surface_type == "BUILDINGSURFACE:DETAILED":
            surfaces.extend([surface for surface in idf.idfobjects[surface_type] if
                             ((surface.Outside_Boundary_Condition.lower() == 'outdoors') | (
                                         surface.Outside_Boundary_Condition.lower() == 'adiabatic') | (
                                          surface.Outside_Boundary_Condition.lower() == 'foundation'))])
        else:
            surfaces.extend(idf.idfobjects[surface_type])

    return surfaces


# gets all zones of model
def get_zones(idf):
    zone_types = ["ZONE"]
    zones = []
    for zone_type in zone_types:
        zones.extend(idf.idfobjects[zone_type])

    return zones


# creates collections based on building surface type
def get_collections(idf, opacity=1):
    """Set up 3D collections for each surface type."""
    surfaces = get_surfaces(idf)
    zones = get_zones(idf)

    #
    limits = get_limits(idf=idf)
    y = limits["y"][1]

    # HEX codes for surface coloring
    wall_color = "#e6c973"
    window_color = "#abdee3"
    roof_color = "#5d2e2e"
    door_color = "#ac9656"

    # set up the collections
    walls = get_collection("wall", surfaces, opacity, zones, facecolor=wall_color)
    floors = get_collection("floor", surfaces, opacity, zones, facecolor="dimgray")  # not plotted
    roofs = get_collection("roof", surfaces, opacity, zones, facecolor=roof_color)
    windows = get_collection("window", surfaces, opacity, zones, facecolor=window_color, y_lim=y)
    windows_behind = get_collection("window", surfaces, opacity, zones, facecolor="cornflowerblue")  # not plotted
    doors = get_collection("door", surfaces, opacity, zones, facecolor=door_color, y_lim=y)
    doors_behind = get_collection("door", surfaces, opacity, zones, facecolor="saddlebrown")  # not plotted
    return walls, roofs, windows, doors


#
def get_collection(surface_type, surfaces, opacity, zones, facecolor, edgecolors="black", y_lim=None):
    """Make collections from a list of EnergyPlus surfaces."""
    origin = {}

    # if coordinate system is relative,
    # get the zone origin coordinates for each surface
    if len(zones) >= 1:
        coords = []
        for s in surfaces:
            if (s.Surface_Type.lower() != "window") & (s.Surface_Type.lower() != "door"):
                zname = s.Zone_Name
                for zone in zones:
                    if zone.Name == zname:
                        origin[s.Name] = (zone.X_Origin, zone.Y_Origin, zone.Z_Origin)
        for s in surfaces:
            if s.Surface_Type.lower() in ["window", "door"]:
                parent = s.Building_Surface_Name
                if parent in origin:
                    origin[s.Name] = origin[parent]
                else:
                    continue
            if s.Surface_Type.lower() == surface_type.lower():
                adj_coords = []
                if (s.Surface_Type.lower() == "window") | (s.Surface_Type.lower() == "door"):
                    origin[s.Name]
                if y_lim is not None:  # test whether windows/doors are on back walls (x=0 or y=ymax for all coordinates)
                    is_on_back = True
                    is_on_side = True
                    for crd_set in getcoords(s):
                        adj_coords.append(tuple([crd + org for crd, org in zip(crd_set, origin[s.Name])]))
                        if adj_coords[0][1] < y_lim:
                            is_on_back = False
                        if adj_coords[0][0] > 0:
                            is_on_side = False
                    if is_on_side | is_on_back:
                        adj_coords = []
                else:
                    for crd_set in getcoords(s):
                        adj_coords.append(tuple([crd + org for crd, org in zip(crd_set, origin[s.Name])]))
                coords.append(adj_coords)
    else:
        coords = [
            getcoords(s) for s in surfaces if s.Surface_Type.lower() == surface_type.lower()
        ]
    trimmed_coords = [c for c in coords if c]  # dump any empty surfaces
    zorder_nb = {'wall': 2, 'floor': 2, 'roof': 2, 'window': 1, 'door': 2}
    collection = Poly3DCollection(
        trimmed_coords, alpha=opacity, facecolor=facecolor, edgecolors=edgecolors, zorder=zorder_nb[surface_type]
    )
    return collection


# gets min & max coordinates to determine plot size
def get_limits(idf=None, polygons=None, collections=None):
    """Get limits for the x, y and z axes so the plot is fitted to the axes."""
    if polygons:
        x = [pt[0] for color in polygons for p in polygons[color] for pt in p]
        y = [pt[1] for color in polygons for p in polygons[color] for pt in p]
        z = [pt[2] for color in polygons for p in polygons[color] for pt in p]

    elif idf:
        surfaces = get_surfaces(idf)

        x = [pt[0] for s in surfaces for pt in getcoords(s)]
        y = [pt[1] for s in surfaces for pt in getcoords(s)]
        z = [pt[2] for s in surfaces for pt in getcoords(s)]

    elif collections:

        x = []
        y = []
        z = []

        for c in collections:
            xdata, ydata, zdata, _ = c._vec
            for x_i, y_i, z_i in zip(xdata, ydata, zdata):
                x.append(x_i)
                y.append(y_i)
                z.append(z_i)

    max_delta = max((max(x) - min(x)), (max(y) - min(y)), (max(z) - min(z)))

    return {
        "x": (min(x), min(x) + max_delta),
        "y": (min(y), min(y) + max_delta),
        "z": (min(z), min(y) + max_delta),
    }


def view_geometry(idf, savefig=True, filepath=''):
    # create the figure and add the surfaces
    ax = plt.axes(projection="3d")
    collections = get_collections(idf, opacity=1)
    i = 0
    for c in collections:
        if i == 0:
            c.set_sort_zpos(i)
        ax.add_collection3d(c)
        i += 1

    # calculate and set the axis limits
    limits = get_limits(collections=collections)
    ax.set_xlim(limits["x"])
    ax.set_ylim(limits["y"])
    ax.set_zlim(limits["z"]);

    ax.set_aspect('equal')
    ax.set_axis_off()
    if savefig == True:
        plt.savefig(filepath)
    return


    return
# =====================================================
# BUILDING DESCRIPTION
# =====================================================

def building_description(model):

    building = model.getBuilding()

    floor_area = building.floorArea()

    stories = len(model.getBuildingStorys())

    spaces = model.getSpaces()

    space_types = []

    for s in spaces:

        if s.spaceType().is_initialized():
            space_types.append(s.spaceType().get().nameString())

    space_count = Counter(space_types)

    climate_zone = "Not defined"

    czs = model.getClimateZones()

    if czs.numClimateZones() > 0:
        cz = czs.getClimateZone(0)

        climate_zone = cz.value()

    return floor_area, stories, space_count, climate_zone


# =====================================================
# WINDOW TO WALL RATIO
# =====================================================

def compute_wwr(eplustbl_file):

    # -------------------------
    # 1. Load HTML
    # -------------------------
    if not os.path.exists(eplustbl_file):
        raise FileNotFoundError(f"{eplustbl_file} not found")

    with open(eplustbl_file, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f, "lxml")

    # -------------------------
    # 2. Find "Window-Wall Ratio" table
    # -------------------------
    wwr_tag = soup.find("b", string="Window-Wall Ratio")
    if not wwr_tag:
        raise ValueError("Window-Wall Ratio section not found in HTML")

    table = wwr_tag.find_next("table")
    if not table:
        raise ValueError("No table found after 'Window-Wall Ratio'")

    # -------------------------
    # 3. Parse table
    # -------------------------
    rows = []
    for tr in table.find_all("tr"):
        cells = [td.get_text(strip=True) for td in tr.find_all("td")]
        if cells:
            rows.append(cells)
    # Ensure flat Python lists
    # Find the row containing the WWR
    row_tag = soup.find("td", string=lambda x: x and "Above Ground Window-Wall Ratio" in x).parent

    # Extract text from each <td>
    cells2 = [td.get_text(strip=True) for td in row_tag.find_all("td")]
    # Define main façades
    facades = ["North", "South", "East", "West"]

    # Convert values to floats
    wwr_values = [float(cells2[i]) / 100 for i in range(1, 5)]

    # Create DataFrame
    data = list(zip(facades, wwr_values))

    df_wwr = pd.DataFrame(data, columns=["Facade", "WWR"])

    return df_wwr


# =====================================================
# LOAD RESULTS JSON
# =====================================================

def load_results():

    with open(RESULT_JSON) as f:
        data = json.load(f)

    return data


# =====================================================
# ENERGY PROFILE
# =====================================================

def extract_energy(eplustbl_file):
    from bs4 import BeautifulSoup
    import os

    if not os.path.exists(eplustbl_file):
        raise FileNotFoundError(f"{eplustbl_file} not found")

    with open(eplustbl_file, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f, "lxml")

    # Look for all tables
    tables = soup.find_all("table")

    total_energy = {}
    for table in tables:
        # Loop over all rows
        for tr in table.find_all("tr"):
            tds = [td.get_text(strip=True) for td in tr.find_all("td")]
            if not tds:
                continue
            if "Total Site Energy" in tds[0]:
                # Columns: [Label, Total Energy [GJ], Energy per Total Area [MJ/m2], Energy per Conditioned Area [MJ/m2]]
                total_energy["Total Energy [kWh]"] = float(tds[1].replace(",", ""))* 277.778
                total_energy["EUI Total Area [kWh/m2]"] = float(tds[2].replace(",", ""))*0.277778
                total_energy["EUI Conditioned Area [kWh/m2]"] = float(tds[3].replace(",", ""))*0.277778
                return total_energy

    raise ValueError("Total Site Energy table not found")

# =====================================================
# MONTHLY HEATING
# =====================================================

def monthly_heating(results):
    import json
    print(json.dumps(results, indent=2))
    heating = results["energy_consumption"]["heating"]["monthly"]

    months = list(range(1,13))

    return months, heating


# =====================================================
# PLOT MONTHLY GRAPH
# =====================================================

def create_monthly_plot():
    import pandas as pd
    from bs4 import BeautifulSoup
    import os
    import matplotlib.pyplot as plt
    # -------------------------
    # File paths
    # -------------------------

    epluscsv_file = r'C:\Users\oriol\PycharmProjects\Buildingcards\HR_AJ_19802010\run\epluszsz.csv'  # detailed zone CSV
    output_csv = r'C:\Users\oriol\PycharmProjects\Buildingcards\monthly_energy_summary.csv'

    # -------------------------
    # 1. Load the HTML
    # -------------------------
    with open(eplustbl_file, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f, "lxml")

    # -------------------------
    # 2. Find all "Custom Monthly Report" tables
    # -------------------------
    custom_reports = soup.find_all("b", string="Custom Monthly Report")
    all_tables = []

    for idx, report in enumerate(custom_reports):
        table = report.find_next("table")
        if not table:
            continue

        # Extract headers
        first_tr = table.find("tr")
        headers = [td.get_text(strip=True) for td in first_tr.find_all("td")]

        if headers[0] == "":
            headers[0] = "Month"

        rows = []
        # Iterate all tr elements inside the table, including multiple tbody sections
        for tr in table.find_all("tr")[1:]:
            cells = [td.get_text(strip=True) for td in tr.find_all("td")]
            # Skip completely empty rows
            if not any(cells):
                continue
            # Skip rows that don't have a month name in the first cell
            month_cell = cells[0].strip()
            if month_cell.lower() in ["total", "", "report", "timestamp"]:
                continue
            rows.append(cells)

        if rows:
            df = pd.DataFrame(rows, columns=headers)
            df["Report_ID"] = idx + 1
            all_tables.append(df)

    # -------------------------
    # 3. Combine all tables
    # -------------------------
    if not all_tables:
        raise ValueError("No Custom Monthly Report tables found")

    monthly_data = pd.concat(all_tables, ignore_index=True)

    # -------------------------
    # 4. Convert numeric columns safely and J → kWh
    # -------------------------
    J_to_kWh = 1 / 3_600_000  # 1 kWh = 3.6e6 J

    for col in monthly_data.columns:
        if col in ["Report_ID", "Month"]:
            continue
        monthly_data[col] = pd.to_numeric(
            monthly_data[col].str.replace(",", "").str.strip(), errors='coerce'
        ) * J_to_kWh

    monthly_data = monthly_data.fillna(0)

    # -------------------------
    # 5b. Aggregate duplicate months and clean invalid rows
    # -------------------------

    # First, drop any rows where Month is empty or not a valid month name
    valid_months = ["January", "February", "March", "April", "May", "June",
                    "July", "August", "September", "October", "November", "December"]

    monthly_data = monthly_data[monthly_data["Month"].isin(valid_months)].copy()

    # Aggregate numeric columns by Month
    numeric_cols = [col for col in monthly_data.columns if col not in ["Month", "Report_ID"]]
    monthly_data_agg = monthly_data.groupby("Month")[numeric_cols].sum().reset_index()

    # Ensure Month is categorical and ordered
    monthly_data_agg["Month"] = pd.Categorical(monthly_data_agg["Month"], categories=valid_months, ordered=True)
    monthly_data_agg = monthly_data_agg.sort_values("Month")

    # Remove columns that are zero in all months
    non_zero_cols = [col for col in numeric_cols if monthly_data_agg[col].sum() > 0]
    monthly_data_agg = monthly_data_agg[["Month"] + non_zero_cols]

    # Reset index
    monthly_data_agg = monthly_data_agg.reset_index(drop=True)

    # -------------------------
    # 6b. Convert from J to kWh (if not done yet)
    # -------------------------
    J_to_kWh = 1 / 1  # 1 kWh = 3.6e6 J
    for col in non_zero_cols:
        monthly_data_agg[col] = monthly_data_agg[col] * J_to_kWh

    # -------------------------
    # 7b. Plot stacked bar chart
    # -------------------------
    import matplotlib.pyplot as plt

    ax = monthly_data_agg.set_index("Month").plot(
        kind="bar",
        stacked=True,
        figsize=(12, 6),
        colormap="tab20"
    )
    ax.set_ylabel("Energy [kWh]")
    ax.set_title("Monthly Energy Consumption by Type")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig("monthly_heating.png")

    plt.close()
# =====================================================
# DIVISION BY USAGE
# =====================================================

from bs4 import BeautifulSoup


def extract_end_uses(html_path):
    """
    Extracts non-zero electricity end uses from EnergyPlus HTML report.
    Returns a dict like {'Heating': 1409.76, 'Cooling': 487.60, ...}
    """
    with open(html_path, "r", encoding="utf-8", errors="ignore") as f:
        soup = BeautifulSoup(f, "html.parser")

    # Find the "End Uses" table by locating its header
    for table in soup.find_all("table"):
        caption = table.find("caption") or table.find("b") or table.find("td")
        # Search for the table that has "End Uses" as title nearby
        prev = table.find_previous(string=lambda t: t and "End Uses" in t)
        if not prev:
            continue

        headers = [th.get_text(strip=True) for th in table.find_all("tr")[0].find_all("td")]

        # Find the index of the Electricity column
        elec_index = next(
            (i for i, h in enumerate(headers) if "Electricity" in h), None
        )
        if elec_index is None:
            continue

        result = {}
        for row in table.find_all("tr")[1:]:  # skip header row
            cells = row.find_all("td")
            if len(cells) <= elec_index:
                continue

            end_use = cells[0].get_text(strip=True)

            # Skip total row and empty rows
            if not end_use or "Total" in end_use:
                continue

            try:
                value = float(cells[elec_index].get_text(strip=True))*277.78
            except ValueError:
                continue

            if value != 0.0:
                result[end_use] = value

        if result:
            return result

    raise ValueError("Could not find 'End Uses' table in the EnergyPlus HTML report.")
# =====================================================
# GENERATE PDF
# =====================================================


# =====================================================
# MAIN
# =====================================================

def main():

    # print("Loading model")
    #
    model = load_model()
    view_geometry(idf1, savefig=True, filepath='test2.png')
    #
    # print("Reading results")
    #
    # results = load_results()
    #
    # print("Extracting geometry")
    #
    floor_area,stories,space_count,climate_zone = building_description(model)
    #
    # print("Computing WWR")
    #
    wwr = compute_wwr(eplustbl_file)
    #
    # print("Energy profile")
    #
    energy = extract_energy(eplustbl_file)
    #
    # print("Monthly heating")
    #
    create_monthly_plot()
    #
    # print("Generating PDF")
    #
    # generate_pdf(floor_area,stories,space_count,
    #              climate_zone,wwr,energy)
    #
    # print("Building card created")
    from jinja2 import Environment, FileSystemLoader

    env = Environment(loader=FileSystemLoader("."))

    template = env.get_template("report.html")

    end_uses = extract_end_uses(eplustbl_file)

    html = template.render(
        floor_area=floor_area,
        stories=stories,
        climate_zone=climate_zone,
        energy=energy,
        end_uses=end_uses,
        wwr=wwr.values.tolist(),
        imagemodel="test2.png"
    )

    with open("report_filled.html", "w",encoding="utf-8") as f:
        f.write(html)

if __name__ == "__main__":

    main()
