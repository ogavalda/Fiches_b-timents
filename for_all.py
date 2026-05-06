import os
from per_folder import process_building

#test

PROJECTS_ROOT = r"MURBS_2026"
view_folder = r"View cards"
operation_folder = r"Operation cards"
TEMPLATES = r"MURBS_2026"
IDD_PATH = r"C:\EnergyPlusV25-2-0\Energy+.idd"


def run_all():
    for name in os.listdir(PROJECTS_ROOT):

        path = os.path.join(PROJECTS_ROOT, name)

        if not os.path.isdir(path):
            continue

        try:
            print(f"Processing {name}...")
            out = process_building(path, TEMPLATES, IDD_PATH, operation_folder,view_folder)
            print(f"✔ Done: {out}")

        except Exception as e:
            print(f"❌ Error in {name}: {e}")


if __name__ == "__main__":
    run_all()