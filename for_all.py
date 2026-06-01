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
from datetime import datetime

from per_folder import process_building
from save_results import save_files

# PATHS
PROJECTS_ROOT = r"SFD_2026"
GIT_ROOT = r"git_root"

# NEW: updated template here 
TEMPLATES = r"SFD_2026"
#TEMPLATES = r"MURBS_2026"

#IDD_PATH = r"C:\EnergyPlusV25-2-0\Energy+.idd"
IDD_PATH = r"C:\EnergyPlusV22-2-0\Energy+.idd"

### not used : 
view_folder = r"View cards"
operation_folder = r"Operation cards"

### differentiate poly/concordia functions
from config import team_id



def run_all():
    for name in os.listdir(PROJECTS_ROOT):

        path = os.path.join(PROJECTS_ROOT, name)

        if not os.path.isdir(path):
            continue

        try:            
            # FIRST : create outputs (reports) 
            print(f"Processing {name}...")
            out = process_building(path, TEMPLATES, IDD_PATH, operation_folder,view_folder, team_id) # returns folder structure for git
            print(f"✔ Done: {name}")
            # THEN : save all into proper file structure            
            print(f"Saving {name}...")
            out = save_files(path, GIT_ROOT, out)
            print(f"✔ Done: {name}")

        except Exception as e:
            print(f"❌ Error in {name}: {e}")


if __name__ == "__main__":
    run_all()