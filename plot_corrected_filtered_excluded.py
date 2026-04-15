#!/usr/bin/env python3
"""
Plot corrected and filtered trajectories after excluding one satellite in RTKLIB.
"""

import math
import os
import webbrowser

INPUT_POS = "out/solution_excl_G06.pos"
INPUT_GNSS_LOG = "logger/2/gnss_log_2026_03_15_11_10_23.txt"
OUT_MAP = "trajectory_corrected_filtered_excl_G06.html"
OUT_CSV = "trajectory_corrected_filtered_excl_G06.csv"


def read_pos(path):
    
    rows = []
    with open(path, "r") as f:
        for line in f:
            if not line.strip() or line.startswith("%"):
                continue
            p = line.split()
            if len(p) < 9:
                continue
            rows.append(
                {
                    "date": p[0],
                    "time": p[1],
                    "lat": float(p[2]),
                    "lon": float(p[3]),
                    "h": float(p[4]),
                    "q": int(p[5]),
                    "sdn": float(p[7]),
                    "sde": float(p[8]),
                }
            )
    return rows


def read_phone_fix(path):
    rows = []
    with open(path, "r") as f:
        for line in f:
            if not line.startswith("Fix,"):
                continue
            p = line.strip().split(",")
            if len(p) < 5:
                continue
            try:
                rows.append([float(p[2]), float(p[3])])
            except ValueError:
                continue
    return rows


def ll_to_xy(lat, lon, lat0, lon0):
    r = 6378137.0
    x = math.radians(lon - lon0) * r * math.cos(math.radians(lat0))
    y = math.radians(lat - lat0) * r
    return x, y


def xy_to_ll(x, y, lat0, lon0):
    r = 6378137.0
    lat = lat0 + math.degrees(y / r)
    lon = lon0 + math.degrees(x / (r * math.cos(math.radians(lat0))))
    return lat, lon


def median_filter(values, window=5):
    half = window // 2
    out = []
    n = len(values)
    for i in range(n):
        a = max(0, i - half)
        b = min(n, i + half + 1)
        w = sorted(values[a:b])
        out.append(w[len(w) // 2])
    return out


def moving_average(values, window=7):
    half = window // 2
    out = []
    n = len(values)
    for i in range(n):
        a = max(0, i - half)
        b = min(n, i + half + 1)
        out.append(sum(values[a:b]) / (b - a))
    return out


def smooth(rows):
    lat0 = rows[0]["lat"]
    lon0 = rows[0]["lon"]

    xs = []
    ys = []
    for r in rows:
        x, y = ll_to_xy(r["lat"], r["lon"], lat0, lon0)
        xs.append(x)
        ys.append(y)

    xs = median_filter(xs, window=5)
    ys = median_filter(ys, window=5)
    xs = moving_average(xs, window=7)
    ys = moving_average(ys, window=7)

    out = []
    for i, r in enumerate(rows):
        lat_s, lon_s = xy_to_ll(xs[i], ys[i], lat0, lon0)
        q = dict(r)
        q["lat_s"] = lat_s
        q["lon_s"] = lon_s
        out.append(q)
    return out


def write_csv(rows, path):
    with open(path, "w") as f:
        f.write("date,time,lat_corrected,lon_corrected,lat_filtered,lon_filtered,height_m,q,sdn_m,sde_m\n")
        for r in rows:
            f.write(
                f"{r['date']},{r['time']},{r['lat']:.8f},{r['lon']:.8f},{r['lat_s']:.8f},{r['lon_s']:.8f},"
                f"{r['h']:.3f},{r['q']},{r['sdn']:.3f},{r['sde']:.3f}\n"
            )


def build_map(rows, raw_phone, path):
    corrected = [[r["lat"], r["lon"]] for r in rows]
    filtered = [[r["lat_s"], r["lon_s"]] for r in rows]

    c_lat = sum(r["lat_s"] for r in rows) / len(rows)
    c_lon = sum(r["lon_s"] for r in rows) / len(rows)

    html = f"""<!doctype html>
<html>
<head>
  <meta charset=\"utf-8\"/>
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\"/>
  <title>Corrected vs Filtered (Excluded G06)</title>
  <link rel=\"stylesheet\" href=\"https://unpkg.com/leaflet@1.9.4/dist/leaflet.css\"/>
  <script src=\"https://unpkg.com/leaflet@1.9.4/dist/leaflet.js\"></script>
  <style>
    html, body, #map {{ height: 100%; margin: 0; }}
    .panel {{ background: white; padding: 8px 10px; border-radius: 6px; line-height: 1.35; }}
  </style>
</head>
<body>
<div id=\"map\"></div>
<script>
  const map = L.map('map').setView([{c_lat:.8f}, {c_lon:.8f}], 17);
  L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{ maxZoom: 20, attribution: '&copy; OpenStreetMap contributors' }}).addTo(map);

  const corrected = {corrected};
  const filtered = {filtered};
    const rawPhone = {raw_phone};

    if (rawPhone.length > 1) {{
        L.polyline(rawPhone, {{color:'#16a34a', weight:2, opacity:0.60}}).addTo(map).bindPopup('Raw phone trajectory');
    }}

  L.polyline(corrected, {{color:'#2563eb', weight:2, opacity:0.7}}).addTo(map).bindPopup('Corrected (satellite G06 excluded)');
  L.polyline(filtered, {{color:'#dc2626', weight:3, opacity:0.95}}).addTo(map).bindPopup('Filtered');

  L.marker(filtered[0]).addTo(map).bindPopup('Start');
  L.marker(filtered[filtered.length-1]).addTo(map).bindPopup('End');

  const panel = L.control({{position:'topright'}});
  panel.onAdd = function() {{
    const div = L.DomUtil.create('div','panel');
        div.innerHTML = '<b>Trajectories</b><br/>Green: raw phone<br/>Blue: corrected (excl G06)<br/>Red: filtered';
    return div;
  }};
  panel.addTo(map);
</script>
</body>
</html>
"""

    with open(path, "w", encoding="utf-8") as f:
        f.write(html)


def main():
    rows = read_pos(INPUT_POS)
    if not rows:
        print("No rows found in", INPUT_POS)
        return
    raw_phone = read_phone_fix(INPUT_GNSS_LOG)

    sm = smooth(rows)
    write_csv(sm, OUT_CSV)
    build_map(sm, raw_phone, OUT_MAP)

    print(f"Rows: {len(sm)}")
    print(f"Raw phone points: {len(raw_phone)}")
    print(f"Saved map: {OUT_MAP}")
    print(f"Saved csv: {OUT_CSV}")

    webbrowser.open("file://" + os.path.realpath(OUT_MAP))


if __name__ == "__main__":
    main()
