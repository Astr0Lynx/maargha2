"""
plot_logger8_comparison.py
==========================
Generate a single interactive Leaflet map comparing 6 trajectories from the
Logger/8 simultaneous walk session (April 11, 2026):

  Device A — OnePlus 11R (code-only, no carrier phase)
    1. Raw GGA
    2. NMEA-filtered (SNR/HDOP gating)
    3. CORS-corrected on raw RINEX (Order 8, HYDE101G00)

  Device B — Samsung A35 (carrier phase capable)
    4. Raw GGA
    5. NMEA-filtered (SNR/HDOP gating)
    6. CORS-corrected on raw RINEX (Order 8, HYDE101G00)

Usage:
    python plot_logger8_comparison.py

Outputs:
    out/logger8_comparison_6traj.html
"""

import os
import re
import math
import subprocess
import json
from collections import defaultdict

# ─── CONFIG ─────────────────────────────────────────────────────────────────
WORKDIR = r"C:\Users\Guntesh\Desktop\foo\gsd"

ONEPLUS_NMEA  = r"logger\8_OnePlus\gnss_log_2026_04_11_11_40_31.nmea"
SAMSUNG_NMEA  = r"logger\8_Samsung\gnss_log_2026_04_11_11_40_39.nmea"

ONEPLUS_RINEX = r"logger\8_OnePlus\gnss_log_2026_04_11_11_40_31.26o"
SAMSUNG_RINEX = r"logger\8_Samsung\gnss_log_2026_04_11_11_40_39.26o"

CORS_OBS    = r"cors\Order8\HYDE101G00.26o"
CORS_NAV_N  = r"cors\Order8\HYDE101G00.26n"
CORS_NAV_G  = r"cors\Order8\HYDE101G00.26g"
CORS_NAV_L  = r"cors\Order8\HYDE101G00.26l"
CORS_NAV_C  = r"cors\Order8\HYDE101G00.26c"
CORS_NAV_J  = r"cors\Order8\HYDE101G00.26j"

OUT_DIR     = r"out"
POS_ONEPLUS = r"out\logger8_oneplus_cors.pos"
POS_SAMSUNG = r"out\logger8_samsung_cors.pos"
OUT_HTML    = r"out\logger8_comparison_6traj.html"

RTKLIB_EXE  = r"C:\tools\RTKLIB_EX_2.5.0\rnx2rtkp.exe"

# NMEA quality filter thresholds
MIN_SNR_DB    = 25    # dBHz
MIN_GOOD_SATS = 4     # epochs must have this many good-SNR sats
MAX_HDOP      = 2.0   # max HDOP
MIN_FIX_QUAL  = 1     # GGA quality indicator

# Geographic bounding box (Hyderabad area)
LAT_MIN, LAT_MAX = 17.0, 19.0
LON_MIN, LON_MAX = 77.0, 82.0
# ─────────────────────────────────────────────────────────────────────────────


def nmea_lat_lon(lat_str, lat_hem, lon_str, lon_hem):
    """Convert NMEA DDDMM.MMMM(MM) to decimal degrees."""
    lat_deg = int(float(lat_str) / 100)
    lat_min = float(lat_str) - lat_deg * 100
    lat = lat_deg + lat_min / 60.0
    if lat_hem.upper() == 'S':
        lat = -lat

    lon_deg = int(float(lon_str) / 100)
    lon_min = float(lon_str) - lon_deg * 100
    lon = lon_deg + lon_min / 60.0
    if lon_hem.upper() == 'W':
        lon = -lon

    return lat, lon


def parse_nmea_file(filepath):
    """
    Parse an Android GnssLogger NMEA file.
    Returns (raw_track, filtered_track) as lists of (lat, lon).
    Handles both OnePlus (GNGGA, ms-precision timestamps) and
    Samsung (GPGGA, 1-second timestamps) formats.

    SNR matching is done per UTC second (bucket), not exact ms,
    because Android may output GSV and GGA at slightly different timestamps.
    """
    # Key: unix_second (int) -> list of SNR values
    sec_snr  = defaultdict(list)
    # Key: unix_second -> (lat, lon, hdop, fix_q)
    sec_gga  = {}

    with open(filepath, 'r', encoding='ascii', errors='replace') as f:
        for line in f:
            line = line.strip()
            if not line.startswith('NMEA,'):
                continue

            parts = line.split(',')
            try:
                last   = parts[-1]
                ts_str = last.split('*')[0].strip()
                ts_ms  = int(ts_str)
                ts_sec = ts_ms // 1000   # bucket to the second
            except (ValueError, IndexError):
                continue

            # ---- GGA: position + fix quality ----
            gga_match = re.search(
                r'\$G.GGA,[\d.]+,([\d.]+),([NS]),([\d.]+),([EW]),(\d),\d+,([\d.]+)',
                line
            )
            if gga_match:
                try:
                    lat, lon = nmea_lat_lon(
                        gga_match.group(1), gga_match.group(2),
                        gga_match.group(3), gga_match.group(4)
                    )
                    fix_q = int(gga_match.group(5))
                    hdop  = float(gga_match.group(6))
                    if (LAT_MIN <= lat <= LAT_MAX and
                            LON_MIN <= lon <= LON_MAX and
                            fix_q >= MIN_FIX_QUAL):
                        # Keep best fix per second (favour highest fix_q)
                        if ts_sec not in sec_gga or fix_q > sec_gga[ts_sec][3]:
                            sec_gga[ts_sec] = (lat, lon, hdop, fix_q)
                except Exception:
                    pass

            # ---- GSV: satellite SNR ----
            elif 'GSV' in line:
                gsv_m = re.search(
                    r'\$G.GSV,\d+,\d+,\d+((?:,\d*,\d*,\d*,\d*)+)',
                    line.split('*')[0]
                )
                if gsv_m:
                    sat_fields = gsv_m.group(1).strip(',').split(',')
                    for i in range(0, len(sat_fields) - 3, 4):
                        snr_s = sat_fields[i + 3] if i + 3 < len(sat_fields) else ''
                        if snr_s.isdigit() and int(snr_s) > 0:
                            sec_snr[ts_sec].append(int(snr_s))

    raw_track      = []
    filtered_track = []

    for sec in sorted(sec_gga.keys()):
        lat, lon, hdop, fix_q = sec_gga[sec]

        # Look for SNR data in this second or adjacent second
        snrs = (sec_snr.get(sec, []) or
                sec_snr.get(sec - 1, []) or
                sec_snr.get(sec + 1, []))
        good_sats = sum(1 for s in snrs if s >= MIN_SNR_DB)

        raw_track.append((lat, lon))

        if hdop <= MAX_HDOP and good_sats >= MIN_GOOD_SATS:
            filtered_track.append((lat, lon))

    return raw_track, filtered_track



def run_rtklib(rover_rinex, out_pos):
    """Run rnx2rtkp DGPS positioning and return (returncode, output)."""
    base_files = [CORS_OBS, CORS_NAV_N, CORS_NAV_G, CORS_NAV_L, CORS_NAV_C, CORS_NAV_J]
    cmd = [
        RTKLIB_EXE,
        "-p", "2",           # DGPS
        "-f", "1",           # L1 only
        "-sys", "G,R,E,C,J",
        "-m", "10",          # 10° elevation mask
        "-o", out_pos,
        rover_rinex,
    ] + base_files
    print(f"  Running: rnx2rtkp {os.path.basename(rover_rinex)} ...")
    try:
        result = subprocess.run(
            cmd, cwd=WORKDIR,
            capture_output=True, text=True, timeout=300
        )
        out = (result.stdout or "")[-2000:] + (result.stderr or "")[-2000:]
        return result.returncode, out
    except Exception as e:
        return -1, str(e)


def parse_pos_file(path, max_q=4):
    """
    Parse RTKLIB .pos file.
    
    File format (GPS week+SOW):
      col[0]=week, col[1]=SOW, col[2]=lat, col[3]=lon, col[4]=h,
      col[5]=Q, col[6]=ns, col[7]=sdn, col[8]=sde ...
    
    File format (datetime):
      col[0]=YYYY/MM/DD, col[1]=HH:MM:SS.ss, col[2]=lat, col[3]=lon,
      col[4]=h, col[5]=Q, col[6]=ns ...
    
    Q values: 1=fixed, 2=float, 3=SBAS, 4=DGPS, 5=single, 6=PPP
    max_q: only include solutions with Q <= max_q (lower = better)
    """
    points = []
    if not os.path.exists(path):
        print(f"  WARNING: pos file not found: {path}")
        return points

    n_total = 0
    n_kept  = 0
    q_counter = {}

    with open(path, 'r', errors='ignore') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('%') or line.startswith('#'):
                continue
            p = line.split()
            n_total += 1

            try:
                if '/' in p[0]:
                    # Datetime format: YYYY/MM/DD HH:MM:SS lat lon h Q ns ...
                    lat = float(p[2])
                    lon = float(p[3])
                    q   = int(p[5])
                else:
                    # GPS week SOW format: week SOW lat lon h Q ns ...
                    lat = float(p[2])
                    lon = float(p[3])
                    q   = int(p[5])

                q_counter[q] = q_counter.get(q, 0) + 1

                # Quality filter: only keep Q <= max_q
                if q > max_q:
                    continue

                if LAT_MIN <= lat <= LAT_MAX and LON_MIN <= lon <= LON_MAX:
                    points.append((lat, lon))
                    n_kept += 1
            except Exception:
                continue

    q_labels = {1:'FIX',2:'FLOAT',3:'SBAS',4:'DGPS',5:'SINGLE',6:'PPP'}
    q_str = ', '.join(f'Q={k}({q_labels.get(k,"?")}):{v}' for k,v in sorted(q_counter.items()))
    print(f"    Pos file: {n_total} total, kept {n_kept} (Q<={max_q}) | {q_str}")
    return points


def haversine_m(p1, p2):
    """Distance in metres between two (lat, lon) points."""
    R = 6371000
    lat1 = math.radians(p1[0]); lon1 = math.radians(p1[1])
    lat2 = math.radians(p2[0]); lon2 = math.radians(p2[1])
    dlat = lat2 - lat1; dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2
    return R * 2 * math.asin(math.sqrt(min(1.0, a)))


def track_length_m(track):
    """Total path length in metres."""
    if len(track) < 2:
        return 0.0
    return sum(haversine_m(track[i-1], track[i]) for i in range(1, len(track)))


def js_coords(track):
    """Convert track to JS polyline array string."""
    return '[' + ','.join(f'[{p[0]:.7f},{p[1]:.7f}]' for p in track) + ']'


def make_html(layers, out_path):
    """
    Generate an interactive Leaflet HTML map with multiple trajectory layers.
    layers: list of dicts with keys: label, color, dash, weight, opacity, coords
    """
    all_lats = [p[0] for ly in layers for p in ly['coords']]
    all_lons = [p[1] for ly in layers for p in ly['coords']]

    if not all_lats:
        print("ERROR: No coordinates in any layer!")
        return

    clat = sum(all_lats) / len(all_lats)
    clon = sum(all_lons) / len(all_lons)
    bounds = [
        [min(all_lats) - 0.001, min(all_lons) - 0.001],
        [max(all_lats) + 0.001, max(all_lons) + 0.001]
    ]

    # Build layer JS
    layer_defs = []
    layer_adds = []
    legend_items = []
    overlay_entries = []

    for i, ly in enumerate(layers):
        var   = f"lyr{i}"
        color = ly['color']
        dash  = ly.get('dash', '')
        wt    = ly.get('weight', 2.5)
        op    = ly.get('opacity', 0.85)
        label = ly['label']
        coords_js = js_coords(ly['coords'])
        n_pts = len(ly['coords'])
        dist  = track_length_m(ly['coords'])

        layer_defs.append(f"""
var {var} = L.polyline({coords_js}, {{
  color: '{color}', weight: {wt}, opacity: {op},
  dashArray: '{dash}'
}}).bindTooltip('{label} ({n_pts} pts, {dist:.0f}m)', {{sticky: true}});""")

        layer_adds.append(f"{var}.addTo(map);")
        overlay_entries.append(f"    '{label}': {var},")

        dot_style = f"background:{color};" if not dash else f"border-top:3px dashed {color};background:transparent;height:3px;"
        legend_items.append(f"""
        <div class="leg-item">
          <div class="leg-swatch" style="{dot_style}"></div>
          <div class="leg-text">
            <span class="leg-label">{label}</span>
            <span class="leg-stat">{n_pts} pts · {dist:.0f} m</span>
          </div>
        </div>""")

    layer_js_block  = "\n".join(layer_defs)
    layer_add_block = "\n".join(layer_adds)
    overlay_block   = "\n".join(overlay_entries)
    legend_block    = "\n".join(legend_items)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Logger/8 — OnePlus vs Samsung vs CORS | April 11, 2026</title>
  <meta name="description" content="Comparative GNSS trajectory map: OnePlus 11R (code-only) vs Samsung A35 (carrier phase) with CORS Order8 correction, Logger/8 session.">
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: 'Inter', system-ui, sans-serif;
      background: #0a0e1a;
      color: #e2e8f0;
    }}
    #map {{ width: 100vw; height: 100vh; }}

    /* ── Header panel ── */
    #header {{
      position: fixed; top: 0; left: 0; right: 0; z-index: 1200;
      background: linear-gradient(135deg, rgba(10,14,26,0.97) 0%, rgba(17,24,39,0.97) 100%);
      border-bottom: 1px solid rgba(99,179,237,0.2);
      backdrop-filter: blur(12px);
      padding: 10px 20px;
      display: flex; align-items: center; gap: 16px;
      box-shadow: 0 4px 20px rgba(0,0,0,0.5);
    }}
    #header h1 {{
      font-size: 13px; font-weight: 700; color: #7dd3fc; letter-spacing: 0.5px;
      text-transform: uppercase; white-space: nowrap;
    }}
    #header .subtitle {{
      font-size: 11px; color: #94a3b8; white-space: nowrap;
    }}
    #header .sep {{ width: 1px; height: 28px; background: rgba(255,255,255,0.1); }}

    /* ── Legend panel ── */
    #legend {{
      position: fixed; bottom: 20px; left: 16px; z-index: 1200;
      background: rgba(10,14,26,0.95);
      border: 1px solid rgba(99,179,237,0.2);
      border-radius: 12px;
      padding: 14px 16px;
      backdrop-filter: blur(12px);
      box-shadow: 0 8px 32px rgba(0,0,0,0.5);
      min-width: 220px;
    }}
    #legend h2 {{
      font-size: 11px; font-weight: 700; color: #7dd3fc;
      text-transform: uppercase; letter-spacing: 0.8px;
      margin-bottom: 10px; padding-bottom: 8px;
      border-bottom: 1px solid rgba(255,255,255,0.08);
    }}
    .device-group {{ margin-bottom: 10px; }}
    .device-title {{
      font-size: 10px; font-weight: 600; color: #94a3b8;
      text-transform: uppercase; letter-spacing: 0.5px;
      margin-bottom: 6px;
    }}
    .leg-item {{
      display: flex; align-items: center; gap: 8px;
      margin: 4px 0; cursor: pointer;
      border-radius: 6px; padding: 3px 4px;
      transition: background 0.2s;
    }}
    .leg-item:hover {{ background: rgba(255,255,255,0.06); }}
    .leg-swatch {{
      width: 24px; height: 4px; border-radius: 2px; flex-shrink: 0;
    }}
    .leg-text {{ display: flex; flex-direction: column; }}
    .leg-label {{ font-size: 11px; font-weight: 500; }}
    .leg-stat  {{ font-size: 10px; color: #64748b; margin-top: 1px; }}

    /* ── Stats bar ── */
    #stats {{
      position: fixed; top: 64px; left: 50%; transform: translateX(-50%);
      z-index: 1100;
      display: flex; gap: 8px; flex-wrap: wrap; justify-content: center;
    }}
    .stat-chip {{
      background: rgba(10,14,26,0.92);
      border: 1px solid rgba(99,179,237,0.15);
      border-radius: 20px;
      padding: 4px 12px;
      font-size: 10px; color: #94a3b8;
      backdrop-filter: blur(8px);
      white-space: nowrap;
    }}
    .stat-chip strong {{ color: #e2e8f0; }}
  </style>
</head>
<body>
  <div id="map"></div>

  <div id="header">
    <div>
      <div id="header" style="position:static;border:none;background:none;box-shadow:none;padding:0;display:block;">
        <h1>📡 Logger/8 — Device Comparison</h1>
        <div class="subtitle">OnePlus 11R (Code-Only) · Samsung A35 (Carrier Phase) · CORS Order 8 — April 11, 2026</div>
      </div>
    </div>
  </div>

  <div id="legend">
    <h2>🗂 Trajectories</h2>

    <div class="device-group">
      <div class="device-title">📱 OnePlus 11R (Code-Only)</div>
      {chr(10).join(legend_items[:3])}
    </div>

    <div class="device-group">
      <div class="device-title">📱 Samsung A35 (Carrier Phase)</div>
      {chr(10).join(legend_items[3:])}
    </div>

    <div style="margin-top:10px;font-size:9px;color:#475569;border-top:1px solid rgba(255,255,255,0.06);padding-top:8px;">
      Click layer control (top-right) to toggle individual trajectories.<br>
      CORS: HYDE101G00 Order 8 reference station.
    </div>
  </div>

  <script>
    var map = L.map('map', {{
      zoomControl: true,
      preferCanvas: true
    }}).setView([{clat:.6f}, {clon:.6f}], 17);

    // Base layers
    var osm = L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
      attribution: '© OpenStreetMap contributors', maxZoom: 21
    }}).addTo(map);

    var sat = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{{z}}/{{y}}/{{x}}', {{
      attribution: 'Tiles © Esri', maxZoom: 21
    }});

    var baseMaps = {{'OpenStreetMap': osm, 'Satellite': sat}};

    // ── Trajectory layers ──
    {layer_js_block}

    // Add all to map
    {layer_add_block}

    // Start / End markers for first raw track (OnePlus)
    function circleMarker(latlng, color, label) {{
      return L.circleMarker(latlng, {{
        radius: 7, fillColor: color, color: '#fff',
        weight: 2, fillOpacity: 1
      }}).bindPopup('<b>' + label + '</b>');
    }}

    var lyr0coords = {js_coords(layers[0]['coords']) if layers[0]['coords'] else '[]'};
    if (lyr0coords.length > 0) {{
      circleMarker(lyr0coords[0], '#22c55e', 'Walk Start').addTo(map);
      circleMarker(lyr0coords[lyr0coords.length - 1], '#ef4444', 'Walk End').addTo(map);
    }}

    // Fit map bounds
    map.fitBounds({json.dumps(bounds)}, {{padding: [60, 60]}});

    // Layer control
    var overlayMaps = {{
{overlay_block}
    }};
    L.control.layers(baseMaps, overlayMaps, {{collapsed: false, position: 'topright'}}).addTo(map);
  </script>
</body>
</html>"""

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"  OK Saved: {out_path}")


def main():
    os.chdir(WORKDIR)
    os.makedirs(OUT_DIR, exist_ok=True)

    print("=" * 65)
    print("MAARGHA Logger/8 — 6-Trajectory Comparison (OnePlus vs Samsung)")
    print("=" * 65)

    # ──────────────────────────────────────────────────
    # 1. Parse NMEA for both devices
    # ──────────────────────────────────────────────────
    print("\n[1/3] Parsing NMEA files ...")

    print("  Parsing OnePlus NMEA ...")
    op_raw, op_filt = parse_nmea_file(ONEPLUS_NMEA)
    print(f"    OnePlus  -> raw: {len(op_raw)} pts, filtered: {len(op_filt)} pts")

    print("  Parsing Samsung NMEA ...")
    sam_raw, sam_filt = parse_nmea_file(SAMSUNG_NMEA)
    print(f"    Samsung  -> raw: {len(sam_raw)} pts, filtered: {len(sam_filt)} pts")

    # ──────────────────────────────────────────────────
    # 2. Run RTKLIB DGPS for both devices
    # ──────────────────────────────────────────────────
    print("\n[2/3] Running RTKLIB DGPS corrections ...")

    if not os.path.exists(POS_ONEPLUS):
        rc, out = run_rtklib(ONEPLUS_RINEX, POS_ONEPLUS)
        if rc != 0:
            print(f"    WARNING: rnx2rtkp exited {rc} for OnePlus")
            print("    Output:", out[-500:])
        else:
            print(f"    OK OnePlus CORS pos file written: {POS_ONEPLUS}")
    else:
        print(f"    OK OnePlus CORS pos already exists, skipping RTKLIB")

    if not os.path.exists(POS_SAMSUNG):
        rc, out = run_rtklib(SAMSUNG_RINEX, POS_SAMSUNG)
        if rc != 0:
            print(f"    WARNING: rnx2rtkp exited {rc} for Samsung")
            print("    Output:", out[-500:])
        else:
            print(f"    OK Samsung CORS pos file written: {POS_SAMSUNG}")
    else:
        print(f"    OK Samsung CORS pos already exists, skipping RTKLIB")

    op_cors  = parse_pos_file(POS_ONEPLUS)
    sam_cors = parse_pos_file(POS_SAMSUNG)
    print(f"    OnePlus  CORS: {len(op_cors)} pts")
    print(f"    Samsung  CORS: {len(sam_cors)} pts")

    # ──────────────────────────────────────────────────
    # 3. Build HTML map
    # ──────────────────────────────────────────────────
    print("\n[3/3] Generating HTML map ...")

    # Color palette
    # OnePlus: orange family   |  Samsung: blue family
    # Raw = faded, NMEA = vivid, CORS = bright contrasting
    layers = [
        {
            "label":   "OnePlus — Raw GGA",
            "color":   "#fb923c",   # amber-400
            "dash":    "6,4",
            "weight":  2.0,
            "opacity": 0.65,
            "coords":  op_raw,
        },
        {
            "label":   "OnePlus — NMEA Filtered",
            "color":   "#f97316",   # orange-500
            "dash":    "",
            "weight":  2.5,
            "opacity": 0.85,
            "coords":  op_filt,
        },
        {
            "label":   "OnePlus — CORS (Order 8)",
            "color":   "#fbbf24",   # amber-400
            "dash":    "",
            "weight":  3.5,
            "opacity": 0.95,
            "coords":  op_cors,
        },
        {
            "label":   "Samsung — Raw GGA",
            "color":   "#67e8f9",   # cyan-300
            "dash":    "6,4",
            "weight":  2.0,
            "opacity": 0.65,
            "coords":  sam_raw,
        },
        {
            "label":   "Samsung — NMEA Filtered",
            "color":   "#22d3ee",   # cyan-400
            "dash":    "",
            "weight":  2.5,
            "opacity": 0.85,
            "coords":  sam_filt,
        },
        {
            "label":   "Samsung — CORS (Order 8)",
            "color":   "#6366f1",   # indigo-500
            "dash":    "",
            "weight":  3.5,
            "opacity": 0.95,
            "coords":  sam_cors,
        },
    ]

    make_html(layers, OUT_HTML)

    print("\n" + "=" * 65)
    print("DONE!")
    print(f"  Map: {os.path.abspath(OUT_HTML)}")
    print("\nTrajectory summary:")
    for ly in layers:
        n = len(ly['coords'])
        d = track_length_m(ly['coords'])
        print(f"  {ly['label']:<35} {n:>4} pts  {d:>7.0f} m")
    print("=" * 65)


if __name__ == '__main__':
    main()
