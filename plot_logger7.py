"""
plot_logger7.py - Plot raw and NMEA-filtered trajectory for logger/7 (Samsung A35)
Produces an interactive HTML map with two trajectory layers.
"""
import re
import os
import math
from collections import defaultdict

# ─── CONFIG ─────────────────────────────────────────────────────────────────
NMEA_FILE = r"c:\Users\Guntesh\Desktop\foo\gsd\logger\7\gnss_log_2026_04_07_16_58_09.nmea"
OUT_HTML   = r"c:\Users\Guntesh\Desktop\foo\gsd\out\logger7_trajectory.html"

# NMEA quality filter thresholds
MIN_SNR_DB  = 25      # minimum dBHz for a satellite to be considered "good"
MIN_GOOD_SATS = 6     # epoch must have at least this many good-SNR sats
MAX_HDOP    = 1.5     # maximum HDOP to accept epoch
MIN_FIX_QUALITY = 1   # GGA fix quality (1=GPS, 2=DGPS, 4=RTK fixed, 5=RTK float)
# ─────────────────────────────────────────────────────────────────────────────


def nmea_lat_lon(lat_str, lat_hem, lon_str, lon_hem):
    """Convert NMEA DDDMM.MMMM to decimal degrees."""
    lat_deg = float(lat_str[:2])
    lat_min = float(lat_str[2:])
    lat = lat_deg + lat_min / 60.0
    if lat_hem == 'S':
        lat = -lat

    lon_deg = float(lon_str[:3])
    lon_min = float(lon_str[3:])
    lon = lon_deg + lon_min / 60.0
    if lon_hem == 'W':
        lon = -lon

    return lat, lon


def parse_nmea(filepath):
    """
    Parse NMEA file and return:
      raw_track    : list of (lat, lon) from all valid GGA fixes
      filtered_track: list of (lat, lon) after SNR + HDOP gating
    """
    # Build per-epoch SNR map from GSV sentences
    # Key: epoch_ts (milliseconds from last field), Value: list of SNR values
    epoch_snr = defaultdict(list)      # ts -> [snr1, snr2, ...]
    epoch_hdop = {}                    # ts -> hdop
    epoch_pos = {}                     # ts -> (lat, lon)
    epoch_fix_quality = {}             # ts -> fix_quality

    with open(filepath, 'r', encoding='ascii', errors='replace') as f:
        for line in f:
            line = line.strip()
            if not line.startswith('NMEA,'):
                continue

            # Last field is the timestamp
            parts = line.split(',')
            try:
                ts = int(parts[-1].split('*')[0]) if '*' in parts[-1] else int(parts[-1])
            except ValueError:
                continue

            # Strip the leading "NMEA," to get the actual sentence
            sentence = line[5:]  # remove "NMEA,"

            # GGA: position + fix quality
            if '$GPGGA' in sentence or '$GNGGA' in sentence:
                # $GPGGA,hhmmss.ss,lat,N,lon,E,quality,numSV,HDOP,alt,...
                m = re.search(
                    r'\$G.GGA,[\d.]+,(\d{4,}\.[\d]+),([NS]),([\d]+\.[\d]+),([EW]),(\d),(\d+),([\d.]+)',
                    sentence
                )
                if m:
                    lat, lon = nmea_lat_lon(m.group(1), m.group(2), m.group(3), m.group(4))
                    fix_quality = int(m.group(5))
                    hdop = float(m.group(7))
                    epoch_pos[ts] = (lat, lon)
                    epoch_hdop[ts] = hdop
                    epoch_fix_quality[ts] = fix_quality

            # GSV: satellite SNR values (any constellation prefix)
            # $G?GSV,numMsg,msgNum,numSV,[sv,elev,az,snr,]+
            elif 'GSV' in sentence:
                # Extract all SNR values from groups of 4 fields after sv count
                gsv_match = re.search(r'\$G.GSV,\d+,\d+,\d+((?:,\d*,\d*,\d*,\d*)+)', sentence.split('*')[0])
                if gsv_match:
                    sat_fields = gsv_match.group(1).strip(',').split(',')
                    # Each satellite: prn, elev, azim, snr (groups of 4)
                    for i in range(0, len(sat_fields) - 3, 4):
                        snr_str = sat_fields[i + 3] if i + 3 < len(sat_fields) else ''
                        if snr_str.isdigit() and int(snr_str) > 0:
                            epoch_snr[ts].append(int(snr_str))

    # Build trajectories
    raw_track = []
    filtered_track = []

    for ts in sorted(epoch_pos.keys()):
        lat, lon = epoch_pos[ts]
        fix_q = epoch_fix_quality.get(ts, 0)
        hdop  = epoch_hdop.get(ts, 99.0)
        snrs  = epoch_snr.get(ts, [])
        good_sats = sum(1 for s in snrs if s >= MIN_SNR_DB)

        # Raw: only require a valid fix (quality >= 1)
        if fix_q >= MIN_FIX_QUALITY and 17.0 <= lat <= 20.0 and 77.0 <= lon <= 82.0:
            raw_track.append((lat, lon))

        # Filtered: SNR + HDOP gating
        if (fix_q >= MIN_FIX_QUALITY
                and hdop <= MAX_HDOP
                and good_sats >= MIN_GOOD_SATS
                and 17.0 <= lat <= 20.0
                and 77.0 <= lon <= 82.0):
            filtered_track.append((lat, lon))

    return raw_track, filtered_track


def haversine_m(p1, p2):
    R = 6371000
    lat1, lon1 = math.radians(p1[0]), math.radians(p1[1])
    lat2, lon2 = math.radians(p2[0]), math.radians(p2[1])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2
    return R * 2 * math.asin(math.sqrt(a))


def track_length_m(track):
    total = 0.0
    for i in range(1, len(track)):
        total += haversine_m(track[i-1], track[i])
    return total


def make_html(raw_track, filtered_track, out_path):
    """Generate a Leaflet HTML map with two trajectory layers."""
    if not raw_track:
        print("ERROR: No raw track points — check NMEA parsing.")
        return

    # Center map
    clat = sum(p[0] for p in raw_track) / len(raw_track)
    clon = sum(p[1] for p in raw_track) / len(raw_track)

    def js_coords(track):
        return '[' + ','.join(f'[{p[0]:.7f},{p[1]:.7f}]' for p in track) + ']'

    raw_js  = js_coords(raw_track)
    filt_js = js_coords(filtered_track) if filtered_track else '[]'

    raw_len  = track_length_m(raw_track)
    filt_len = track_length_m(filtered_track) if filtered_track else 0

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Logger/7 Trajectory — Samsung A35 (Carrier Phase)</title>
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <style>
    * {{ margin:0; padding:0; box-sizing:border-box; }}
    body {{ font-family: 'Segoe UI', sans-serif; background:#0f1117; color:#eee; }}
    #map {{ width:100vw; height:100vh; }}
    #panel {{
      position:fixed; top:16px; left:50%; transform:translateX(-50%);
      background:rgba(15,17,23,0.92); border:1px solid #333;
      border-radius:12px; padding:14px 20px; z-index:1000;
      backdrop-filter:blur(8px); min-width:420px; text-align:center;
    }}
    #panel h2 {{ font-size:14px; font-weight:600; color:#7dd3fc; margin-bottom:10px; letter-spacing:.5px; }}
    .legend {{ display:flex; gap:16px; justify-content:center; flex-wrap:wrap; }}
    .legend-item {{ display:flex; align-items:center; gap:6px; font-size:12px; }}
    .dot {{ width:12px; height:12px; border-radius:50%; display:inline-block; }}
    .stats {{ display:flex; gap:20px; justify-content:center; margin-top:10px; font-size:11px; color:#94a3b8; }}
    .stat {{ text-align:center; }}
    .stat span {{ display:block; font-size:14px; font-weight:700; color:#e2e8f0; }}
    #toggle-panel {{
      position:fixed; bottom:16px; right:16px;
      background:rgba(15,17,23,0.9); border:1px solid #333;
      border-radius:10px; padding:10px 14px; z-index:1000;
      font-size:12px;
    }}
    .toggle-btn {{
      display:flex; align-items:center; gap:8px; cursor:pointer;
      margin:4px 0; padding:4px 8px; border-radius:6px;
      transition:background .2s;
    }}
    .toggle-btn:hover {{ background:rgba(255,255,255,0.07); }}
    .toggle-btn input {{ cursor:pointer; }}
  </style>
</head>
<body>
  <div id="map"></div>
  <div id="panel">
    <h2>📍 LOGGER/7 — Samsung A35 | Carrier Phase Data | April 7, 2026</h2>
    <div class="legend">
      <div class="legend-item"><div class="dot" style="background:#f97316"></div> Raw GGA ({len(raw_track)} pts)</div>
      <div class="legend-item"><div class="dot" style="background:#22d3ee"></div> NMEA Filtered — SNR≥{MIN_SNR_DB}dB, HDOP≤{MAX_HDOP} ({len(filtered_track)} pts)</div>
    </div>
    <div class="stats">
      <div class="stat">Raw Length<span>{raw_len:.0f} m</span></div>
      <div class="stat">Filtered Length<span>{filt_len:.0f} m</span></div>
      <div class="stat">Filtered Points<span>{len(filtered_track)}/{len(raw_track)}</span></div>
      <div class="stat">Start (UTC)<span>11:28:27</span></div>
    </div>
  </div>
  <div id="toggle-panel">
    <div class="toggle-btn"><input type="checkbox" id="cb-raw" checked onchange="toggleLayer('raw', this.checked)"> Raw trajectory</div>
    <div class="toggle-btn"><input type="checkbox" id="cb-filt" checked onchange="toggleLayer('filt', this.checked)"> NMEA filtered</div>
  </div>

  <script>
    var map = L.map('map', {{zoomControl: true}}).setView([{clat:.6f}, {clon:.6f}], 17);

    L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
      attribution: '© OpenStreetMap contributors',
      maxZoom: 21
    }}).addTo(map);

    // Satellite tiles option
    var sat = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{{z}}/{{y}}/{{x}}', {{
      attribution: 'Tiles &copy; Esri', maxZoom: 21
    }});

    var rawCoords = {raw_js};
    var filtCoords = {filt_js};

    var rawLine = L.polyline(rawCoords, {{
      color: '#f97316', weight: 2.5, opacity: 0.75
    }}).addTo(map);

    var filtLine = L.polyline(filtCoords, {{
      color: '#22d3ee', weight: 3, opacity: 0.9
    }}).addTo(map);

    // Start/end markers
    function circleMarker(latlng, color, label) {{
      return L.circleMarker(latlng, {{
        radius:7, fillColor:color, color:'#fff',
        weight:2, fillOpacity:1
      }}).bindPopup(label);
    }}

    if (rawCoords.length > 0) {{
      circleMarker(rawCoords[0], '#22c55e', 'Start').addTo(map);
      circleMarker(rawCoords[rawCoords.length-1], '#ef4444', 'End').addTo(map);
    }}

    var layers = {{ raw: rawLine, filt: filtLine }};
    function toggleLayer(name, show) {{
      if (show) map.addLayer(layers[name]);
      else map.removeLayer(layers[name]);
    }}

    // Layer control
    L.control.layers({{'OpenStreetMap': L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{maxZoom:21}}).addTo(map), 'Satellite': sat}}).addTo(map);

    map.fitBounds(rawLine.getBounds(), {{padding: [40, 40]}});
  </script>
</body>
</html>"""

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"Saved: {out_path}")


if __name__ == '__main__':
    print("Parsing NMEA...")
    raw, filtered = parse_nmea(NMEA_FILE)
    print(f"Raw points    : {len(raw)}")
    print(f"Filtered points: {len(filtered)}")
    if raw:
        print(f"Start: {raw[0]}")
        print(f"End  : {raw[-1]}")
    make_html(raw, filtered, OUT_HTML)
    print("Done. Open the HTML file in a browser.")
