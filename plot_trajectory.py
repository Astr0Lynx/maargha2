#!/usr/bin/env python3
"""
Plot CORS-corrected GNSS trajectory on an interactive map
No external dependencies - uses pure Python
"""

import os
import json
import webbrowser

# Read and parse the solution file
data = []
with open('out/solution_first.pos', 'r') as f:
    for line in f:
        if line.startswith('%'):
            continue
        parts = line.split()
        if len(parts) >= 14:
            try:
                data.append({
                    'time': parts[1],
                    'lat': float(parts[2]),
                    'lon': float(parts[3]),
                    'height': float(parts[4]),
                    'Q': int(parts[5]),
                    'ns': int(parts[6]),
                    'sdn': float(parts[7]),
                    'sde': float(parts[8])
                })
            except:
                pass

# Print summary
print("Trajectory Summary:")
print(f"Points: {len(data)}")
lats = [p['lat'] for p in data]
lons = [p['lon'] for p in data]
heights = [p['height'] for p in data]
accs = [p['sdn'] for p in data]
print(f"Lat range: {min(lats):.6f} to {max(lats):.6f}")
print(f"Lon range: {min(lons):.6f} to {max(lons):.6f}")
print(f"Height range: {min(heights):.1f} to {max(heights):.1f} m")
print(f"Mean horizontal accuracy: {sum(accs)/len(accs):.2f} m\n")

# Create Leaflet HTML
center_lat = sum(lats) / len(lats)
center_lon = sum(lons) / len(lons)

html = f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>GNSS Trajectory - CORS Corrected</title>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <style>
        body {{ margin: 0; padding: 0; }}
        #map {{ position: absolute; top: 0; bottom: 0; width: 100%; }}
        .info {{
            padding: 6px 8px;
            background: white;
            background: rgba(255,255,255,0.8);
            box-shadow: 0 0 15px rgba(0,0,0,0.2);
            border-radius: 5px;
        }}
        .legend {{
            background: white;
            padding: 10px;
            border-radius: 5px;
            box-shadow: 0 0 15px rgba(0,0,0,0.2);
        }}
        .legend i {{
            width: 18px;
            height: 18px;
            float: left;
            margin-right: 8px;
            opacity: 0.7;
        }}
    </style>
</head>
<body>
    <div id="map"></div>
    <script>
        // Initialize map
        var map = L.map('map').setView([{center_lat}, {center_lon}], 16);
        
        L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
            attribution: '&copy; OpenStreetMap contributors',
            maxZoom: 19
        }}).addTo(map);
        
        // Trajectory data
        var trajectory = {json.dumps(data)};
        
        // Create route line
        var latlngs = [];
        for (var i = 0; i < trajectory.length; i++) {{
            latlngs.push([trajectory[i].lat, trajectory[i].lon]);
        }}
        
        var polyline = L.polyline(latlngs, {{
            color: 'blue',
            weight: 2,
            opacity: 0.7
        }}).addTo(map);
        
        // Add individual points with popups
        for (var i = 0; i < trajectory.length; i++) {{
            var point = trajectory[i];
            var color = point.sdn < 1.0 ? 'darkgreen' : 'orange';
            
            var popupText = '<b>Time:</b> ' + point.time + '<br>' +
                          '<b>Lat:</b> ' + point.lat.toFixed(6) + '<br>' +
                          '<b>Lon:</b> ' + point.lon.toFixed(6) + '<br>' +
                          '<b>Height:</b> ' + point.height.toFixed(1) + ' m<br>' +
                          '<b>Accuracy:</b> ' + point.sdn.toFixed(2) + ' m<br>' +
                          '<b>Satellites:</b> ' + point.ns;
            
            L.circleMarker([point.lat, point.lon], {{
                radius: 2,
                fillColor: color,
                color: color,
                weight: 0,
                opacity: 1,
                fillOpacity: 0.5
            }}).bindPopup(popupText).addTo(map);
        }}
        
        // Add start marker
        L.marker([trajectory[0].lat, trajectory[0].lon], {{
            icon: L.icon({{
                iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-green.png',
                shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/0.7.7/images/marker-shadow.png',
                iconSize: [25, 41],
                iconAnchor: [12, 41],
                popupAnchor: [1, -34],
                shadowSize: [41, 41]
            }})
        }}).bindPopup('<b>START</b><br>05:40:23.4').addTo(map);
        
        // Add end marker
        L.marker([trajectory[trajectory.length-1].lat, trajectory[trajectory.length-1].lon], {{
            icon: L.icon({{
                iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-red.png',
                shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/0.7.7/images/marker-shadow.png',
                iconSize: [25, 41],
                iconAnchor: [12, 41],
                popupAnchor: [1, -34],
                shadowSize: [41, 41]
            }})
        }}).bindPopup('<b>END</b><br>05:46:55.4').addTo(map);
        
        // Add legend
        var legend = L.control({{position: 'bottomright'}});
        legend.onAdd = function(map) {{
            var div = L.DomUtil.create('div', 'info legend');
            div.innerHTML = '<h4 style="margin: 0 0 10px 0;">Trajectory Info</h4>' +
                           '<p style="margin: 5px 0;">📍 Green points: &lt; 1.0 m error</p>' +
                           '<p style="margin: 5px 0;">📍 Orange points: ≥ 1.0 m error</p>' +
                           '<p style="margin: 5px 0;">🟢 = Start (05:40:23)</p>' +
                           '<p style="margin: 5px 0;">🔴 = End (05:46:55)</p>' +
                           '<p style="margin: 10px 0 0 0; font-size: 11px; color: #666;">Quality: Q=4 (DGPS)</p>';
            return div;
        }};
        legend.addTo(map);
    </script>
</body>
</html>
'''

# Save HTML
with open('trajectory_map.html', 'w') as f:
    f.write(html)

print("✓ Interactive map saved to: trajectory_map.html")
print("  Opening in browser...\n")

# Open in browser
webbrowser.open('file://' + os.path.realpath('trajectory_map.html'))

# Export to simple CSV
print("✓ CSV export:")
print("\ntime,latitude,longitude,elevation_m,accuracy_m,satellites")
for point in data[:5]:
    print(f"{point['time']},{point['lat']:.6f},{point['lon']:.6f},{point['height']:.1f},{point['sdn']:.2f},{point['ns']}")
print(f"... ({len(data)-5} more points)")

# Save CSV
with open('trajectory_corrected.csv', 'w') as f:
    f.write("time,latitude,longitude,elevation_m,accuracy_m,satellites\n")
    for point in data:
        f.write(f"{point['time']},{point['lat']:.6f},{point['lon']:.6f},{point['height']:.1f},{point['sdn']:.2f},{point['ns']}\n")

print("\n✓ CSV file saved to: trajectory_corrected.csv")
