from geomeppy import IDF
from eppy.function_helpers import getcoords

import plotly.graph_objects as go
import numpy as np
import mapbox_earcut as earcut
import kaleido

import os


# =====================================================
# VISUALIZATION
# =====================================================

def view_geometry(idd_path, idf_path, savepath=None):
    # first set idd
    set_IDD(idd_path)
    # create IDF object
    idf = IDF(idf_path)


    # generate image
    fig = go.Figure()

    traces = build_plotly_geometry(idf)

    for t in traces:
        fig.add_trace(t)

    fig.update_layout(

        scene=dict(

            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
            zaxis=dict(visible=False),

            aspectmode='data',

            camera=dict(
                eye=dict(
                    x=1.0,
                    y=-2.0,
                    z=0.8
                )
            )
        ),

        margin=dict(
            l=0,
            r=0,
            t=0,
            b=0
        ),

        showlegend=False
    )

    if savepath:
        fig.write_image(
            savepath,
            width=1800,
            height=1400,
            scale=2
        )

    #fig.show()




# =====================================================
# BUILD PLOTLY TRACES
# =====================================================

def build_plotly_geometry(idf):

    surfaces = get_surfaces(idf)
    zones = get_zones(idf)

    origins = build_surface_origins(surfaces, zones)

    categories = {
        "wall": [],
        "roof": [],
        "window": [],
        "door": [],
        "floor": []
    }

    # categorize polygons
    for s in surfaces:
        stype = s.Surface_Type.lower()
        poly = adjusted_polygon(s, origins) # each polygon has a list of 4 sets of X,Y,Z coordinates

        if stype == "wall":
            categories["wall"].append(poly)

        elif stype == "roof":
            categories["roof"].append(poly)

        elif stype == "window":
            # when windows cooincide with wall surfaces they aren't properly visible, offset outward to have windows "lay on top of" the walls
            poly = offset_polygon_along_normal(poly)
            categories["window"].append(poly)

        elif stype == "door":
            # same for doors : add offset
            poly = offset_polygon_along_normal(poly)
            categories["door"].append(poly)

        elif stype == "floor":
            categories["floor"].append(poly)

    colors = {
        "wall": "#e6c973",
        "roof": "#5d2e2e",
        "window": "#abdee3",
        "door": "#ac9656",
        "floor": "dimgray"
    }

    edge_colors = {
        "wall": "black",
        "roof": "black",
        "window": "darkblue",
        "door": "dimgrey",
        "floor": "black"
    }


    traces = []
    for category, polys in categories.items():

        if not polys: # no surfaces in category
            continue
        
        x, y, z, i, j, k = polygons_to_mesh(polys) # transform surface coordinates to 3D mesh

        opacity = 1.0

        # surface mesh
        mesh = go.Mesh3d(
            x=x,
            y=y,
            z=z,
            i=i,
            j=j,
            k=k,
            color=colors[category],
            opacity=opacity,
            flatshading=True,
            hoverinfo="skip",
            name=category
        )

        traces.append(mesh)

        # edge overlay
        edge_trace = build_polygon_edge_trace(
            polys,
            color=edge_colors[category],
            width=1 if category == "window" else 2
        )

        traces.append(edge_trace)

    return traces





# =====================================================
# SURFACE EXTRACTION
# =====================================================

def get_surfaces(idf):
    surface_types = [
        "BUILDINGSURFACE:DETAILED",
        "FENESTRATIONSURFACE:DETAILED"
    ]

    surfaces = []

    for surface_type in surface_types:

        if surface_type == "BUILDINGSURFACE:DETAILED":

            surfaces.extend([
                s for s in idf.idfobjects[surface_type]
                if s.Outside_Boundary_Condition.lower()
                in ["outdoors", "adiabatic", "foundation"]
            ])

        else:
            surfaces.extend(idf.idfobjects[surface_type])
    
    # fenestration surfaces : filter indoor windows/doors
    interior_windows = []
    for s in surfaces:
        if s.Surface_Type.lower() in ["window", "door"]:
            parent = s.Building_Surface_Name
            if parent in [surface.Name for surface in surfaces]:
                pass
            else:
                interior_windows.append(s)
    filtered_surfaces = [s for s in surfaces if s not in interior_windows]
    
    return filtered_surfaces


def get_zones(idf):
    return idf.idfobjects["ZONE"]


# =====================================================
# COORDINATE HANDLING
# =====================================================

def build_surface_origins(surfaces, zones):
    origins = {}

    # building surfaces
    for s in surfaces:
        if s.Surface_Type.lower() not in ["window", "door"]:
            zname = s.Zone_Name
            for zone in zones:
                if zone.Name == zname:
                    origins[s.Name] = (
                        zone.X_Origin,
                        zone.Y_Origin,
                        zone.Z_Origin
                    )

    # fenestration surfaces
    for s in surfaces:

        if s.Surface_Type.lower() in ["window", "door"]:

            parent = s.Building_Surface_Name

            if parent in origins:
                origins[s.Name] = origins[parent]
            else:
                print(s.Name)
                print("We shouldn't end up here")


    return origins

def adjusted_polygon(surface, origins):
    origin = origins.get(surface.Name, (0, 0, 0))
    poly = []
    for crd_set in getcoords(surface):
        poly.append(tuple(crd + org for crd, org in zip(crd_set, origin)))
    return poly


def offset_polygon_along_normal(poly, eps=0.01):

    p0 = np.array(poly[0])
    p1 = np.array(poly[1])
    p2 = np.array(poly[2])

    # polygon normal
    normal = np.cross(p1 - p0, p2 - p0)
    norm = np.linalg.norm(normal)

    if norm == 0:
        return poly

    normal = normal / norm

    # offset outward
    offset_poly = [
        tuple(np.array(p) + eps * normal)
        for p in poly
    ]

    return offset_poly


# =====================================================
# TRIANGULATION
# =====================================================


def polygons_to_mesh(polygons):

    vertices = []
    i_idx, j_idx, k_idx = [], [], []

    vertex_offset = 0

    for poly in polygons:

        if len(poly) < 3: #colinear
            continue

        # reverse winding (fixes filling in of concave surfaces)
        poly = poly[::-1]

        vertices.extend(poly)

        # fan triangulation
        for t in range(1, len(poly) - 1):

            i_idx.append(vertex_offset)
            j_idx.append(vertex_offset + t)
            k_idx.append(vertex_offset + t + 1)

        vertex_offset += len(poly)

    x = [v[0] for v in vertices]
    y = [v[1] for v in vertices]
    z = [v[2] for v in vertices]

    return x, y, z, i_idx, j_idx, k_idx


# =====================================================
# EDGE GENERATION
# =====================================================

def build_polygon_edge_trace(polygons, color="black", width=2):

    x_lines = []
    y_lines = []
    z_lines = []

    for poly in polygons:

        n = len(poly)

        for idx in range(n):

            p1 = poly[idx]
            p2 = poly[(idx + 1) % n]

            x_lines += [p1[0], p2[0], None]
            y_lines += [p1[1], p2[1], None]
            z_lines += [p1[2], p2[2], None]

    return go.Scatter3d(
        x=x_lines,
        y=y_lines,
        z=z_lines,
        mode="lines",
        line=dict(
            color=color,
            width=width
        ),
        hoverinfo="skip",
        showlegend=False
    )


# =====================================================
# SUPPORT FUNCTIONS
# =====================================================


### before creating any geomeppy idf object, the idd file needs to be linked to the geomeppy IDF class
# this only needs to happen once
def set_IDD(idd_file):
    if os.path.exists(idd_file):
        IDF.setiddname(idd_file)
    else:
        raise Exception('IDD file of E+ installation not in default location, add correct path')



