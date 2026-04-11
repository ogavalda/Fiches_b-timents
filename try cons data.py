from bs4 import BeautifulSoup

def get_unique_uvalues_by_tilt(html: str) -> dict[float, list[float]]:
    soup = BeautifulSoup(html, "html.parser")

    for b in soup.find_all("b"):
        if "Opaque Exterior" in b.get_text():

            table = b.find_next("table")
            if not table:
                continue

            rows = table.find_all("tr")

            # 🔥 Extract headers dynamically
            headers = [th.get_text(strip=True) for th in rows[0].find_all("td")]

            # Find correct column indices
            u_index = headers.index("U-Factor with Film [W/m2-K]")
            tilt_index = headers.index("Tilt [deg]")

            result = {}

            for row in rows[1:]:
                cols = [td.get_text(strip=True) for td in row.find_all("td")]

                if len(cols) <= max(u_index, tilt_index):
                    continue

                try:
                    u_value = float(cols[u_index])
                    tilt = float(cols[tilt_index])

                    result.setdefault(tilt, set()).add(u_value)

                except:
                    continue

            return {k: sorted(v) for k, v in result.items()}

    return {}

html_path = r"C:\Users\Mahmoud\OneDrive - Concordia University - Canada\Phase 2 Office Buildings\cards\Trial single\ID47_HR_AJ_19802010\ID47_HR_AJ_19802010\run\eplustbl.htm"

with open(html_path, "r", encoding="utf-8") as f:
    html = f.read()

trial_list = get_unique_uvalues_by_tilt(html)

print(trial_list)