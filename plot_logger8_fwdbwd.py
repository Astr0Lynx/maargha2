"""
plot_logger8_fwdbwd.py
======================
Runs RTKLIB with forward/backward combined Kalman smoothing (-c flag)
on both devices and plots all trajectories on ONE map:

  OnePlus 11R  (code-only / DGPS):
    - NMEA filtered            [orange, solid]
    - CORS DGPS  fwd/bwd       [gold,   solid, thick]

  Samsung A35  (carrier phase / RTK kinematic):
    - NMEA filtered            [cyan,   solid]
    - CORS RTK   fwd/bwd       [indigo, solid, thick]

Output: out/logger8_fwdbwd_combined.html
        out/logger8_oneplus_fwdbwd.pos
        out/logger8_samsung_fwdbwd.pos

What -c does in RTKLIB:
  1. Forward pass  : processes epochs t=0 -> t=end  (standard Kalman filter)
  2. Backward pass : processes epochs t=end -> t=0  (smoother / RTS)
  3. Combine       : merges fwd+bwd at each epoch, weighting by covariance
  Result: smooth, minimum-variance trajectory — no extra Gaussian needed.
"""

import os, re, math, subprocess, json
from collections import defaultdict

# ── Config ────────────────────────────────────────────────────────────────────
WORKDIR       = r"C:\Users\Guntesh\Desktop\foo\gsd"

ONEPLUS_NMEA  = r"logger\8_OnePlus\gnss_log_2026_04_11_11_40_31.nmea"
SAMSUNG_NMEA  = r"logger\8_Samsung\gnss_log_2026_04_11_11_40_39.nmea"
ONEPLUS_RINEX = r"logger\8_OnePlus\gnss_log_2026_04_11_11_40_31.26o"
SAMSUNG_RINEX = r"logger\8_Samsung\gnss_log_2026_04_11_11_40_39.26o"

CORS_OBS   = r"cors\Order8\HYDE101G00.26o"
CORS_NAV_N = r"cors\Order8\HYDE101G00.26n"
CORS_NAV_G = r"cors\Order8\HYDE101G00.26g"
CORS_NAV_L = r"cors\Order8\HYDE101G00.26l"
CORS_NAV_C = r"cors\Order8\HYDE101G00.26c"
CORS_NAV_J = r"cors\Order8\HYDE101G00.26j"

POS_ONEPLUS   = r"out\logger8_oneplus_fwdbwd.pos"
POS_SAMSUNG   = r"out\logger8_samsung_fwdbwd.pos"
OUT_HTML      = r"out\logger8_fwdbwd_combined.html"
RTKLIB_EXE    = r"C:\tools\RTKLIB_EX_2.5.0\rnx2rtkp.exe"

LAT_MIN, LAT_MAX = 17.0, 19.0
LON_MIN, LON_MAX = 77.0, 82.0
MIN_SNR_DB = 25; MIN_GOOD_SATS = 4; MAX_HDOP = 2.0; MIN_FIX_QUAL = 1
# ──────────────────────────────────────────────────────────────────────────────


# ── NMEA parser ───────────────────────────────────────────────────────────────
def nmea_ll(lat_s, lat_h, lon_s, lon_h):
    ld  = int(float(lat_s) / 100)
    lat = ld + (float(lat_s) - ld * 100) / 60.0
    if lat_h.upper() == 'S': lat = -lat
    lo  = int(float(lon_s) / 100)
    lon = lo + (float(lon_s) - lo * 100) / 60.0
    if lon_h.upper() == 'W': lon = -lon
    return lat, lon


def parse_nmea(fp):
    sec_snr = defaultdict(list)
    sec_gga = {}
    with open(fp, 'r', encoding='ascii', errors='replace') as f:
        for line in f:
            line = line.strip()
            if not line.startswith('NMEA,'): continue
            parts = line.split(',')
            try:
                ts  = int(parts[-1].split('*')[0])
                sec = ts // 1000
            except: continue

            m = re.search(
                r'\$G.GGA,[\d.]+,([\d.]+),([NS]),([\d.]+),([EW]),(\d),\d+,([\d.]+)',
                line)
            if m:
                try:
                    lat, lon = nmea_ll(m.group(1), m.group(2),
                                       m.group(3), m.group(4))
                    q    = int(m.group(5))
                    hdop = float(m.group(6))
                    if (LAT_MIN <= lat <= LAT_MAX and
                            LON_MIN <= lon <= LON_MAX and q >= MIN_FIX_QUAL):
                        if sec not in sec_gga or q > sec_gga[sec][3]:
                            sec_gga[sec] = (lat, lon, hdop, q)
                except: pass
            elif 'GSV' in line:
                gm = re.search(
                    r'\$G.GSV,\d+,\d+,\d+((?:,\d*,\d*,\d*,\d*)+)',
                    line.split('*')[0])
                if gm:
                    sf = gm.group(1).strip(',').split(',')
                    for i in range(0, len(sf) - 3, 4):
                        s = sf[i + 3] if i + 3 < len(sf) else ''
                        if s.isdigit() and int(s) > 0:
                            sec_snr[sec].append(int(s))

    filt = []
    for sec in sorted(sec_gga):
        lat, lon, hdop, _ = sec_gga[sec]
        snrs = (sec_snr.get(sec, []) or
                sec_snr.get(sec - 1, []) or
                sec_snr.get(sec + 1, []))
        gs = sum(1 for s in snrs if s >= MIN_SNR_DB)
        if hdop <= MAX_HDOP and gs >= MIN_GOOD_SATS:
            filt.append((lat, lon))
    return filt


# ── RTKLIB with -c flag ───────────────────────────────────────────────────────
def run_rtklib_fwdbwd(rover_rinex, out_pos, mode, label):
    """
    -c = forward/backward combined Kalman smoothing.
    Mode 1 = DGPS  (OnePlus, code-only).
    Mode 2 = kinematic RTK  (Samsung, carrier phase).
    """
    base = [CORS_OBS, CORS_NAV_N, CORS_NAV_G, CORS_NAV_L, CORS_NAV_C, CORS_NAV_J]
    cmd = [
        RTKLIB_EXE,
        "-p", str(mode),
        "-f", "1",             # L1 only
        "-sys", "G,R,E,C,J",
        "-m", "10",            # 10-deg elevation mask
        "-c",                  # <-- forward/backward combined Kalman smoother
        "-o", out_pos,
        rover_rinex,
    ] + base

    print("  Running RTKLIB [{} fwd/bwd combined, mode={}] ...".format(label, mode))
    try:
        r = subprocess.run(cmd, cwd=WORKDIR,
                           capture_output=True, text=True, timeout=600)
        # RTKLIB always exits non-zero when printing to stderr — check file instead
        if os.path.exists(out_pos) and os.path.getsize(out_pos) > 0:
            print("    OK -> {} ({} bytes)".format(out_pos, os.path.getsize(out_pos)))
        else:
            tail = ((r.stdout or '') + (r.stderr or ''))[-400:]
            print("    WARNING: pos file not written or empty. tail={}".format(tail))
        return r.returncode
    except Exception as e:
        print("    ERROR: {}".format(e))
        return -1


# ── .pos parser ───────────────────────────────────────────────────────────────
def parse_pos(path, max_q=4):
    """
    Columns: week  SOW  lat  lon  h  Q  ns  sdn  sde  sdu ...
              [0]  [1]  [2]  [3] [4] [5]
    Q: 1=FIX, 2=FLOAT, 3=SBAS, 4=DGPS, 5=SINGLE
    """
    pts = []; q_dist = {}
    if not os.path.exists(path):
        print("  WARNING: {} not found".format(path))
        return pts
    with open(path, 'r', errors='ignore') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('%'): continue
            p = line.split()
            try:
                lat = float(p[2]); lon = float(p[3]); q = int(p[5])
                q_dist[q] = q_dist.get(q, 0) + 1
                if q <= max_q and LAT_MIN <= lat <= LAT_MAX and LON_MIN <= lon <= LON_MAX:
                    pts.append((lat, lon))
            except: continue

    ql = {1:'FIX', 2:'FLOAT', 3:'SBAS', 4:'DGPS', 5:'SINGLE', 6:'PPP'}
    s  = '  |  '.join('Q{}({}): {}'.format(k, ql.get(k, '?'), v)
                      for k, v in sorted(q_dist.items()))
    print("    {} -> {} pts  [{}]".format(os.path.basename(path), len(pts), s))
    return pts


# ── Helpers ───────────────────────────────────────────────────────────────────
def hav(a, b):
    R = 6371000
    la1, lo1 = math.radians(a[0]), math.radians(a[1])
    la2, lo2 = math.radians(b[0]), math.radians(b[1])
    x = (math.sin((la2-la1)/2)**2 +
         math.cos(la1) * math.cos(la2) * math.sin((lo2-lo1)/2)**2)
    return R * 2 * math.asin(math.sqrt(min(1.0, x)))

def pdist(t):
    return sum(hav(t[i-1], t[i]) for i in range(1, len(t))) if len(t) > 1 else 0

def jc(t):
    return '[' + ','.join('[{:.7f},{:.7f}]'.format(p[0], p[1]) for p in t) + ']'

def step_stats(pts):
    if len(pts) < 2: return 'no data'
    steps = sorted(hav(pts[i-1], pts[i]) for i in range(1, len(pts)))
    n = len(steps)
    return 'median={:.2f}m  p90={:.2f}m  max={:.2f}m'.format(
        steps[n//2], steps[int(0.9*n)], steps[-1])


# ── HTML map ─────────────────────────────────────────────────────────────────
def make_html(op_nmea, op_cors,
              sam_nmea, sam_cors, out_path):

    all_lats = [p[0] for t in [op_nmea, sam_nmea] for p in t if t]
    all_lons = [p[1] for t in [op_nmea, sam_nmea] for p in t if t]
    clat = sum(all_lats) / len(all_lats)
    clon = sum(all_lons) / len(all_lons)
    bounds = [[min(all_lats)-0.001, min(all_lons)-0.001],
              [max(all_lats)+0.001, max(all_lons)+0.001]]

    def stat(t, lbl):
        return '{}: {} pts | {:.0f} m'.format(lbl, len(t), pdist(t))

    layers = [
        # OnePlus
        dict(var='lON', coords=op_nmea,
             color='#f97316', dash='',  weight=2.5, opacity=0.85,
             label='OnePlus — NMEA Filtered',
             tooltip=stat(op_nmea, 'OnePlus NMEA')),
        dict(var='lOC', coords=op_cors,
             color='#fbbf24', dash='',  weight=4.0, opacity=0.95,
             label='OnePlus — CORS DGPS (fwd/bwd)',
             tooltip=stat(op_cors, 'OnePlus CORS')),
        # Samsung
        dict(var='lSN', coords=sam_nmea,
             color='#22d3ee', dash='',  weight=2.5, opacity=0.85,
             label='Samsung — NMEA Filtered',
             tooltip=stat(sam_nmea, 'Samsung NMEA')),
        dict(var='lSC', coords=sam_cors,
             color='#818cf8', dash='',  weight=4.0, opacity=0.95,
             label='Samsung — CORS RTK (fwd/bwd)',
             tooltip=stat(sam_cors, 'Samsung CORS')),
    ]

    # JS for each polyline
    polyline_js   = ''
    layer_add_js  = ''
    overlay_js    = ''
    legend_html   = ''

    for ly in layers:
        v   = ly['var']
        col = ly['color']
        da  = ly['dash']
        wt  = ly['weight']
        op  = ly['opacity']
        lbl = ly['label']
        tip = ly['tooltip']
        cds = jc(ly['coords'])

        polyline_js += """
var {v} = L.polyline({cds}, {{
  color:'{col}', weight:{wt}, opacity:{op}, dashArray:'{da}'
}}).bindTooltip('{tip}', {{sticky:true}});
""".format(v=v, cds=cds, col=col, wt=wt, op=op, da=da, tip=tip)

        layer_add_js += "{}.addTo(map);\n".format(v)
        overlay_js   += "    '{}': {},\n".format(lbl, v)

        swatch = ('background:{};'.format(col) if not da
                  else 'border-top:3px dashed {};background:transparent;height:3px;'.format(col))
        legend_html += """
<div class="leg-item">
  <div class="leg-sw" style="{sw}"></div>
  <div>
    <div class="leg-lbl">{lbl}</div>
    <div class="leg-stat">{tip}</div>
  </div>
</div>""".format(sw=swatch, lbl=lbl, tip=tip)

    # start/end marker JS (use OnePlus NMEA as reference)
    ref = op_nmea
    start_end_js = ''
    if ref:
        start_end_js = """
L.circleMarker({ref0}, {{radius:8,fillColor:'#22c55e',color:'#fff',weight:2,fillOpacity:1}})
 .bindPopup('<b>Walk Start</b>').addTo(map);
L.circleMarker({refn}, {{radius:8,fillColor:'#ef4444',color:'#fff',weight:2,fillOpacity:1}})
 .bindPopup('<b>Walk End</b>').addTo(map);
""".format(ref0='[{:.7f},{:.7f}]'.format(*ref[0]),
           refn='[{:.7f},{:.7f}]'.format(*ref[-1]))

    html = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Logger/8 — Forward/Backward Kalman | OnePlus vs Samsung | April 11 2026</title>
  <meta name="description" content="RTKLIB fwd/bwd combined Kalman: OnePlus DGPS vs Samsung RTK, CORS Order 8, compared with NMEA filtered.">
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style>
    *,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
    body{{font-family:'Inter',system-ui,sans-serif;background:#0a0e1a;color:#e2e8f0}}
    #map{{width:100vw;height:100vh}}

    /* header */
    #hdr{{
      position:fixed;top:0;left:0;right:0;z-index:1200;
      background:linear-gradient(135deg,rgba(10,14,26,.97),rgba(17,24,39,.97));
      border-bottom:1px solid rgba(99,179,237,.2);
      backdrop-filter:blur(12px);
      padding:9px 20px;
      display:flex;align-items:center;gap:16px;
      box-shadow:0 4px 20px rgba(0,0,0,.5);
    }}
    #hdr h1{{font-size:13px;font-weight:700;color:#7dd3fc;
             text-transform:uppercase;letter-spacing:.5px;white-space:nowrap}}
    #hdr .sub{{font-size:10px;color:#94a3b8;margin-top:2px}}

    /* badge */
    .badge{{
      background:rgba(99,179,237,.12);border:1px solid rgba(99,179,237,.25);
      border-radius:12px;padding:3px 10px;font-size:10px;color:#7dd3fc;white-space:nowrap;
    }}

    /* legend */
    #legend{{
      position:fixed;bottom:16px;left:14px;z-index:1200;
      background:rgba(10,14,26,.95);
      border:1px solid rgba(99,179,237,.2);border-radius:12px;
      padding:12px 16px;backdrop-filter:blur(12px);
      box-shadow:0 8px 32px rgba(0,0,0,.5);min-width:240px;
    }}
    #legend h2{{font-size:10px;font-weight:700;color:#7dd3fc;
               text-transform:uppercase;letter-spacing:.8px;
               margin-bottom:10px;padding-bottom:8px;
               border-bottom:1px solid rgba(255,255,255,.08)}}
    .leg-item{{display:flex;align-items:center;gap:8px;margin:5px 0;
              border-radius:6px;padding:3px 4px;transition:background .2s;cursor:default}}
    .leg-item:hover{{background:rgba(255,255,255,.05)}}
    .leg-sw{{width:24px;height:4px;border-radius:2px;flex-shrink:0}}
    .leg-lbl{{font-size:11px;font-weight:500}}
    .leg-stat{{font-size:9.5px;color:#64748b;margin-top:1px}}

    /* device section dividers */
    .leg-divider{{font-size:9px;font-weight:600;color:#475569;
                 text-transform:uppercase;letter-spacing:.6px;
                 margin:8px 0 4px;padding-top:6px;
                 border-top:1px solid rgba(255,255,255,.06)}}

    /* note box */
    #note{{
      position:fixed;bottom:16px;right:14px;z-index:1200;
      background:rgba(10,14,26,.93);
      border:1px solid rgba(99,179,237,.15);border-radius:9px;
      padding:10px 13px;font-size:9.5px;color:#64748b;
      max-width:230px;line-height:1.6;backdrop-filter:blur(8px);
    }}
    #note strong{{color:#94a3b8;display:block;margin-bottom:4px;font-size:10px}}
  </style>
</head>
<body>
<div id="map"></div>

<div id="hdr">
  <div>
    <h1>Logger/8 — Forward/Backward Kalman Smoothing</h1>
    <div class="sub">OnePlus 11R (Code-Only / DGPS)  vs  Samsung A35 (Carrier Phase / RTK)  |  CORS Order 8 — April 11, 2026</div>
  </div>
  <div class="badge">RTKLIB -c combined</div>
  <div class="badge">NMEA vs CORS Fwd/Bwd</div>
</div>

<div id="legend">
  <h2>Trajectories</h2>

  <div class="leg-divider">OnePlus 11R — Code Only</div>
  {legend_op}

  <div class="leg-divider">Samsung A35 — Carrier Phase</div>
  {legend_sam}

  <div style="margin-top:8px;font-size:9px;color:#334155;
              border-top:1px solid rgba(255,255,255,.05);padding-top:7px">
    CORS mode: DGPS (OnePlus) | Kinematic RTK (Samsung)<br>
    -c = fwd + bwd Kalman combined — no extra smoothing applied.
  </div>
</div>

<div id="note">
  <strong>What is fwd/bwd?</strong>
  RTKLIB runs the Kalman filter twice — once forward in time, once backward
  — then combines both solutions weighted by their covariance.
  This is the <em>Rauch-Tung-Striebel (RTS) smoother</em> and
  produces a minimum-variance, drift-free smooth trajectory without
  needing IMU data.
</div>

<script>
var map = L.map('map', {{preferCanvas:true, zoomControl:true}})
           .setView([{clat:.7f}, {clon:.7f}], 17);

var osm = L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png',
  {{maxZoom:21, attribution:'© OpenStreetMap contributors'}}).addTo(map);
var sat = L.tileLayer(
  'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{{z}}/{{y}}/{{x}}',
  {{maxZoom:21, attribution:'Tiles © Esri'}});

{polyline_js}
{layer_add_js}
{start_end_js}

map.fitBounds({bounds}, {{padding:[60,60]}});

var overlays = {{
{overlay_js}}};
L.control.layers({{'OpenStreetMap':osm,'Satellite':sat}}, overlays,
  {{collapsed:false, position:'topright'}}).addTo(map);
</script>
</body>
</html>""".format(
        legend_op=''.join(
            '<div class="leg-item"><div class="leg-sw" style="background:{col}"></div>'
            '<div><div class="leg-lbl">{lbl}</div>'
            '<div class="leg-stat">{tip}</div></div></div>'.format(
                col=ly['color'], lbl=ly['label'], tip=ly['tooltip'])
            for ly in layers[:2]),
        legend_sam=''.join(
            '<div class="leg-item"><div class="leg-sw" style="background:{col}"></div>'
            '<div><div class="leg-lbl">{lbl}</div>'
            '<div class="leg-stat">{tip}</div></div></div>'.format(
                col=ly['color'], lbl=ly['label'], tip=ly['tooltip'])
            for ly in layers[2:]),
        clat=clat, clon=clon,
        polyline_js=polyline_js,
        layer_add_js=layer_add_js,
        start_end_js=start_end_js,
        bounds=json.dumps(bounds),
        overlay_js=overlay_js,
    )

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(html)
    print("  Saved: {}".format(out_path))


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    os.chdir(WORKDIR)
    print("=" * 65)
    print("Logger/8 — RTKLIB Forward/Backward Combined Kalman")
    print("  OnePlus : -p 1 (DGPS)       + -c (fwd/bwd)")
    print("  Samsung : -p 2 (kinematic)  + -c (fwd/bwd)")
    print("=" * 65)

    # 1. Parse NMEA (filtered only — no need for raw in this map)
    print("\n[1] Parsing NMEA filtered tracks ...")
    op_nmea  = parse_nmea(ONEPLUS_NMEA)
    sam_nmea = parse_nmea(SAMSUNG_NMEA)
    print("  OnePlus  NMEA filtered: {} pts  {:.0f} m".format(
        len(op_nmea), pdist(op_nmea)))
    print("  Samsung  NMEA filtered: {} pts  {:.0f} m".format(
        len(sam_nmea), pdist(sam_nmea)))

    # 2. Run RTKLIB with -c
    print("\n[2] Running RTKLIB with fwd/bwd Kalman smoother (-c) ...")
    run_rtklib_fwdbwd(ONEPLUS_RINEX, POS_ONEPLUS, mode=1, label="OnePlus DGPS")
    run_rtklib_fwdbwd(SAMSUNG_RINEX, POS_SAMSUNG, mode=2, label="Samsung RTK-kinematic")

    # 3. Parse pos files — OnePlus keep Q<=4, Samsung keep Q<=2 (float+fix)
    print("\n[3] Parsing pos files ...")
    op_cors  = parse_pos(POS_ONEPLUS,  max_q=4)
    sam_cors = parse_pos(POS_SAMSUNG,  max_q=2)

    print("\n  Step-size analysis after fwd/bwd:")
    print("  OnePlus  CORS: {}".format(step_stats(op_cors)))
    print("  Samsung  CORS: {}".format(step_stats(sam_cors)))

    # 4. Build map
    print("\n[4] Building HTML map ...")
    make_html(op_nmea, op_cors, sam_nmea, sam_cors, OUT_HTML)

    print("\n" + "=" * 65)
    print("DONE!")
    print("  Open: {}".format(os.path.abspath(OUT_HTML)))
    print("=" * 65)


def step_stats(pts):
    if len(pts) < 2: return 'no data'
    steps = sorted(hav(pts[i-1], pts[i]) for i in range(1, len(pts)))
    n = len(steps)
    return 'median={:.2f}m  p90={:.2f}m  max={:.2f}m'.format(
        steps[n//2], steps[int(0.9*n)], steps[-1])


if __name__ == '__main__':
    main()
