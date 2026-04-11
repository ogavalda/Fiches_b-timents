from bs4 import BeautifulSoup
import os
import json

def extract_construction_summary(html_input: str, json_path) -> dict:
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

    Infiltration = get_airtightness_value(json_path)

    return {
        "Walls Ext [W/m2-K]": avg(data["Walls Ext"]),
        "Walls Int [W/m2-K]": avg(data["Walls Int"]),
        "Roof [W/m2-K]": avg(data["Roof"]),
        "Slabs [W/m2-K]": avg(data["Slabs"]),
        "Glazing [W/m2-K]": avg(data["Glazing"]),
        "SHGC": avg(data["SHGC"]),
        "Infiltration [m^3/h-m^2]": Infiltration
    }



def get_airtightness_value(json_path):
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    try:
        value = data["SetNISTInfiltrationCorrelations"]["airtightness_value"]
        return value
    except KeyError:
        print("⚠️ airtightness_value not found in JSON")
        return None

if __name__ == "__main__":
    html_path = r"C:\Users\Mahmoud\OneDrive - Concordia University - Canada\Phase 2 Office Buildings\cards\Trial single\ID47_HR_AJ_19802010\ID47_HR_AJ_19802010\run\eplustbl.htm"
    json_path = r"C:\Users\Mahmoud\OneDrive - Concordia University - Canada\Phase 2 Office Buildings\cards\Trial single\ID47_HR_AJ_19802010\ID47_HR_AJ_19802010\run\measure_attributes.json"
    result = extract_construction_summary(html_path,json_path)

    print(result)