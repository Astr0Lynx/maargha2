#!/usr/bin/env python3
"""
Create interactive Leaflet maps for trajectory comparison.
"""

import json
from math import radians, cos, sin, asin, sqrt

def read_pos(path):
    """Read RTKLIB POS file."""
    rows = []
    with open(path) as f:
        for line in f:
            if line.startswith('%') or line.startswith('#'):
                continue
            parts = line.split()
            if len(parts) < 8:
                continue
            try:
                lat, lon, height = float(parts[2]), float(parts[3]), float(parts[4])
                rows.append({'lat': lat, 'lon': lon, 'height': height})
            except:
                continue
    return rows

def read_csv(path):
    """Read our CSV files."""
    rows = []
    with open(path) as f:
        f.readline()  # skip header
        for line in f:
            parts = line.split(',')
            if len(parts) >= 3:
                try:
                    lat, lon = float(parts[1]), float(parts[2])
                    rows.append({'lat': lat, 'lon': lon})
                except:
                    continue
    return rows

def build_map(baseline, kalman, raim):
    """Create interactive Leaflet map."""
    html = """<!DOCTYPE html>
<html>
<head>
    <title>Trajectory Cleaning Results</title>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css" />
    <script src="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js"></script>
    <style>
        body { margin:0; padding:0; }
        #map { position: absolute; top:0; bottom:0; width:100%; }
        .info { 
            padding: 6px 8px; 
            font: 14px Arial, Helvetica, sans-serif; 
            background: white; 
            background: rgba(255,255,255,0.9);
            box-shadow: 0 0 15px rgba(0,0,0,0.2);
            border-radius: 5px;
        }
        .legend { 
            padding: 8px 12px;
            font: 13px Arial;
            background: white;
            background: rgba(255,255,255,0.95);
            box-shadow: 0 0 15px rgba(0,0,0,0.2);
            border-radius: 5px;
            line-height: 1.8;
        }
        .legend i { 
            width: 18px; 
            height: 18px; 
            float: left; 
            margin-right: 8px; 
            opacity: 0.7; 
            border: 1px solid #ccc;
        }
        .metric {
            font-size: 12px;
            margin: 4px 0;
            padding: 2px;
        }
        .best {
            background-color: #c8e6c9;
            padding: 2px 4px;
            border-radius: 3px;
            margin-top: 8px;
            font-weight: bold;
        }
    </style>
</head>
<body>

<div id="map"></div>

<div class="legend" style="top: 10px; right: 10px; width: 320px; position: fixed; z-index: 500;">
    <div class="metric"><strong>Trajectory Cleaning Results - Click on lines to see details!</strong></div>
    <div style="border-top: 1px solid #ccc; margin: 6px 0;"></div>
    
    <div style="display: flex; align-items: center; margin: 8px 0;">
        <div style="width: 20px; height: 3px; background: #000; margin-right: 8px; border: 1px solid #333;"></div>
        <span><strong>BASELINE (unclean) - WITH SPIKES</strong></span>
    </div>
    <div style="font-size: 11px; margin-left: 28px; color: #666; margin-bottom: 8px;">
        Mean: 2.90m | P95: 6.18m | Spikes >5m: 41
    </div>
    
    <div style="display: flex; align-items: center; margin: 8px 0;">
        <div style="width: 20px; height: 3px; background: #ff9800; margin-right: 8px;"></div>
        <span>RAIM Gate (moderate improvement)</span>
    </div>
    <div style="font-size: 11px; margin-left: 28px; color: #666; margin-bottom: 8px;">
        Mean: 2.85m | P95: 5.95m | Spikes >5m: 27 | Lost 52 epochs
    </div>
    
    <div style="display: flex; align-items: center; margin: 8px 0;">
        <div style="width: 20px; height: 3px; background: #4CAF50; margin-right: 8px; border: 1px solid #2e7d32;"></div>
        <span><strong>Robust Kalman (BEST SOLUTION) ✓</strong></span>
    </div>
    <div style="font-size: 11px; margin-left: 28px; color: #2e7d32; margin-bottom: 8px; font-weight: bold;">
        Mean: 1.56m | P95: 3.73m | Spikes >5m: 5 | All 393 epochs retained
    </div>
    
    <div style="border-top: 1px solid #ccc; margin: 8px 0;"></div>
    
    <div class="best">
        ✓ USE: trajectory_app4_kalman.csv FOR LANE-LEVEL MATCHING
    </div>
    
    <div style="margin-top: 8px; font-size: 11px; line-height: 1.5; background: #e3f2fd; padding: 6px; border-radius: 3px;">
        <b>Key Improvements:</b><br>
        • Mean step: ↓46% (2.90m → 1.56m)<br>
        • P95 step: ↓40% (6.18m → 3.73m)<br>
        • Spikes >5m: ↓88% (41 → 5)<br>
        • Spikes >10m: Eliminated (2 → 0)
    </div>
</div>

<script>
var map = L.map('map').setView([17.4453, 78.3489], 16);

L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '© OpenStreetMap contributors',
    maxZoom: 19
}).addTo(map);

// Baseline trajectory (black - more visible)
var baseline = """ + json.dumps([[r['lat'], r['lon']] for r in baseline]) + """;
L.polyline(baseline, {
    color: '#000000',
    weight: 2.5,
    opacity: 0.8,
    dashArray: '8, 4',
    className: 'baseline'
}).addTo(map).bindPopup('BASELINE - Unclean trajectory with spikes (mean step: 2.90m, 41 spikes >5m)');

// RAIM Gate trajectory (orange)
var raim = """ + json.dumps([[r['lat'], r['lon']] for r in raim]) + """;
L.polyline(raim, {
    color: '#ff9800',
    weight: 2.5,
    opacity: 0.75,
    className: 'raim'
}).addTo(map).bindPopup('RAIM Gate approach (341 epochs, mean step: 2.85m, 27 spikes >5m)');

// Robust Kalman trajectory (green - best)
var kalman = """ + json.dumps([[r['lat'], r['lon']] for r in kalman]) + """;
L.polyline(kalman, {
    color: '#4CAF50',
    weight: 3.5,
    opacity: 0.9,
    className: 'kalman'
}).addTo(map).bindPopup('Robust Kalman Filter: BEST (393 epochs, mean step: 1.56m, only 5 spikes >5m)');

// Add start and end markers
var startMarker = L.circleMarker([baseline[0][0], baseline[0][1]], {
    radius: 8,
    fillColor: '#2196F3',
    color: '#fff',
    weight: 2,
    opacity: 1,
    fillOpacity: 0.8
}).addTo(map).bindPopup('Start (05:40:23 UTC)');

var endMarker = L.circleMarker([baseline[baseline.length-1][0], baseline[baseline.length-1][1]], {
    radius: 8,
    fillColor: '#F44336',
    color: '#fff',
    weight: 2,
    opacity: 1,
    fillOpacity: 0.8
}).addTo(map).bindPopup('End (05:46:55 UTC)');

</script>

</body>
</html>
"""
    
    with open('trajectory_cleaned_comparison.html', 'w', encoding='utf-8') as f:
        f.write(html)
    print("Saved: trajectory_cleaned_comparison.html")

if __name__ == '__main__':
    print("Loading trajectories...")
    baseline = read_pos('out/solution_first.pos')
    kalman = read_csv('trajectory_app4_kalman.csv')
    raim = read_csv('trajectory_app3_raim.csv')
    
    print(f"Baseline: {len(baseline)} epochs")
    print(f"Kalman: {len(kalman)} epochs")  
    print(f"RAIM: {len(raim)} epochs")
    
    build_map(baseline, kalman, raim)
    print("\n✓ Interactive map created!")
