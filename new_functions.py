import openstudio
import pandas as pd

# ============================================================
# INPUT OSM
# ============================================================

osm_path = r"MURBS_2026\ID39_MR_ND_1945\ID39_MR_ND_1945.osm"

# ============================================================
# LOAD MODEL
# ============================================================

translator = openstudio.osversion.VersionTranslator()
model = translator.loadModel(osm_path).get()

# ============================================================
# CREATE MAPPING TABLE
# ============================================================

mapping_data = []

# ============================================================
# LOOP THROUGH ELECTRIC EQUIPMENT
# ============================================================

for eq in model.getElectricEquipments():

    # --------------------------------------------------------
    # INSTANCE NAME
    # --------------------------------------------------------

    eq_instance_name = eq.nameString()

    # --------------------------------------------------------
    # SPACE NAME
    # --------------------------------------------------------

    if eq.space().is_initialized():
        space_name = eq.space().get().nameString()
    else:
        space_name = "NO SPACE"

    # --------------------------------------------------------
    # DEFINITION
    # --------------------------------------------------------

    definition = eq.electricEquipmentDefinition()

    definition_name = definition.nameString()

    # --------------------------------------------------------
    # DESIGN LEVEL
    # --------------------------------------------------------

    design_level = None

    if definition.designLevel().is_initialized():
        design_level = definition.designLevel().get()

    # --------------------------------------------------------
    # WATTS / AREA
    # --------------------------------------------------------

    watts_per_area = None

    if definition.wattsperSpaceFloorArea().is_initialized():
        watts_per_area = definition.wattsperSpaceFloorArea().get()

    # --------------------------------------------------------
    # WATTS / PERSON
    # --------------------------------------------------------

    watts_per_person = None

    if definition.wattsperPerson().is_initialized():
        watts_per_person = definition.wattsperPerson().get()

    # --------------------------------------------------------
    # SCHEDULE
    # --------------------------------------------------------

    schedule_name = "NO SCHEDULE"

    if eq.schedule().is_initialized():
        schedule_name = eq.schedule().get().nameString()

    # --------------------------------------------------------
    # STORE DATA
    # --------------------------------------------------------

    mapping_data.append({

        "Equipment_Instance": eq_instance_name,
        "Space": space_name,
        "Definition": definition_name,
        "Design_Level_W": design_level,
        "Watts_per_Area": watts_per_area,
        "Watts_per_Person": watts_per_person,
        "Schedule": schedule_name

    })

# ============================================================
# CREATE DATAFRAME
# ============================================================

df = pd.DataFrame(mapping_data)

# ============================================================
# PRINT RESULTS
# ============================================================

print("\nELECTRIC EQUIPMENT MAPPING:\n")

print(df)

# ============================================================
# EXPORT CSV
# ============================================================

df.to_csv("electric_equipment_mapping.csv", index=False)

print("\nCSV exported successfully.")