"""
Application
SPDX - License - Identifier: LGPL - 3.0 - or -later
Copyright © 2025-2026 Université Polytechnique
                      Next-Generation Cities Institute, Concordia University
Code contributors: Kato Vanroy, kato.vanroy@polymtl.ca
                   Mahmoud Awad, mahmoud.awad@mail.concordia.ca
                   Oriol Gavalda, oriol.gavalda@concordia.ca
"""


import os
from per_folder import process_building
from datetime import datetime
# PATHS
PROJECTS_ROOT = r"SFD_2026"

# NEW: updated template here 
TEMPLATES = r"SFD_2026"
#TEMPLATES = r"MURBS_2026"

#IDD_PATH = r"C:\EnergyPlusV25-2-0\Energy+.idd"
IDD_PATH = r"C:\EnergyPlusV22-2-0\Energy+.idd"

### not used : 
view_folder = r"View cards"
operation_folder = r"Operation cards"

### differentiate poly/concordia functions
team_id = 'poly'


def run_all():
    for name in os.listdir(PROJECTS_ROOT):

        path = os.path.join(PROJECTS_ROOT, name)

        if not os.path.isdir(path):
            continue

        try:
            print(f"Processing {name}...")
            out = process_building(path, TEMPLATES, IDD_PATH, operation_folder,view_folder, team_id)
            print(f"✔ Done: {out}")

        except Exception as e:
            print(f"❌ Error in {name}: {e}")


if __name__ == "__main__":
    run_all()