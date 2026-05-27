from bs4 import BeautifulSoup
import os
import json

def extract_construction_summary(html_input: str) -> dict:
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

                    elif tilt == 180:
                        data["Roof"].add(u)

                    elif tilt == 0:
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

            for row in rows[1:]:
                cols = [td.get_text(strip=True) for td in row.find_all("td")]

                if len(cols) <= max(u_index, construction_index):
                    continue

                try:
                    construction = cols[construction_index].upper()
                    u = float(cols[u_index])

                    if "WALL" in construction:
                        data["Walls Int"].add(u)

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

    # -------------------------
    # FINAL AGGREGATION
    # -------------------------
    def avg(values):
        return sum(values) / len(values) if values else None

    Infiltration = 0   ## infiltration to be recoded

    return {
        "Walls Ext [W/m2-K]": avg(data["Walls Ext"]),
        "Walls Int [W/m2-K]": 0, ## no int walls
        "Roof [W/m2-K]": avg(data["Roof"]), ## roof to be recoded
        "Slabs [W/m2-K]": 0, ## slabs to be recoded 
        "Glazing [W/m2-K]": avg(data["Glazing"]),
        "SHGC": avg(data["SHGC"]),
        "Infiltration [m^3/h-m^2]": Infiltration, ## infiltration to be recoded
    }, floor_area