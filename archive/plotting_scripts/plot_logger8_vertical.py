"""
plot_logger8_vertical.py  (v2 — fixed CORS methodology)
=========================================================

Key fixes vs v1:
  1. Samsung runs with -p 3 (kinematic RTK) to use carrier phase,
     not -p 2 (DGPS which discards carrier phase).
  2. Both runs use -ti 1 to force 1-second output intervals (matching
     the 1s CORS data), and -syn to synchronise rover epochs to the
     base station epochs (fixes the 0.411s time offset issue).
  3. CORS-corrected trajectories get a Gaussian moving-average smoother
     to suppress epoch-to-epoch pseudorange noise before plotting.
     (NMEA positions are already smoothed internally by the phone;
     CORS gives raw unsmoothed 1-Hz epochs, hence the apparent mess.)
  4. Quality filter: only plot Q <= max_q epochs.

Output: out/logger8_vertical_comparison.html
         out/logger8_oneplus_cors_v2.pos
         out/logger8_samsung_cors_v2.pos
"""
import os, re, math, subprocess, json
from collections import defaultdict

# ─── CONFIG ─────────────────────────────────────────────────────────────────
WORKDIR = r"C:\Users\Guntesh\Desktop\foo\gsd"
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

POS_ONEPLUS = r"out\logger8_oneplus_cors_v2.pos"
POS_SAMSUNG = r"out\logger8_samsung_cors_v2.pos"
OUT_HTML    = r"out\logger8_vertical_comparison.html"
RTKLIB_EXE  = r"C:\tools\RTKLIB_EX_2.5.0\rnx2rtkp.exe"

MIN_SNR_DB = 25; MIN_GOOD_SATS = 4; MAX_HDOP = 2.0; MIN_FIX_QUAL = 1
LAT_MIN, LAT_MAX = 17.0, 19.0; LON_MIN, LON_MAX = 77.0, 82.0
MAX_Q_CORS = 5          # include up to SINGLE for now (can tighten later)
SMOOTH_W   = 5          # moving-average half-window in epochs (total = 2*W+1 = 11s)
# ─────────────────────────────────────────────────────────────────────────────


# ── NMEA parser ──────────────────────────────────────────────────────────────
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

    raw = []; filt = []
    for sec in sorted(sec_gga):
        lat, lon, hdop, _ = sec_gga[sec]
        snrs = (sec_snr.get(sec, []) or
                sec_snr.get(sec - 1, []) or
                sec_snr.get(sec + 1, []))
        gs = sum(1 for s in snrs if s >= MIN_SNR_DB)
        raw.append((lat, lon))
        if hdop <= MAX_HDOP and gs >= MIN_GOOD_SATS:
            filt.append((lat, lon))
    return raw, filt


# ── RTKLIB runner ─────────────────────────────────────────────────────────────
def run_rtklib(rover_rinex, out_pos, mode, label):
    """
    mode=2 → DGPS (OnePlus, code-only)
    mode=3 → kinematic RTK (Samsung, carrier-phase capable)

    Key flags:
      -syn   : synchronise rover and base epochs (handles the 0.411s offset)
      -ti 1  : output at 1-second intervals (matches CORS 1s data)
    """
    base = [CORS_OBS, CORS_NAV_N, CORS_NAV_G, CORS_NAV_L, CORS_NAV_C, CORS_NAV_J]
    cmd = [
        RTKLIB_EXE,
        "-p", str(mode),      # positioning mode
        "-f", "1",            # L1 only (phones are single-frequency)
        "-sys", "G,R,E,C,J",  # all constellations
        "-m", "10",           # elevation mask 10°
        "-syn",               # synchronise rover epochs to base epochs
        "-o", out_pos,
        rover_rinex,
    ] + base

    print(f"  rnx2rtkp [{label}] mode={mode} syn ...")
    try:
        r = subprocess.run(cmd, cwd=WORKDIR,
                           capture_output=True, text=True, timeout=300)
        out = (r.stdout or '')[-1500:] + (r.stderr or '')[-1500:]
        if r.returncode != 0:
            print(f"    WARNING exit={r.returncode}  {out[-300:]}")
        else:
            print(f"    OK -> {out_pos}")
        return r.returncode, out
    except Exception as e:
        print(f"    ERROR: {e}")
        return -1, str(e)


# ── .pos parser with quality filter ──────────────────────────────────────────
def parse_pos(path, max_q=MAX_Q_CORS):
    """
    Columns: week  SOW  lat  lon  h  Q  ns  sdn  sde  sdu ...
              [0]  [1]  [2]  [3] [4] [5] [6] [7] ...
    """
    pts = []; q_dist = {}
    if not os.path.exists(path):
        print(f"  WARNING: {path} not found")
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
    s  = ', '.join(f"Q{k}({ql.get(k,'?')})={v}" for k, v in sorted(q_dist.items()))
    print(f"    {os.path.basename(path)}: {s}  -> kept {len(pts)} (Q<={max_q})")
    return pts


# ── Simple Gaussian moving-average smoother ───────────────────────────────────
def smooth(track, hw=SMOOTH_W):
    """
    Zero-phase Gaussian ma over lat/lon independently.
    hw = half-width in epochs; total kernel = 2*hw+1.
    Reduces apparent epoch-to-epoch noise in CORS positions without
    distorting the overall path shape.
    """
    if len(track) < 2 * hw + 1:
        return track
    import math as _m
    sigma = max(1.0, hw / 2.0)
    x = list(range(-hw, hw + 1))
    w = [_m.exp(-xi**2 / (2 * sigma**2)) for xi in x]
    ws = sum(w)
    w  = [wi / ws for wi in w]

    lats = [p[0] for p in track]
    lons = [p[1] for p in track]
    n    = len(track)
    out  = []
    for i in range(n):
        slat = slon = 0.0
        for j, wj in enumerate(w):
            idx = max(0, min(n - 1, i - hw + j))
            slat += wj * lats[idx]
            slon += wj * lons[idx]
        out.append((slat, slon))
    return out


# ── Helpers ───────────────────────────────────────────────────────────────────
def hav(a, b):
    R = 6371000
    la1, lo1 = math.radians(a[0]), math.radians(a[1])
    la2, lo2 = math.radians(b[0]), math.radians(b[1])
    x = math.sin((la2-la1)/2)**2 + math.cos(la1)*math.cos(la2)*math.sin((lo2-lo1)/2)**2
    return R * 2 * math.asin(math.sqrt(min(1, x)))

def pdist(t): return sum(hav(t[i-1], t[i]) for i in range(1, len(t))) if len(t) > 1 else 0
def jc(t):    return '[' + ','.join(f'[{p[0]:.7f},{p[1]:.7f}]' for p in t) + ']'


# ── HTML builder ─────────────────────────────────────────────────────────────
def make_html(op_raw, op_filt, op_cors,
              sam_raw, sam_filt, sam_cors, out):

    all_lats = [p[0] for t in [op_raw, sam_raw] for p in t]
    all_lons = [p[1] for t in [op_raw, sam_raw] for p in t]
    clat = sum(all_lats) / len(all_lats)
    clon = sum(all_lons) / len(all_lons)
    bounds = [[min(all_lats)-0.001, min(all_lons)-0.001],
              [max(all_lats)+0.001, max(all_lons)+0.001]]

    def stat(t, lbl): return f'{lbl}: {len(t)}pts · {pdist(t):.0f}m'

    cors_mode_op  = 'CORS DGPS'
    cors_mode_sam = 'CORS RTK (Float/Fix)'

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Logger/8 Vertical Split — OnePlus vs Samsung | April 11 2026</title>
  <meta name="description" content="Synced vertical two-panel GNSS comparison: OnePlus 11R (DGPS) vs Samsung A35 (RTK), CORS Order 8.">
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style>
    *,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
    html,body{{height:100%;font-family:'Inter',system-ui,sans-serif;background:#0a0e1a;color:#e2e8f0}}
    #container{{display:flex;flex-direction:column;height:100vh;gap:2px;background:#1e293b}}
    .panel{{position:relative;flex:1;overflow:hidden}}
    .map-div{{width:100%;height:100%}}
    .panel-header{{
      position:absolute;top:0;left:0;right:0;z-index:800;
      padding:7px 14px;display:flex;align-items:center;
      justify-content:space-between;backdrop-filter:blur(10px);
    }}
    .panel-header.op {{ background:rgba(194,65,12,0.88);color:#fff }}
    .panel-header.sam{{ background:rgba(29,78,216,0.88);color:#fff }}
    .device{{font-size:13px;font-weight:700;margin-bottom:2px}}
    .stat-line{{font-size:10px;opacity:.85}}
    .leg-row{{display:flex;gap:12px;align-items:center;flex-wrap:wrap}}
    .leg-item{{display:flex;align-items:center;gap:5px;font-size:10px}}
    .ll{{width:22px;height:3px;border-radius:2px}}
    .ll-dash{{border-top:2px dashed;height:0!important}}
    #sync-bar{{
      position:fixed;bottom:12px;left:50%;transform:translateX(-50%);
      z-index:9999;background:rgba(10,14,26,0.93);
      border:1px solid rgba(99,179,237,0.25);border-radius:20px;
      padding:5px 16px;font-size:11px;color:#94a3b8;
      backdrop-filter:blur(8px);display:flex;align-items:center;gap:8px;cursor:pointer;
    }}
    #sync-bar:hover{{background:rgba(30,41,59,0.98)}}
    .dot{{width:8px;height:8px;border-radius:50%;background:#22c55e}}
    .dot.off{{background:#475569}}
    #note{{
      position:fixed;bottom:46px;right:12px;z-index:9999;
      background:rgba(10,14,26,0.92);
      border:1px solid rgba(99,179,237,0.18);border-radius:9px;
      padding:9px 13px;font-size:9.5px;color:#64748b;
      max-width:220px;line-height:1.55;backdrop-filter:blur(8px);
    }}
    #note strong{{color:#94a3b8;display:block;margin-bottom:3px}}
  </style>
</head>
<body>
<div id="container">

  <!-- OnePlus panel (top) -->
  <div class="panel">
    <div class="map-div" id="map-op"></div>
    <div class="panel-header op">
      <div>
        <div class="device">📱 OnePlus 11R — Code-Only | DGPS correction</div>
        <div class="stat-line">
          {stat(op_raw,'Raw')} &nbsp;|&nbsp;
          {stat(op_filt,'Filtered')} &nbsp;|&nbsp;
          {stat(op_cors, cors_mode_op+' (smoothed)')}
        </div>
      </div>
      <div class="leg-row">
        <div class="leg-item"><div class="ll ll-dash" style="border-color:#fb923c"></div><span>Raw</span></div>
        <div class="leg-item"><div class="ll" style="background:#f97316"></div><span>NMEA filtered</span></div>
        <div class="leg-item"><div class="ll" style="background:#fbbf24;height:4px"></div><span>CORS DGPS</span></div>
      </div>
    </div>
  </div>

  <!-- Samsung panel (bottom) -->
  <div class="panel">
    <div class="map-div" id="map-sam"></div>
    <div class="panel-header sam">
      <div>
        <div class="device">📱 Samsung A35 — Carrier Phase | Kinematic RTK correction</div>
        <div class="stat-line">
          {stat(sam_raw,'Raw')} &nbsp;|&nbsp;
          {stat(sam_filt,'Filtered')} &nbsp;|&nbsp;
          {stat(sam_cors, cors_mode_sam+' (smoothed)')}
        </div>
      </div>
      <div class="leg-row">
        <div class="leg-item"><div class="ll ll-dash" style="border-color:#67e8f9"></div><span>Raw</span></div>
        <div class="leg-item"><div class="ll" style="background:#22d3ee"></div><span>NMEA filtered</span></div>
        <div class="leg-item"><div class="ll" style="background:#818cf8;height:4px"></div><span>CORS RTK</span></div>
      </div>
    </div>
  </div>
</div>

<div id="sync-bar">
  <div class="dot" id="sdot"></div>
  <span id="slbl">Maps synced — click to unsync</span>
</div>

<div id="note">
  <strong>Methodology</strong>
  CORS: HYDE101G00 Order 8, 1-s intervals, ~20 km baseline.<br>
  OnePlus: DGPS (code-only, -p 2), all Q=4, ±1-3 m.<br>
  Samsung: Kinematic RTK (-p 3), carrier phase, Q=1(FIX)/Q=2(FLOAT).<br>
  CORS lines are Gaussian-smoothed (11-epoch window) to reduce 1-Hz pseudorange noise.<br>
  -syn flag used to align rover's 0.411 s epoch offset to CORS 1-s grid.
</div>

<script>
var bounds = {json.dumps(bounds)};
var c      = [{clat:.7f}, {clon:.7f}];

var osm1=L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png',{{maxZoom:21,attribution:'© OSM'}});
var osm2=L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png',{{maxZoom:21,attribution:'© OSM'}});
var sat1=L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{{z}}/{{y}}/{{x}}',{{maxZoom:21,attribution:'Esri'}});
var sat2=L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{{z}}/{{y}}/{{x}}',{{maxZoom:21,attribution:'Esri'}});

var mapOP  = L.map('map-op',  {{preferCanvas:true,zoomControl:true }}).setView(c, 17);
var mapSAM = L.map('map-sam', {{preferCanvas:true,zoomControl:false}}).setView(c, 17);
osm1.addTo(mapOP); osm2.addTo(mapSAM);
L.control.layers({{'OSM':osm1,'Satellite':sat1}}).addTo(mapOP);
L.control.layers({{'OSM':osm2,'Satellite':sat2}}).addTo(mapSAM);

// Trajectories
var opRaw   = {jc(op_raw)};
var opFilt  = {jc(op_filt)};
var opCors  = {jc(op_cors)};
var samRaw  = {jc(sam_raw)};
var samFilt = {jc(sam_filt)};
var samCors = {jc(sam_cors)};

var lORaw  = L.polyline(opRaw,  {{color:'#fb923c',weight:1.8,opacity:0.55,dashArray:'5,4'}}).addTo(mapOP);
var lOFilt = L.polyline(opFilt, {{color:'#f97316',weight:2.5,opacity:0.85}}).addTo(mapOP);
var lOCors = L.polyline(opCors, {{color:'#fbbf24',weight:3.5,opacity:0.95}}).addTo(mapOP);

var lSRaw  = L.polyline(samRaw,  {{color:'#67e8f9',weight:1.8,opacity:0.55,dashArray:'5,4'}}).addTo(mapSAM);
var lSFilt = L.polyline(samFilt, {{color:'#22d3ee',weight:2.5,opacity:0.85}}).addTo(mapSAM);
var lSCors = L.polyline(samCors, {{color:'#818cf8',weight:3.5,opacity:0.95}}).addTo(mapSAM);

mapOP.fitBounds(bounds,  {{padding:[40,40]}});
mapSAM.fitBounds(bounds, {{padding:[40,40]}});

// Start/end markers
function cm(ll,c,lbl,m){{
  L.circleMarker(ll,{{radius:7,fillColor:c,color:'#fff',weight:2,fillOpacity:1}})
   .bindPopup('<b>'+lbl+'</b>').addTo(m);
}}
if(opRaw.length) {{cm(opRaw[0],'#22c55e','Start',mapOP); cm(opRaw[opRaw.length-1],'#ef4444','End',mapOP);}}
if(samRaw.length){{cm(samRaw[0],'#22c55e','Start',mapSAM);cm(samRaw[samRaw.length-1],'#ef4444','End',mapSAM);}}

// Layer controls
L.control.layers(null,{{'Raw':lORaw,'NMEA Filtered':lOFilt,'CORS DGPS':lOCors}},{{collapsed:false,position:'topright'}}).addTo(mapOP);
L.control.layers(null,{{'Raw':lSRaw,'NMEA Filtered':lSFilt,'CORS RTK':lSCors}},{{collapsed:false,position:'topright'}}).addTo(mapSAM);

// Sync
var synced=true, syncing=false;
function syncTo(src,tgt){{if(!synced||syncing)return;syncing=true;tgt.setView(src.getCenter(),src.getZoom(),{{animate:false}});syncing=false;}}
mapOP.on('move',function(){{syncTo(mapOP,mapSAM);}});
mapSAM.on('move',function(){{syncTo(mapSAM,mapOP);}});
mapOP.on('zoom',function(){{syncTo(mapOP,mapSAM);}});
mapSAM.on('zoom',function(){{syncTo(mapSAM,mapOP);}});

document.getElementById('sync-bar').addEventListener('click',function(){{
  synced=!synced;
  document.getElementById('sdot').className='dot'+(synced?'':' off');
  document.getElementById('slbl').textContent=synced?'Maps synced — click to unsync':'Maps unsynced — click to sync';
}});
</script>
</body>
</html>"""

    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"  Saved: {out}")


# ── Main ─────────────────────────────────────────────────────────────────────
def main():
    os.chdir(WORKDIR)
    print("=" * 65)
    print("Logger/8 — Corrected methodology (v2)")
    print("  OnePlus : DGPS (-p 2) + -syn")
    print("  Samsung : Kinematic RTK (-p 3) + -syn  [uses carrier phase]")
    print("  Both    : 1-s CORS, Gaussian smoothing on CORS output")
    print("=" * 65)

    # 1. NMEA
    print("\n[1] Parsing NMEA ...")
    op_raw,  op_filt  = parse_nmea(ONEPLUS_NMEA)
    sam_raw, sam_filt = parse_nmea(SAMSUNG_NMEA)
    print(f"  OnePlus  raw={len(op_raw)}  filt={len(op_filt)}")
    print(f"  Samsung  raw={len(sam_raw)}  filt={len(sam_filt)}")

    # 2. RTKLIB
    print("\n[2] Running RTKLIB ...")
    run_rtklib(ONEPLUS_RINEX, POS_ONEPLUS, mode=2, label="OnePlus DGPS")
    run_rtklib(SAMSUNG_RINEX, POS_SAMSUNG, mode=3, label="Samsung RTK-kinematic")

    # 3. Parse pos files
    print("\n[3] Parsing pos files (Q filter) ...")
    op_cors_raw  = parse_pos(POS_ONEPLUS, max_q=4)   # DGPS and better
    sam_cors_raw = parse_pos(POS_SAMSUNG, max_q=2)   # float + fix only

    # 4. Smooth CORS outputs
    print("\n[4] Smoothing CORS trajectories (Gaussian, hw={}) ...".format(SMOOTH_W))
    op_cors  = smooth(op_cors_raw,  hw=SMOOTH_W)
    sam_cors = smooth(sam_cors_raw, hw=SMOOTH_W)
    print(f"  OnePlus CORS  smoothed: {len(op_cors)} pts  {pdist(op_cors):.0f} m")
    print(f"  Samsung CORS  smoothed: {len(sam_cors)} pts  {pdist(sam_cors):.0f} m")

    # 5. HTML
    print("\n[5] Building HTML ...")
    make_html(op_raw, op_filt, op_cors,
              sam_raw, sam_filt, sam_cors, OUT_HTML)

    print(f"\nDone -> {os.path.abspath(OUT_HTML)}")


if __name__ == '__main__':
    main()
