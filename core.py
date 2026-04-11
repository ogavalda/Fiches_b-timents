import json
import os
import openstudio
import matplotlib.pyplot as plt
from geomeppy import IDF
from eppy.function_helpers import getcoords
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from collections import Counter
from bs4 import BeautifulSoup
import pandas as pd


# =========================
# LOAD MODEL
# =========================
def load_model(osm_path):
    model = openstudio.model.Model.load(osm_path)
    if model.is_initialized():
        return model.get()
    raise Exception(f"Could not load OSM model: {osm_path}")


# =========================
# GEOMETRY (IDENTICAL)
# =========================
def get_surfaces(idf):
    surface_types = ["BUILDINGSURFACE:DETAILED", "FENESTRATIONSURFACE:DETAILED"]
    surfaces = []
    for surface_type in surface_types:
        if surface_type == "BUILDINGSURFACE:DETAILED":
            surfaces.extend([
                surface for surface in idf.idfobjects[surface_type]
                if surface.Outside_Boundary_Condition.lower() in ["outdoors", "adiabatic", "foundation"]
            ])
        else:
            surfaces.extend(idf.idfobjects[surface_type])
    return surfaces


def get_zones(idf):
    zones = []
    zones.extend(idf.idfobjects["ZONE"])
    return zones


def get_collection(surface_type, surfaces, opacity, zones, facecolor, edgecolors="black", y_lim=None):
    origin = {}

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

                if y_lim is not None:
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

    trimmed_coords = [c for c in coords if c]

    zorder_nb = {'wall': 2, 'floor': 2, 'roof': 2, 'window': 1, 'door': 2}

    return Poly3DCollection(
        trimmed_coords, alpha=opacity, facecolor=facecolor,
        edgecolors=edgecolors, zorder=zorder_nb[surface_type]
    )


def get_collections(idf, opacity=1):
    surfaces = get_surfaces(idf)
    zones = get_zones(idf)

    limits = get_limits(idf=idf)
    y = limits["y"][1]

    wall_color = "#e6c973"
    window_color = "#abdee3"
    roof_color = "#5d2e2e"
    door_color = "#ac9656"

    walls = get_collection("wall", surfaces, opacity, zones, facecolor=wall_color)
    roofs = get_collection("roof", surfaces, opacity, zones, facecolor=roof_color)
    windows = get_collection("window", surfaces, opacity, zones, facecolor=window_color, y_lim=y)
    doors = get_collection("door", surfaces, opacity, zones, facecolor=door_color, y_lim=y)

    return walls, roofs, windows, doors


def get_limits(idf=None, collections=None):
    if idf:
        surfaces = get_surfaces(idf)
        x = [pt[0] for s in surfaces for pt in getcoords(s)]
        y = [pt[1] for s in surfaces for pt in getcoords(s)]
        z = [pt[2] for s in surfaces for pt in getcoords(s)]
    else:
        x, y, z = [], [], []
        for c in collections:
            xdata, ydata, zdata, _ = c._vec
            for x_i, y_i, z_i in zip(xdata, ydata, zdata):
                x.append(x_i)
                y.append(y_i)
                z.append(z_i)

    max_delta = max((max(x)-min(x)), (max(y)-min(y)), (max(z)-min(z)))

    return {
        "x": (min(x), min(x)+max_delta),
        "y": (min(y), min(y)+max_delta),
        "z": (min(z), min(y)+max_delta),
    }


def view_geometry(idf, filepath):
    ax = plt.axes(projection="3d")
    collections = get_collections(idf, opacity=1)

    i = 0
    for c in collections:
        if i == 0:
            c.set_sort_zpos(i)
        ax.add_collection3d(c)
        i += 1

    limits = get_limits(collections=collections)
    ax.set_xlim(limits["x"])
    ax.set_ylim(limits["y"])
    ax.set_zlim(limits["z"])

    ax.set_aspect('equal')
    ax.set_axis_off()

    plt.savefig(filepath)
    plt.close()


# =========================
# DATA (IDENTICAL)
# =========================
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
        climate_zone = czs.getClimateZone(0).value()

    return floor_area, stories, space_count, climate_zone


def compute_wwr(eplustbl_file):
    with open(eplustbl_file, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f, "lxml")

    row_tag = soup.find("td", string=lambda x: x and "Above Ground Window-Wall Ratio" in x).parent
    cells = [td.get_text(strip=True) for td in row_tag.find_all("td")]

    facades = ["North", "South", "East", "West"]
    values = [float(cells[i]) / 100 for i in range(1, 5)]

    return pd.DataFrame(list(zip(facades, values)), columns=["Facade", "WWR"])


def extract_energy(eplustbl_file):
    with open(eplustbl_file, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f, "lxml")

    for table in soup.find_all("table"):
        for tr in table.find_all("tr"):
            tds = [td.get_text(strip=True) for td in tr.find_all("td")]
            if tds and "Total Site Energy" in tds[0]:
                return {
                    "Total Energy [kWh]": float(tds[1].replace(",", "")) * 277.778,
                    "EUI Total Area [kWh/m2]": float(tds[2].replace(",", "")) * 0.277778,
                    "EUI Conditioned Area [kWh/m2]" : float(tds[3].replace(",", "")) * 0.277778
                }

    raise ValueError("Energy table not found")


def extract_end_uses(html_path):
    with open(html_path, "r", encoding="utf-8", errors="ignore") as f:
        soup = BeautifulSoup(f, "html.parser")

    for table in soup.find_all("table"):
        prev = table.find_previous(string=lambda t: t and "End Uses" in t)
        if not prev:
            continue

        headers = [th.get_text(strip=True) for th in table.find_all("tr")[0].find_all("td")]
        elec_index = next((i for i, h in enumerate(headers) if "Electricity" in h), None)

        result = {}
        for row in table.find_all("tr")[1:]:
            cells = row.find_all("td")
            if len(cells) <= elec_index:
                continue

            name = cells[0].get_text(strip=True)

            try:
                val = float(cells[elec_index].get_text(strip=True)) * 277.78
            except:
                continue

            if val != 0:
                result[name] = val

        if result:
            return result

    raise ValueError("End uses not found")


# def create_monthly_plot(eplustbl_file, output_path):
#     with open(eplustbl_file, "r", encoding="utf-8") as f:
#         soup = BeautifulSoup(f, "lxml")
#
#     custom_reports = soup.find_all("b", string="Custom Monthly Report")
#     all_tables = []
#
#     for idx, report in enumerate(custom_reports):
#         table = report.find_next("table")
#         if not table:
#             continue
#
#         headers = [td.get_text(strip=True) for td in table.find("tr").find_all("td")]
#         if headers[0] == "":
#             headers[0] = "Month"
#
#         rows = []
#         for tr in table.find_all("tr")[1:]:
#             cells = [td.get_text(strip=True) for td in tr.find_all("td")]
#             if not any(cells):
#                 continue
#             if cells[0].lower() in ["total", "", "report", "timestamp"]:
#                 continue
#             rows.append(cells)
#
#         if rows:
#             df = pd.DataFrame(rows, columns=headers)
#             df["Report_ID"] = idx + 1
#             all_tables.append(df)
#
#     monthly_data = pd.concat(all_tables, ignore_index=True)
#
#     J_to_kWh = 1 / 3_600_000
#     for col in monthly_data.columns:
#         if col in ["Month", "Report_ID"]:
#             continue
#         monthly_data[col] = pd.to_numeric(
#             monthly_data[col].str.replace(",", ""), errors='coerce'
#         ) * J_to_kWh
#
#     monthly_data = monthly_data.fillna(0)
#
#     valid_months = ["January","February","March","April","May","June",
#                     "July","August","September","October","November","December"]
#
#     monthly_data = monthly_data[monthly_data["Month"].isin(valid_months)]
#
#     numeric_cols = [c for c in monthly_data.columns if c not in ["Month","Report_ID"]]
#     monthly_data = monthly_data.groupby("Month")[numeric_cols].sum().reset_index()
#
#     monthly_data["Month"] = pd.Categorical(monthly_data["Month"], categories=valid_months, ordered=True)
#     monthly_data = monthly_data.sort_values("Month")
#
#     ax = monthly_data.set_index("Month").plot(kind="bar", stacked=True, figsize=(12,6))
#     plt.savefig(output_path)
#     plt.close()


def create_monthly_plot(eplustbl_file, output_path,lang):

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
    if lang=="eng":
        ax.set_ylabel("Energy [kWh]")
        ax.set_title("Monthly Energy Consumption by Type")
    else:
        ax.set_ylabel("Consommation [kWh]")
        ax.set_title("Consommation mensuelle par usage")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(output_path)

    plt.close()