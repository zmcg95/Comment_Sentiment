# streamlit_trail_runner.py
import streamlit as st
import osmnx as ox
import networkx as nx
import random
import math
import gpxpy
import gpxpy.gpx

# -----------------------------
# 1️⃣ Helper: nearest node manually
# -----------------------------
def nearest_node_manual(G, lat, lon):
    min_dist = float('inf')
    nearest = None
    for node, data in G.nodes(data=True):
        node_lat = data['y']
        node_lon = data['x']
        # Haversine distance in meters
        R = 6371000
        phi1 = math.radians(lat)
        phi2 = math.radians(node_lat)
        delta_phi = math.radians(node_lat - lat)
        delta_lambda = math.radians(node_lon - lon)
        a = math.sin(delta_phi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(delta_lambda/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        d = R * c
        if d < min_dist:
            min_dist = d
            nearest = node
    return nearest

# -----------------------------
# 2️⃣ Helper: generate routes
# -----------------------------
def generate_alternative_routes(G, start, end, target_distance, tolerance, k=3):
    routes = []
    attempts = 0
    max_attempts = 1000
    nodes_list = list(G.nodes)

    while len(routes) < k and attempts < max_attempts:
        attempts += 1
        mid_node = random.choice(nodes_list)

        try:
            path1 = nx.shortest_path(G, start, mid_node, weight='length')
            path2 = nx.shortest_path(G, mid_node, end, weight='length')
            route = path1 + path2[1:]

            length = sum(G[u][v][0]['length'] for u, v in zip(route[:-1], route[1:]))

            if abs(length - target_distance) <= tolerance:
                if route not in routes:
                    routes.append(route)
        except (nx.NetworkXNoPath, KeyError):
            continue

    return routes

# -----------------------------
# 3️⃣ Helper: export GPX
# -----------------------------
def route_to_gpx(G, route):
    gpx = gpxpy.gpx.GPX()
    gpx_track = gpxpy.gpx.GPXTrack()
    gpx.tracks.append(gpx_track)
    gpx_segment = gpxpy.gpx.GPXTrackSegment()
    gpx_track.segments.append(gpx_segment)

    for node in route:
        data = G.nodes[node]
        gpx_segment.points.append(gpxpy.gpx.GPXTrackPoint(data['y'], data['x']))

    return gpx.to_xml()

# -----------------------------
# Streamlit App
# -----------------------------
st.title("Trail Runner Route Generator")
st.write("Generate 3 trail routes and download as GPX for your watch.")

# Input parameters
place = st.text_input("Place / City", "Castricum, Netherlands")
start_lat = st.number_input("Start Latitude", value=52.547314)
start_lon = st.number_input("Start Longitude", value=4.646000)
end_lat = st.number_input("End Latitude", value=52.543043)
end_lon = st.number_input("End Longitude", value=4.631985)
target_distance = st.number_input("Target Distance (meters)", value=3000)
tolerance = st.number_input("Distance Tolerance (meters)", value=300)

generate_button = st.button("Generate Routes")

if generate_button:
    with st.spinner("Loading trail network..."):
        G = ox.graph_from_place(place, network_type="walk")
        G = G.to_undirected()

        # Largest connected component
        largest_cc_nodes = max(nx.connected_components(G), key=len)
        G = G.subgraph(largest_cc_nodes).copy()

        # Filter trails
        trail_nodes = set()
        for u, v, k, d in G.edges(keys=True, data=True):
            if d.get("highway") in ["footway", "path", "track"]:
                trail_nodes.add(u)
                trail_nodes.add(v)
        G = G.subgraph(trail_nodes).copy()

        # Snap start/end nodes manually
        start_node = nearest_node_manual(G, start_lat, start_lon)
        end_node = nearest_node_manual(G, end_lat, end_lon)

        # Generate routes
        routes = generate_alternative_routes(G, start_node, end_node, target_distance, tolerance, k=3)

    if not routes:
        st.warning("No routes found. Try increasing tolerance or adjusting start/end points.")
    else:
        st.success(f"{len(routes)} routes generated!")
        for i, r in enumerate(routes):
            length = sum(G[u][v][0]['length'] for u, v in zip(r[:-1], r[1:]))
            st.write(f"Route {i+1}: {length/1000:.2f} km")
            fig, ax = ox.plot_graph_route(G, r, show=False, close=False)
            st.pyplot(fig)

            # GPX download
            gpx_data = route_to_gpx(G, r)
            st.download_button(
                label=f"Download Route {i+1} as GPX",
                data=gpx_data,
                file_name=f"route_{i+1}.gpx",
                mime="application/gpx+xml"
            )
