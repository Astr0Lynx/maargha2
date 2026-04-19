import os
import json
import pandas as pd
import numpy as np
import osmnx as ox
import geopandas as gpd
from shapely.geometry import Point, LineString
import math
import datetime

class ViterbiLaneMatcher:
    def __init__(self, data_path):
        self.data_path = data_path
        self.df = pd.read_csv(data_path)
        self.center_lat = self.df['lat'].mean()
        self.center_lon = self.df['lon'].mean()
        
        print(f"\n[1/4] Downloading HD Base Map from OSM for {(self.center_lat, self.center_lon)}...")
        self.G = ox.graph_from_point((self.center_lat, self.center_lon), dist=1500, network_type='drive')
        
        print("[2/4] Projecting Graph to metric UTM CRS for accurate Cartesian math...")
        self.G_proj = ox.project_graph(self.G)
        self.nodes, self.edges = ox.graph_to_gdfs(self.G_proj)
        self.sindex = self.edges.sindex
        print(f"      -> Graph Ready. {len(self.edges)} Directed Edges isolated.")

        gdf_points = gpd.GeoDataFrame(
            self.df, geometry=gpd.points_from_xy(self.df.lon, self.df.lat), crs="EPSG:4326"
        )
        self.points_proj = gdf_points.to_crs(self.edges.crs)
        
    def calculate_headings(self):
        print("[3/4] Modeling Instantaneous NMEA Angular Headings...")
        headings = []
        for i in range(len(self.points_proj)):
            if i == len(self.points_proj) - 1:
                headings.append(headings[-1])
            else:
                p1 = self.points_proj.iloc[i].geometry
                p2 = self.points_proj.iloc[i+1].geometry
                
                dx = p2.x - p1.x
                dy = p2.y - p1.y
                brng = (math.degrees(math.atan2(dx, dy)) + 360) % 360
                headings.append(brng)
                
        self.df['heading'] = headings

    def run_viterbi(self):
        print("[4/4] Executing Viterbi Hidden Markov Model (HMM) Decoder...")
        SIGMA_Z = 15.0  # Gaussian parameter for spatial emission probability
        
        V = [{}] # HMM Dynamic Programming Matrix
        
        for t in range(len(self.points_proj)):
            pt = self.points_proj.iloc[t].geometry
            obs_heading = self.df.iloc[t]['heading']
            
            # Initial Search Domain
            candidate_idx = list(self.sindex.intersection(pt.buffer(50).bounds))
            candidates = self.edges.iloc[candidate_idx].copy()
            
            if len(candidates) == 0:
                candidate_idx = list(self.sindex.intersection(pt.buffer(200).bounds))
                candidates = self.edges.iloc[candidate_idx].copy()
                
            state_probs = {}
            for idx, candidate in candidates.iterrows():
                geom = candidate.geometry
                dist = pt.distance(geom)
                
                # Emission formulation (how close is GPS to lane?)
                emission = math.exp(-0.5 * (dist / SIGMA_Z) ** 2) / (math.sqrt(2 * math.pi) * SIGMA_Z)
                
                # Directionality formulation (does driving angle match arrow vector?)
                coords = list(geom.coords)
                if len(coords) >= 2:
                    dx = coords[-1][0] - coords[0][0]
                    dy = coords[-1][1] - coords[0][1]
                    edge_brng = (math.degrees(math.atan2(dx, dy)) + 360) % 360
                    
                    diff = min((obs_heading - edge_brng) % 360, (edge_brng - obs_heading) % 360)
                    if diff > 100:
                        emission *= 0.0001 # Absolute penalty for wrong-way traffic mapping
                    elif diff > 45:
                        emission *= 0.1
                    else:
                        emission *= math.cos(math.radians(diff)) # Reward high angular fit
                        
                state_id = (idx[0], idx[1], idx[2])
                
                if t == 0:
                    state_probs[state_id] = {"prob": emission, "prev": None, "edge_geom": geom}
                else:
                    max_prob = -1
                    best_prev = None
                    for prev_state, prev_data in V[t-1].items():
                        # Structural transition topological validation (same road vs disjoint)
                        transition = 1.0 if (prev_state[1] == state_id[0] or prev_state == state_id) else 0.01
                        tr_prob = prev_data["prob"] * transition * emission
                        
                        if tr_prob > max_prob:
                            max_prob = tr_prob
                            best_prev = prev_state
                            
                    state_probs[state_id] = {"prob": max_prob, "prev": best_prev, "edge_geom": geom}
            
            if not state_probs and t > 0:
                state_probs = V[t-1] # Emergency dead-reckoning fallback
                
            V.append(state_probs)
            
        print("      -> Viterbi State matrix populated. Backtracking global optimal path...")
        
        final_state = max(V[-1].keys(), key=lambda k: V[-1][k]["prob"])
        curr_state = final_state
        
        path = []
        for t in range(len(V)-1, 0, -1):
            if curr_state not in V[t]: curr_state = list(V[t].keys())[0]
                
            edge_geom = V[t][curr_state]["edge_geom"]
            raw_pt = self.points_proj.iloc[t-1].geometry
            # Mathematical explicit projection snap!
            snapped_pt = edge_geom.interpolate(edge_geom.project(raw_pt))
            path.append((t-1, snapped_pt))
            
            curr_state = V[t][curr_state]["prev"]
            
        path.reverse()
        
        # Exporting React Structure
        print("      -> Generating Viterbi Snapped JSON Output...")
        snapped_gdf = gpd.GeoDataFrame(geometry=[p[1] for p in path], crs=self.edges.crs)
        snapped_gdf_4326 = snapped_gdf.to_crs("EPSG:4326")
        
        ui_json = []
        for i, row in enumerate(path):
            t_idx = row[0]
            pt = snapped_gdf_4326.iloc[i].geometry
            ts = int(self.df.iloc[t_idx]['timestamp'])
            
            dt = datetime.datetime.fromtimestamp(ts / 1000.0)
            ui_json.append({
                "x": 0.0, "y": 0.0, "z": 1.0, "v": 10.0,
                "lat": pt.y, "lon": pt.x,
                "time": dt.strftime("%H-%M-%S"),
                "milli": ts,
                "file": "", 
                "Surface": "Viterbi_Lane_Level",
                "Condition": "Snapped"
            })
            
        out_json_path = "maarg-web-ui/src/Data/latest_viterbi.json"
        os.makedirs(os.path.dirname(out_json_path), exist_ok=True)
        with open(out_json_path, 'w') as jf:
            json.dump(ui_json, jf, indent=2)
            
        print(f"\n======================================================\nSUCCESS: Viterbi HMM Map Mapped Output saved natively to: {out_json_path}\n======================================================")

if __name__ == "__main__":
    if os.path.exists("Data/trajectory_cleaned.csv"):
        matcher = ViterbiLaneMatcher("Data/trajectory_cleaned.csv")
        matcher.calculate_headings()
        matcher.run_viterbi()
    else:
        print("Data/trajectory_cleaned.csv missing!")
