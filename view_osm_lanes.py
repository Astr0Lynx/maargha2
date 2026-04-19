import osmnx as ox
import matplotlib.pyplot as plt
import pandas as pd

# Load trajectory to find center
try:
    df = pd.read_csv("Data/trajectory_cleaned.csv")
    center_lat = df['lat'].mean()
    center_lon = df['lon'].mean()
    print(f"Center evaluated from trajectory: {center_lat}, {center_lon}")
except Exception as e:
    print(f"Could not load trajectory ({e}). Falling back to hardcoded IIIT coordinates.")
    center_lat = 17.4455
    center_lon = 78.3489

# Download the road network (driving only)
print("Downloading OSM graph for the area...")
# dist=3000 gets a 3.0km radius bounding box around the trajectory center
G = ox.graph_from_point((center_lat, center_lon), dist=3000, network_type='drive')

print("Generating high-resolution spatial plot...")
fig, ax = plt.subplots(figsize=(15, 15), facecolor='#111111')

# Extract nodes and edges as GeoDataFrames
nodes, edges = ox.graph_to_gdfs(G)

# Plot background edges (minor roads)
minor_edges = edges[~edges['highway'].astype(str).str.contains('trunk|primary|motorway|secondary')]
for _, edge in minor_edges.iterrows():
    if hasattr(edge, "geometry") and edge.geometry is not None:
        x, y = edge.geometry.xy
        ax.plot(x, y, color='#333333', linewidth=0.8, alpha=0.5)

# Plot separated directional highways (Pink = OneWay/Explicitly Separated Vectors, Blue = Unseparated Bi-directional)
major_edges = edges[edges['highway'].astype(str).str.contains('trunk|primary|motorway|secondary')]
for _, edge in major_edges.iterrows():
    if hasattr(edge, "geometry") and edge.geometry is not None:
        # OSM defines physically separated dual-carriageways as explicit 'oneway' vectors
        # If it's a true highway, OSM draws two separate lines automatically.
        is_separated = edge.get('oneway', False)
        
        color = '#ff2a6d' if is_separated else '#05d5ff'
        linewidth = 3.0 if is_separated else 1.5
        
        x, y = edge.geometry.xy
        
        # Add a subtle directional arrow to the plot on separated vectors
        ax.plot(x, y, color=color, linewidth=linewidth, alpha=0.9)
        if is_separated:
            mid_idx = len(x) // 2
            dx = x[mid_idx] - x[mid_idx-1]
            dy = y[mid_idx] - y[mid_idx-1]
            # Normalize vector for arrow
            mag = (dx**2 + dy**2)**0.5
            if mag > 0:
                ax.arrow(x[mid_idx-1], y[mid_idx-1], dx*0.01, dy*0.01, 
                         color='white', head_width=0.0003, alpha=0.7, zorder=4)

# Overlay our actual NMEA trajectory
try:
    ax.scatter(df['lon'], df['lat'], color='#00ff44', s=12, zorder=5, label='NMEA Target Path')
except Exception:
    pass

ax.set_title("OSM Directed Vector Graph\nPink = Physically Separated Directional Lanes | Blue = Undivided Roads", 
             color='white', fontsize=16, pad=20)
ax.axis('off')
ax.margins(0)
fig.tight_layout(pad=0)

plt.savefig("iiit_directional_lanes.png", dpi=300, facecolor='#111111')
print("Successfully generated: iiit_directional_lanes.png")
