import openstudio


def get_HW_keys(osm_path):

    # Load model
    translator = openstudio.osversion.VersionTranslator()
    model_optional = translator.loadModel(openstudio.path(osm_path))

    if model_optional.empty():
        raise Exception("Failed to load OSM model")

    model = model_optional.get()

    # Dictionary:
    # {spaceTypeHandle : [space names]}
    spacetype_dict = {}

    # Get spaces
    for space in model.getSpaces():

        name = space.nameString()

        if not space.spaceType().empty():

            spacetype = str(space.spaceType().get().handle())

            if spacetype not in spacetype_dict:
                spacetype_dict[spacetype] = []

            spacetype_dict[spacetype].append(name)

    variable_keys = []

    # Get electric equipment
    for obj in model.getElectricEquipments():

        obj_name = obj.nameString()

        # Match only HW objects
        if 'Chau' in obj_name:

            if not obj.spaceType().empty():

                spacetype = str(obj.spaceType().get().handle())

                if spacetype in spacetype_dict:

                    for space_name in spacetype_dict[spacetype]:

                        key = f"{space_name} {obj_name}"
                        variable_keys.append(key)

    return variable_keys


osm_path = r"C:\Users\Mahmoud\OneDrive - Concordia University - Canada\Phase 2 Office Buildings\cards\models\MURBS_2026\ID39_MR_ND_1945\ID39_MR_ND_1945.osm"

print(get_HW_keys(osm_path))