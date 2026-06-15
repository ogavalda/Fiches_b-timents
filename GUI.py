import tkinter as tk
from tkinter import filedialog
from tkinter import ttk
import os
from datetime import datetime

from per_folder import process_building
from save_results import save_files
import config
import sv_ttk


view_folder = r"View cards"
operation_folder = r"Operation cards"

#IDD_PATH = r"C:\EnergyPlusV25-2-0\Energy+.idd"
#IDD_PATH = r"C:\EnergyPlusV22-2-0\Energy+.idd"


# ======================
# Functions
# ======================

def browse_PROJECTS_ROOT():
    path = filedialog.askdirectory()
    PROJECTS_ROOT_var.set(path)

def browse_TEMPLATES():
    path = filedialog.askdirectory()
    TEMPLATES_var.set(path)

def browse_GIT_ROOT():
    path = filedialog.askdirectory()
    GIT_ROOT_var.set(path)

def browse_IDD_path():
    path = filedialog.askdirectory()
    IDD_path_var.set(path)


def run_process():

    PROJECTS_ROOT = PROJECTS_ROOT_var.get()
    GIT_ROOT = GIT_ROOT_var.get()
    TEMPLATES = TEMPLATES_var.get()
    IDD_PATH = IDD_path_var.get() + "\Energy+.idd"
    teamid = teamid_var.get()
    config.team_id = teamid
    config.per_household_toggle = per_household_var.get()

    print(f"PROJECTS_ROOT: {PROJECTS_ROOT}")
    print(f"GIT_ROOT: {GIT_ROOT}")
    print(f"TEMPLATES: {TEMPLATES}")
    print(f"Mode: {teamid}")
    print(f"team_id is {config.team_id}")
    print(f"per_household_toggle is {config.per_household_toggle}")


    for name in os.listdir(PROJECTS_ROOT):

        path = os.path.join(PROJECTS_ROOT, name)

        if not os.path.isdir(path):
            continue

        try:
            # FIRST : create outputs (reports)
            print(f"Processing {name}...")
            out = process_building(path, TEMPLATES, IDD_PATH, operation_folder,view_folder) # returns folder structure for git
            print(f"✔ Done: {name}")
            # THEN : save all into proper file structure
            print(f"Saving {name}...")
            out = save_files(path, GIT_ROOT, out)
            print(f"✔ Done: {name}")

        except Exception as e:
            print(f"❌ Error in {name}: {e}")


# ======================
# GUI
# ======================

root = tk.Tk()
root.title("My Tool")
root.geometry("800x300")

# sv_ttk.set_theme("dark")

notebook = ttk.Notebook(root)
notebook.pack(fill="both", expand=True)

tab1 = ttk.Frame(notebook)
tab2 = ttk.Frame(notebook)

notebook.add(tab1, text="Batch")
notebook.add(tab2, text="Single Building")


PROJECTS_ROOT_var = tk.StringVar(value = "D:/git/MURBS_2026")

GIT_ROOT_var = tk.StringVar(value = "D:/git/git_root")
TEMPLATES_var = tk.StringVar(value= "D:/git/SFD_2026")
IDD_path_var = tk.StringVar(value = "C:/EnergyPlusV25-2-0")
teamid_var = tk.StringVar()
per_household_var = tk.IntVar()

#### Tab1 --> Batch
# PROJECTS_ROOT Path
ttk.Label(tab2, text="PROJECT ROOT").grid(row=0, column=0, padx=5, pady=5)
ttk.Entry(tab2, textvariable=PROJECTS_ROOT_var, width=60).grid(row=0, column=1, padx=5)
ttk.Button(tab2, text="Browse", command=browse_PROJECTS_ROOT).grid(row=0, column=2)

# GIT_ROOT Path
ttk.Label(tab2,text="GIT_ROOT").grid(row=1, column=0, padx=5, pady=5)
ttk.Entry(tab2, textvariable=GIT_ROOT_var, width=60).grid(row=1, column=1)
ttk.Button(tab2, text="Browse", command=browse_GIT_ROOT).grid(row=1, column=2)

# TEMPLATES Path
ttk.Label(tab2, text="Html templates path").grid(row=2, column=0, padx=5, pady=5)
ttk.Entry(tab2, textvariable=TEMPLATES_var, width=60).grid(row=2, column=1, padx=5)
ttk.Button(tab2, text="Browse", command=browse_TEMPLATES).grid(row=2, column=2)

# IDD Path
ttk.Label(tab2, text="IDD path").grid(row=3, column=0, padx=5, pady=5)
ttk.Entry(tab2, textvariable=IDD_path_var, width=60).grid(row=3, column=1, padx=5)
ttk.Button(tab2, text="Browse", command=browse_IDD_path).grid(row=3, column=2)

## ---------- Radio Buttons
# the team_id --------------
ttk.Label(tab2, text="Archetype").grid(row=4, column=0)
ttk.Radiobutton(tab2,text="Single Family House",variable=teamid_var,value="poly").grid(row=4, column=1, sticky="w")
ttk.Radiobutton(tab2,text="Concordia",variable=teamid_var,value="Concordia").grid(row=5, column=1, sticky="w")
#-----------------------------
# the per_household_toggle --------------
ttk.Label(tab2, text="Simulation Aggregation").grid(row=4, column=1,padx=(100,0))
ttk.Radiobutton(tab2,text="Per Household",variable=per_household_var,value=1).grid(row=4, column=1,padx=(350,0), sticky="w")
ttk.Radiobutton(tab2,text="Whole Building",variable=per_household_var,value=0).grid(row=5, column=1,padx=(350,0), sticky="w")
#-----------------------------

#### Tab2 --> Single Building
# PROJECTS_ROOT Path
ttk.Label(tab2, text="Building Path").grid(row=0, column=0, padx=5, pady=5)
ttk.Entry(tab2, textvariable=PROJECTS_ROOT_var, width=60).grid(row=0, column=1, padx=5)
ttk.Button(tab2, text="Browse", command=browse_PROJECTS_ROOT).grid(row=0, column=2)

# TEMPLATES Path
ttk.Label(tab2, text="Html templates path").grid(row=2, column=0, padx=5, pady=5)
ttk.Entry(tab2, textvariable=TEMPLATES_var, width=60).grid(row=2, column=1, padx=5)
ttk.Button(tab2, text="Browse", command=browse_TEMPLATES).grid(row=2, column=2)

# IDD Path
ttk.Label(tab2, text="IDD path").grid(row=3, column=0, padx=5, pady=5)
ttk.Entry(tab2, textvariable=IDD_path_var, width=60).grid(row=3, column=1, padx=5)
ttk.Button(tab2, text="Browse", command=browse_IDD_path).grid(row=3, column=2)

## ---------- Radio Buttons
# the team_id --------------
ttk.Label(tab2, text="Archetype").grid(row=4, column=0)
ttk.Radiobutton(tab2,text="Single Family House",variable=teamid_var,value="poly").grid(row=4, column=1, sticky="w")
ttk.Radiobutton(tab2,text="Concordia",variable=teamid_var,value="Concordia").grid(row=5, column=1, sticky="w")
#-----------------------------
# the per_household_toggle --------------
ttk.Label(tab2, text="Simulation Aggregation").grid(row=4, column=1,padx=(100,0))
ttk.Radiobutton(tab2,text="Per Household",variable=per_household_var,value=1).grid(row=4, column=1,padx=(350,0), sticky="w")
ttk.Radiobutton(tab2,text="Whole Building",variable=per_household_var,value=0).grid(row=5, column=1,padx=(350,0), sticky="w")
#-----------------------------






# Run Button
ttk.Button(tab2,text="Run Single Building",command=run_process).grid(row=6, column=1, pady=20)

root.mainloop()