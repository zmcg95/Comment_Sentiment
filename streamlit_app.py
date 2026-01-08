import streamlit as st
import osmnx as ox
import networkx as nx
import random
import math
import gpxpy
import gpxpy.gpx
import folium
from streamlit_folium import st_folium

# -----------------------------
# Page polish (padding)
# -----------------------------
st.markdown(
    """
    <style>
        .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
        }
    </style>
    """,
    unsafe_allow_html=True
)

# -----------------------------
# Session state
# -----------------------------
if "clicks" not in st.session_state:
    st.session_state.clicks = []

# -----------------------------
# Helper: manual nearest node (Cloud-safe)
# Helper: manual nearest node
# -----------------------------
def nearest_node_manual(G, lat, lon):
    min_dist = float("inf")
@@ -50,7 +64,6 @@ def nearest_node_manual(G, lat, lon):
def generate_alternative_routes(G, start, end, target_distance, tolerance, k=3):
    routes = []

    # Single Dijkstra from start
    lengths, paths = nx.single_source_dijkstra(G, start, weight="length")

    for mid_node, dist1 in lengths.items():
@@ -64,12 +77,10 @@ def generate_alternative_routes(G, start, end, target_distance, tolerance, k=3):
                for u, v in zip(path2[:-1], path2[1:])
            )

            total_dist = dist1 + dist2

            if abs(total_dist - target_distance) <= tolerance:
                route = paths[mid_node] + path2[1:]
                routes.append(route)
            total = dist1 + dist2

            if abs(total - target_distance) <= tolerance:
                routes.append(paths[mid_node] + path2[1:])
                if len(routes) >= k:
                    break

@@ -79,13 +90,12 @@ def generate_alternative_routes(G, start, end, target_distance, tolerance, k=3):
    return routes

# -----------------------------
# Helper: export GPX
# Helper: GPX export
# -----------------------------
def route_to_gpx(G, route):
    gpx = gpxpy.gpx.GPX()
    track = gpxpy.gpx.GPXTrack()
    segment = gpxpy.gpx.GPXTrackSegment()

    gpx.tracks.append(track)
    track.segments.append(segment)

@@ -98,11 +108,30 @@ def route_to_gpx(G, route):
    return gpx.to_xml()

# -----------------------------
# UI
# Hero header
# -----------------------------
st.title("🏃 Trail Runner Route GPX Generator")
st.write("Click on the map to select your start/end point. Trails load automatically.")
st.markdown(
    """
    <div style="
        background-color:#f0f7f4;
        padding:25px;
        border-radius:15px;
        text-align:center;
        margin-bottom:25px;
        border:1px solid #cce3dc;
    ">
        <h1 style="margin-bottom:10px;">🏃 Trail Runner Route GPX Generator</h1>
        <p style="font-size:16px; color:#444;">
            Click on the map to select your start/end point. Trails load automatically.
        </p>
    </div>
    """,
    unsafe_allow_html=True
)

# -----------------------------
# Controls
# -----------------------------
route_mode = st.radio(
    "Route Type",
    ["Loop (1 click)", "Point-to-point (2 clicks)"]
@@ -111,6 +140,7 @@ def route_to_gpx(G, route):
target_distance = st.number_input(
    "Target Distance (meters)", value=3000, step=500
)

tolerance = st.number_input(
    "Distance Tolerance (meters)", value=300, step=100
)
@@ -121,45 +151,38 @@ def route_to_gpx(G, route):
# -----------------------------
# Map
# -----------------------------
m = folium.Map(
    location=[52.0, 5.0],
    zoom_start=6,
    tiles="OpenStreetMap"
)
m = folium.Map(location=[52, 5], zoom_start=6)

for i, (lat, lon) in enumerate(st.session_state.clicks):
    label = "Start" if i == 0 else "End"
    color = "green" if i == 0 else "red"
    folium.Marker(
        [lat, lon],
        popup=label,
        icon=folium.Icon(color=color)
        popup="Start" if i == 0 else "End",
        icon=folium.Icon(color="green" if i == 0 else "red"),
    ).add_to(m)

map_data = st_folium(m, height=500, width=700)
map_data = st_folium(m, height=450, width=700)

if map_data and map_data.get("last_clicked"):
    lat = map_data["last_clicked"]["lat"]
    lon = map_data["last_clicked"]["lng"]

    max_clicks = 1 if route_mode.startswith("Loop") else 2

    if len(st.session_state.clicks) < max_clicks:
        st.session_state.clicks.append((lat, lon))

# -----------------------------
# Generate routes
# Generate Routes
# -----------------------------
if st.button("Generate Routes"):
    needed_clicks = 1 if route_mode.startswith("Loop") else 2
    needed = 1 if route_mode.startswith("Loop") else 2

    if len(st.session_state.clicks) < needed_clicks:
        st.warning("Please click on the map to select start/end points.")
    if len(st.session_state.clicks) < needed:
        st.warning("Please click on the map.")
        st.stop()

    with st.spinner("Loading trail network and generating routes..."):
    with st.spinner("Loading trails & generating routes..."):
        center_lat, center_lon = st.session_state.clicks[0]

        # Load only trails, 10km radius (FAST)
        G = ox.graph_from_point(
            (center_lat, center_lon),
            dist=10000,
@@ -169,55 +192,59 @@ def route_to_gpx(G, route):
        )

        G = G.to_undirected()

        # Keep largest connected component
        largest_cc = max(nx.connected_components(G), key=len)
        G = G.subgraph(largest_cc).copy()
        G = G.subgraph(max(nx.connected_components(G), key=len)).copy()

        start_lat, start_lon = st.session_state.clicks[0]
        if route_mode.startswith("Loop"):
            end_lat, end_lon = start_lat, start_lon
        else:
            end_lat, end_lon = st.session_state.clicks[1]
        end_lat, end_lon = (
            (start_lat, start_lon)
            if route_mode.startswith("Loop")
            else st.session_state.clicks[1]
        )

        start_node = nearest_node_manual(G, start_lat, start_lon)
        end_node = nearest_node_manual(G, end_lat, end_lon)

        if start_node is None or end_node is None:
            st.warning("No nearby trails found. Try clicking closer to a path.")
            st.stop()

        routes = generate_alternative_routes(
            G,
            start_node,
            end_node,
            target_distance,
            tolerance,
            k=3
            G, start_node, end_node, target_distance, tolerance
        )

    if not routes:
        st.warning("No routes found. Try increasing distance or tolerance.")
        st.warning("No routes found. Try adjusting distance or tolerance.")
    else:
        st.success(f"{len(routes)} routes generated!")

        for i, r in enumerate(routes):
            length = sum(
                G[u][v][0]["length"]
                for u, v in zip(r[:-1], r[1:])
            )

            st.write(f"**Route {i+1}** — {length/1000:.2f} km")

            fig, ax = ox.plot_graph_route(
                G, r, show=False, close=False
            )
            st.pyplot(fig)

            gpx_data = route_to_gpx(G, r)
            st.download_button(
                f"Download Route {i+1} (GPX)",
                gpx_data,
                file_name=f"route_{i+1}.gpx",
                mime="application/gpx+xml",
            )
        cols = st.columns(len(routes))
        for i, (col, r) in enumerate(zip(cols, routes)):
            with col:
                length = sum(
                    G[u][v][0]["length"]
                    for u, v in zip(r[:-1], r[1:])
                )

                st.markdown(
                    f"""
                    <div style="
                        border:1px solid #ddd;
                        border-radius:12px;
                        padding:10px;
                        text-align:center;
                        background-color:#fafafa;
                    ">
                        <h4>Route {i+1}</h4>
                        <p>{length/1000:.2f} km</p>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

                fig, ax = ox.plot_graph_route(
                    G, r, show=False, close=False, figsize=(4, 4)
                )
                st.pyplot(fig)

                st.download_button(
                    "⬇️ Download GPX",
                    route_to_gpx(G, r),
                    file_name=f"route_{i+1}.gpx",
                    mime="application/gpx+xml",
                )
