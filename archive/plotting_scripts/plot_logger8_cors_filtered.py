"""
plot_logger8_cors_filtered.py
==============================
Applies NMEA-equivalent quality filtering directly to CORS pos files,
then plots on a single map:

  For each device (OnePlus / Samsung):
    A) NMEA Filtered  — phone hardware fusion (baseline)
    B) CORS Filtered  — CORS corrected, then filtered by:
          * Q flag (quality)
          * sdn/sde (position std-dev, analog to HDOP)
          * ns (satellite count)
          * velocity gate (reject jumps > walking speed)

This is the closest we can get to "NMEA filtering on CORS data"
without re-running a full Kalman/IMU fusion pipeline.

Output: out/logger8_cors_filtered.html
"""

import os, re, math, json
from collections import defaultdict

# ── Config ────────────────────────────────────────────────────────────────────
WORKDIR     = r"C:\Users\Guntesh\Desktop\foo\gsd"

ONEPLUS_NMEA = r"logger\8_OnePlus\gnss_log_2026_04_11_11_40_31.nmea"
SAMSUNG_NMEA = r"logger\8_Samsung\gnss_log_2026_04_11_11_40_39.nmea"

# Use the fwd/bwd combined pos files (best quality we have)
POS_ONEPLUS  = r"out\logger8_oneplus_fwdbwd.pos"
POS_SAMSUNG  = r"out\logger8_samsung_fwdbwd.pos"

OUT_HTML = r"out\logger8_cors_filtered.html"

LAT_MIN, LAT_MAX = 17.0, 19.0
LON_MIN, LON_MAX = 77.0, 82.0

# NMEA filter values (same as phone baseline)
MIN_SNR_DB    = 25
MIN_GOOD_SATS = 4
MAX_HDOP      = 2.0
MIN_FIX_QUAL  = 1

# CORS pos-file filter equivalents
MAX_Q_OP      = 4      # OnePlus: accept DGPS (4) and better
MAX_Q_SAM     = 4      # Samsung: accept FLOAT (2), FIX (1), and DGPS (4) fallback
MAX_SDN       = 5.0    # max positional std-dev North (metres)
MAX_SDE       = 5.0    # max positional std-dev East  (metres)
MIN_NS        = 4      # minimum satellites
MAX_STEP_M    = 20.0   # velocity gate: reject only obviously wrong jumps (>20m in 1s)
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


def parse_nmea_filtered(fp):
    """Return only NMEA-filtered positions (SNR + HDOP gated)."""
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
                    q = int(m.group(5)); hdop = float(m.group(6))
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


# ── CORS pos-file filter (NMEA equivalent) ────────────────────────────────────
def parse_pos_nmea_style(path, max_q, label):
    """
    Parse a RTKLIB .pos file and apply NMEA-equivalent filters:
      1. Q flag        → equivalent to fix quality in GGA
      2. ns            → equivalent to satellite count (SNR gate proxy)
      3. sdn / sde     → equivalent to HDOP (positional precision)
      4. velocity gate → rejects impossible jumps (IMU physics)

    Columns: week SOW lat lon h Q ns sdn sde sdu sdne sdeu sdun age ratio
              [0] [1] [2] [3][4][5][6] [7] [8] [9]
    """
    raw_pts  = []   # all valid-bounds points
    filt_pts = []   # after quality + velocity filter

    n_total = n_q = n_sd = n_ns = n_vel = 0
    q_dist = {}

    if not os.path.exists(path):
        print("  WARNING: {} not found".format(path))
        return [], []

    with open(path, 'r', errors='ignore') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('%'): continue
            p = line.split()
            try:
                lat = float(p[2]); lon = float(p[3])
                q   = int(p[5]);   ns  = int(p[6])
                sdn = float(p[7]); sde = float(p[8])
            except: continue

            n_total += 1
            q_dist[q] = q_dist.get(q, 0) + 1

            if not (LAT_MIN <= lat <= LAT_MAX and LON_MIN <= lon <= LON_MAX):
                continue
            raw_pts.append((lat, lon))

            # Gate 1: quality flag
            if q > max_q:
                n_q += 1; continue

            # Gate 2: satellite count (analog to SNR/good-sat count)
            if ns < MIN_NS:
                n_ns += 1; continue

            # Gate 3: positional std-dev (analog to HDOP)
            if sdn > MAX_SDN or sde > MAX_SDE:
                n_sd += 1; continue

            filt_pts.append((lat, lon))

    # Gate 4: velocity gate — compare against last KEPT point
    # Comparing against previous raw point would falsely reject valid points
    # after a gap (prev skipped -> big distance from last kept).
    final = []
    last_kept = None
    for pt in filt_pts:
        if last_kept is not None:
            d = hav(last_kept, pt)
            if d > MAX_STEP_M:
                n_vel += 1
                continue   # skip outlier, continue tracking from last_kept
        final.append(pt)
        last_kept = pt

    ql = {1:'FIX', 2:'FLOAT', 3:'SBAS', 4:'DGPS', 5:'SINGLE', 6:'PPP'}
    q_str = '  '.join('Q{}({}): {}'.format(k, ql.get(k,'?'), v)
                      for k, v in sorted(q_dist.items()))

    print("  {} [{}]:".format(label, os.path.basename(path)))
    print("    total={} | Q_dist: {}".format(n_total, q_str))
    print("    Rejected: Q-fail={} ns-fail={} sd-fail={} vel-fail={}".format(
        n_q, n_ns, n_sd, n_vel))
    print("    Kept: {} pts  ({:.0f} m)".format(len(final), pdist(final)))
    return raw_pts, final


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

def step_stat(pts):
    if len(pts) < 2: return 'no data'
    st = sorted(hav(pts[i-1], pts[i]) for i in range(1, len(pts)))
    n = len(st)
    return 'med {:.2f}m | p90 {:.2f}m | max {:.2f}m'.format(
        st[n//2], st[int(.9*n)], st[-1])


# ── HTML builder ──────────────────────────────────────────────────────────────
def make_html(op_nmea, op_cors_filt,
              sam_nmea, sam_cors_filt, out_path):

    all_lats = [p[0] for t in [op_nmea, sam_nmea] for p in t if t]
    all_lons = [p[1] for t in [op_nmea, sam_nmea] for p in t if t]
    clat = sum(all_lats) / len(all_lats)
    clon = sum(all_lons) / len(all_lons)
    bounds = [[min(all_lats)-0.001, min(all_lons)-0.001],
              [max(all_lats)+0.001, max(all_lons)+0.001]]

    def st(t, lbl):
        return '{}: {} pts | {:.0f} m | {}'.format(lbl, len(t), pdist(t), step_stat(t))

    layers = [
        dict(var='lON', coords=op_nmea,      color='#fb923c', dash='4,4',
             weight=2.5, opacity=0.75, label='OnePlus — NMEA Filtered (phone fusion)',
             tooltip=st(op_nmea,      'OnePlus NMEA')),
        dict(var='lOC', coords=op_cors_filt,  color='#fbbf24', dash='',
             weight=3.5, opacity=0.95, label='OnePlus — CORS DGPS + Quality Filter',
             tooltip=st(op_cors_filt, 'OnePlus CORS-filt')),
        dict(var='lSN', coords=sam_nmea,      color='#67e8f9', dash='4,4',
             weight=2.5, opacity=0.75, label='Samsung — NMEA Filtered (phone fusion)',
             tooltip=st(sam_nmea,     'Samsung NMEA')),
        dict(var='lSC', coords=sam_cors_filt, color='#818cf8', dash='',
             weight=3.5, opacity=0.95, label='Samsung — CORS RTK + Quality Filter',
             tooltip=st(sam_cors_filt,'Samsung CORS-filt')),
    ]

    js_layers = ''
    js_add    = ''
    js_ovr    = ''

    for ly in layers:
        v  = ly['var']
        js_layers += """
var {v} = L.polyline({cds}, {{
  color:'{col}', weight:{wt}, opacity:{op}, dashArray:'{da}'
}}).bindTooltip('{tip}', {{sticky:true}});
""".format(v=v, cds=jc(ly['coords']), col=ly['color'],
           wt=ly['weight'], op=ly['opacity'], da=ly['dash'],
           tip=ly['tooltip'].replace("'", ""))
        js_add += "{}.addTo(map);\n".format(v)
        js_ovr += "  '{}': {},\n".format(ly['label'], v)

    # Start / end markers
    ref = op_nmea
    se_js = ''
    if ref:
        se_js = """
L.circleMarker({s}, {{radius:8,fillColor:'#22c55e',color:'#fff',weight:2,fillOpacity:1}})
 .bindPopup('<b>Walk Start</b>').addTo(map);
L.circleMarker({e}, {{radius:8,fillColor:'#ef4444',color:'#fff',weight:2,fillOpacity:1}})
 .bindPopup('<b>Walk End</b>').addTo(map);
""".format(s='[{:.7f},{:.7f}]'.format(*ref[0]),
           e='[{:.7f},{:.7f}]'.format(*ref[-1]))

    # Legend HTML
    leg_op  = ''
    leg_sam = ''
    for i, ly in enumerate(layers):
        sw  = 'background:{};'.format(ly['color'])
        row = ('<div class="li"><div class="sw" style="{}"></div>'
               '<div><div class="ll">{}</div>'
               '<div class="ls">{}</div></div></div>').format(
            sw, ly['label'], ly['tooltip'])
        if i < 2: leg_op  += row
        else:      leg_sam += row

    html = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Logger/8 — CORS + Quality Filter vs NMEA | April 11 2026</title>
  <meta name="description" content="CORS DGPS/RTK positions filtered by equivalent NMEA quality criteria (Q, sdn/sde, ns, velocity gate) vs phone NMEA, April 11 2026.">
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style>
    *,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
    html,body{{height:100%;font-family:'Inter',system-ui,sans-serif;background:#0a0e1a;color:#e2e8f0}}
    #map{{width:100vw;height:100vh}}

    #hdr{{
      position:fixed;top:0;left:0;right:0;z-index:1200;
      background:linear-gradient(135deg,rgba(10,14,26,.97),rgba(17,24,39,.97));
      border-bottom:1px solid rgba(99,179,237,.2);backdrop-filter:blur(12px);
      padding:8px 18px;display:flex;align-items:center;gap:14px;
      box-shadow:0 4px 20px rgba(0,0,0,.5);
    }}
    #hdr h1{{font-size:12px;font-weight:700;color:#7dd3fc;
             text-transform:uppercase;letter-spacing:.5px;white-space:nowrap}}
    #hdr .sub{{font-size:10px;color:#94a3b8;margin-top:1px}}
    .badge{{background:rgba(99,179,237,.12);border:1px solid rgba(99,179,237,.25);
            border-radius:12px;padding:3px 10px;font-size:10px;color:#7dd3fc;white-space:nowrap}}

    #legend{{
      position:fixed;bottom:14px;left:12px;z-index:1200;
      background:rgba(10,14,26,.95);border:1px solid rgba(99,179,237,.2);
      border-radius:12px;padding:12px 15px;backdrop-filter:blur(12px);
      box-shadow:0 8px 32px rgba(0,0,0,.5);min-width:260px;
    }}
    #legend h2{{font-size:10px;font-weight:700;color:#7dd3fc;
               text-transform:uppercase;letter-spacing:.8px;
               margin-bottom:9px;padding-bottom:7px;
               border-bottom:1px solid rgba(255,255,255,.08)}}
    .dv{{font-size:9px;font-weight:600;color:#475569;text-transform:uppercase;
         letter-spacing:.6px;margin:8px 0 4px;padding-top:5px;
         border-top:1px solid rgba(255,255,255,.06)}}
    .li{{display:flex;align-items:center;gap:8px;margin:4px 0;
         border-radius:5px;padding:2px 3px}}
    .li:hover{{background:rgba(255,255,255,.05)}}
    .sw{{width:24px;height:4px;border-radius:2px;flex-shrink:0}}
    .ll{{font-size:10.5px;font-weight:500}}
    .ls{{font-size:9px;color:#64748b;margin-top:1px}}

    #note{{
      position:fixed;bottom:14px;right:12px;z-index:1200;
      background:rgba(10,14,26,.93);border:1px solid rgba(99,179,237,.15);
      border-radius:9px;padding:10px 13px;font-size:9.5px;color:#64748b;
      max-width:240px;line-height:1.65;backdrop-filter:blur(8px);
    }}
    #note strong{{color:#94a3b8;display:block;margin-bottom:4px;font-size:10px}}
    #note code{{color:#7dd3fc;font-size:9px}}
  </style>
</head>
<body>
<div id="map"></div>

<div id="hdr">
  <div>
    <h1>Logger/8 — CORS Quality-Filtered vs NMEA</h1>
    <div class="sub">OnePlus 11R (DGPS) and Samsung A35 (RTK Float/Fix) — April 11, 2026</div>
  </div>
  <div class="badge">CORS fwd/bwd + Q/sdn/ns/velocity filter</div>
  <div class="badge">Dashed = NMEA &nbsp; Solid = CORS filtered</div>
</div>

<div id="legend">
  <h2>Trajectories</h2>
  <div class="dv">OnePlus 11R — Code Only</div>
  {leg_op}
  <div class="dv">Samsung A35 — Carrier Phase</div>
  {leg_sam}
  <div style="margin-top:8px;font-size:9px;color:#334155;
              border-top:1px solid rgba(255,255,255,.05);padding-top:7px">
    Dashed = phone NMEA (hardware Kalman + IMU)<br>
    Solid  = CORS corrected + quality filter<br>
    Toggle layers in control (top-right)
  </div>
</div>

<div id="note">
  <strong>CORS Quality Filter (NMEA equivalent)</strong>
  Applied to RTKLIB fwd/bwd pos file:<br>
  <code>Q &le; {max_q_op} (OnePlus) / {max_q_sam} (Samsung)</code><br>
  <code>sdn &le; {MAX_SDN} m, sde &le; {MAX_SDE} m</code> (analog to HDOP)<br>
  <code>ns &ge; {MIN_NS}</code> satellites<br>
  <code>step &le; {MAX_STEP_M} m/epoch</code> (velocity gate)
</div>

<script>
var map = L.map('map', {{preferCanvas:true}}).setView([{clat:.7f},{clon:.7f}], 17);

var osm = L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png',
  {{maxZoom:21,attribution:'© OpenStreetMap contributors'}}).addTo(map);
var sat = L.tileLayer(
  'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{{z}}/{{y}}/{{x}}',
  {{maxZoom:21,attribution:'Tiles © Esri'}});

{js_layers}
{js_add}
{se_js}

map.fitBounds({bounds}, {{padding:[60,60]}});

L.control.layers({{'OSM':osm,'Satellite':sat}}, {{
{js_ovr}}}, {{collapsed:false,position:'topright'}}).addTo(map);
</script>
</body>
</html>""".format(
        leg_op=leg_op, leg_sam=leg_sam,
        max_q_op=MAX_Q_OP, max_q_sam=MAX_Q_SAM,
        MAX_SDN=MAX_SDN, MAX_SDE=MAX_SDE,
        MIN_NS=MIN_NS, MAX_STEP_M=MAX_STEP_M,
        clat=clat, clon=clon,
        js_layers=js_layers, js_add=js_add, se_js=se_js,
        bounds=json.dumps(bounds), js_ovr=js_ovr,
    )

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(html)
    print("  HTML saved: {}".format(out_path))


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    os.chdir(WORKDIR)
    print("=" * 65)
    print("Logger/8 — CORS Quality-Filtered vs NMEA Baseline")
    print("=" * 65)

    print("\n[1] Parsing NMEA filtered baselines ...")
    op_nmea  = parse_nmea_filtered(ONEPLUS_NMEA)
    sam_nmea = parse_nmea_filtered(SAMSUNG_NMEA)
    print("  OnePlus  NMEA: {} pts  {:.0f} m  {}".format(
        len(op_nmea),  pdist(op_nmea),  step_stat(op_nmea)))
    print("  Samsung  NMEA: {} pts  {:.0f} m  {}".format(
        len(sam_nmea), pdist(sam_nmea), step_stat(sam_nmea)))

    print("\n[2] Parsing CORS pos files with NMEA-equivalent filters ...")
    print("\n  --- OnePlus (DGPS, max_q={}) ---".format(MAX_Q_OP))
    _, op_cors = parse_pos_nmea_style(POS_ONEPLUS,  MAX_Q_OP,  "OnePlus")

    print("\n  --- Samsung (RTK, max_q={}) ---".format(MAX_Q_SAM))
    _, sam_cors = parse_pos_nmea_style(POS_SAMSUNG, MAX_Q_SAM, "Samsung")

    print("\n[3] Building HTML map ...")
    make_html(op_nmea, op_cors, sam_nmea, sam_cors, OUT_HTML)

    print("\n" + "=" * 65)
    print("DONE!  Open: {}".format(os.path.abspath(OUT_HTML)))
    print("=" * 65)


if __name__ == '__main__':
    main()
