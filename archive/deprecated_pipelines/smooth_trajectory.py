#!/usr/bin/env python3
"""
Create a cleaned trajectory from RTKLIB POS output using robust filtering.
Pure-Python implementation (no external dependencies).
"""

import math
import os
import webbrowser

INPUT_POS = "out/solution_first.pos"
INPUT_GNSS_LOG = "logger/2/gnss_log_2026_03_15_11_10_23.txt"
OUTPUT_CSV = "trajectory_smoothed.csv"
OUTPUT_HTML = "trajectory_smoothed_map.html"


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
                    "Q": int(p[5]),
                    "ns": int(p[6]),
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
            parts = line.strip().split(",")
            if len(parts) < 5:
                continue
            try:
                rows.append(
                    {
                        "provider": parts[1],
                        "lat": float(parts[2]),
                        "lon": float(parts[3]),
                        "alt": float(parts[4]),
                        "acc": float(parts[6]) if len(parts) > 6 and parts[6] else float("nan"),
                    }
                )
            except ValueError:
                continue
    return rows


def haversine_m(lat1, lon1, lat2, lon2):
    r = 6371000.0
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def ll_to_local_xy(lat, lon, lat0, lon0):
    r = 6378137.0
    x = math.radians(lon - lon0) * r * math.cos(math.radians(lat0))
    y = math.radians(lat - lat0) * r
    return x, y


def local_xy_to_ll(x, y, lat0, lon0):
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


def interpolate_gaps(pts):
    n = len(pts)
    i = 0
    while i < n:
        if pts[i]["keep"]:
            i += 1
            continue

        start = i - 1
        j = i
        while j < n and not pts[j]["keep"]:
            j += 1
        end = j

        if start >= 0 and end < n:
            x0, y0 = pts[start]["x"], pts[start]["y"]
            x1, y1 = pts[end]["x"], pts[end]["y"]
            gap = end - start
            for k in range(start + 1, end):
                t = (k - start) / gap
                pts[k]["x"] = x0 + t * (x1 - x0)
                pts[k]["y"] = y0 + t * (y1 - y0)
                pts[k]["interp"] = True
                pts[k]["keep"] = True
        elif start >= 0:
            for k in range(i, end):
                pts[k]["x"] = pts[start]["x"]
                pts[k]["y"] = pts[start]["y"]
                pts[k]["interp"] = True
                pts[k]["keep"] = True
        elif end < n:
            for k in range(0, end):
                pts[k]["x"] = pts[end]["x"]
                pts[k]["y"] = pts[end]["y"]
                pts[k]["interp"] = True
                pts[k]["keep"] = True

        i = end


def clean_trajectory(rows):
    if not rows:
        return []

    lat0 = rows[0]["lat"]
    lon0 = rows[0]["lon"]

    pts = []
    for r in rows:
        x, y = ll_to_local_xy(r["lat"], r["lon"], lat0, lon0)
        rr = dict(r)
        rr["x"] = x
        rr["y"] = y
        rr["keep"] = True
        rr["interp"] = False
        pts.append(rr)

    max_step_m = 3.0
    for i in range(1, len(pts)):
        step = math.hypot(pts[i]["x"] - pts[i - 1]["x"], pts[i]["y"] - pts[i - 1]["y"])
        if step > max_step_m:
            pts[i]["keep"] = False

    interpolate_gaps(pts)

    xs = [p["x"] for p in pts]
    ys = [p["y"] for p in pts]

    xs = median_filter(xs, window=5)
    ys = median_filter(ys, window=5)

    xs = moving_average(xs, window=7)
    ys = moving_average(ys, window=7)

    out = []
    for i, p in enumerate(pts):
        lat, lon = local_xy_to_ll(xs[i], ys[i], lat0, lon0)
        q = dict(p)
        q["lat_s"] = lat
        q["lon_s"] = lon
        out.append(q)

    return out


def write_csv(cleaned, out_csv):
    with open(out_csv, "w") as f:
        f.write("date,time,lat_raw,lon_raw,lat_smoothed,lon_smoothed,height_m,sdn_m,sde_m,interpolated\n")
        for p in cleaned:
            f.write(
                f"{p['date']},{p['time']},{p['lat']:.8f},{p['lon']:.8f},{p['lat_s']:.8f},{p['lon_s']:.8f},"
                f"{p['h']:.3f},{p['sdn']:.3f},{p['sde']:.3f},{int(p['interp'])}\n"
            )


def build_html(cleaned, raw_phone, out_html):
    corr_js = [[p["lat"], p["lon"]] for p in cleaned]
    sm_js = [[p["lat_s"], p["lon_s"]] for p in cleaned]
    phone_js = [[p["lat"], p["lon"]] for p in raw_phone]

    c_lat = sum(p["lat_s"] for p in cleaned) / len(cleaned)
    c_lon = sum(p["lon_s"] for p in cleaned) / len(cleaned)

    html = f"""<!doctype html>
<html>
<head>
  <meta charset=\"utf-8\"/>
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\"/>
    <title>Raw vs Corrected vs Smoothed Trajectory</title>
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

    const phoneRaw = {phone_js};
    const corrected = {corr_js};
  const smooth = {sm_js};

    if (phoneRaw.length > 1) {{
        const phoneLine = L.polyline(phoneRaw, {{color:'#16a34a', weight:2, opacity:0.65}}).addTo(map);
        phoneLine.bindPopup('Raw phone Fix trajectory (from gnss_log .txt)');
    }}

    const corrLine = L.polyline(corrected, {{color:'#2563eb', weight:2, opacity:0.55}}).addTo(map);
    corrLine.bindPopup('CORS-corrected RTKLIB trajectory');

  const smLine = L.polyline(smooth, {{color:'#dc2626', weight:3, opacity:0.95}}).addTo(map);
  smLine.bindPopup('Smoothed trajectory');

  L.marker(smooth[0]).addTo(map).bindPopup('Start');
  L.marker(smooth[smooth.length-1]).addTo(map).bindPopup('End');

  const panel = L.control({{position:'topright'}});
  panel.onAdd = function() {{
    const div = L.DomUtil.create('div','panel');
        div.innerHTML = '<b>Trajectory Compare</b><br/>Green: phone raw Fix<br/>Blue: CORS corrected<br/>Red: filtered/smoothed';
    return div;
  }};
  panel.addTo(map);
</script>
</body>
</html>
"""

    with open(out_html, "w", encoding="utf-8") as f:
        f.write(html)


def metrics(rows, lat_key="lat", lon_key="lon"):
    steps = []
    for i in range(1, len(rows)):
        d = haversine_m(rows[i - 1][lat_key], rows[i - 1][lon_key], rows[i][lat_key], rows[i][lon_key])
        steps.append(d)
    steps_sorted = sorted(steps)
    p95_idx = int(0.95 * len(steps_sorted)) - 1
    p95 = steps_sorted[max(0, p95_idx)]
    return {
        "mean_step": sum(steps) / len(steps),
        "p95_step": p95,
        "max_step": max(steps),
        "gt3": sum(1 for s in steps if s > 3.0),
        "gt5": sum(1 for s in steps if s > 5.0),
    }


def main():
    rows = read_pos(INPUT_POS)
    if not rows:
        print("No trajectory rows found.")
        return

    phone_raw = read_phone_fix(INPUT_GNSS_LOG)

    cleaned = clean_trajectory(rows)

    raw_m = metrics(rows, "lat", "lon")
    sm_m = metrics(cleaned, "lat_s", "lon_s")

    write_csv(cleaned, OUTPUT_CSV)
    build_html(cleaned, phone_raw, OUTPUT_HTML)

    print("Raw step stats (m):")
    print(f"  mean={raw_m['mean_step']:.2f}, p95={raw_m['p95_step']:.2f}, max={raw_m['max_step']:.2f}, >3m={raw_m['gt3']}, >5m={raw_m['gt5']}")
    print("Smoothed step stats (m):")
    print(f"  mean={sm_m['mean_step']:.2f}, p95={sm_m['p95_step']:.2f}, max={sm_m['max_step']:.2f}, >3m={sm_m['gt3']}, >5m={sm_m['gt5']}")

    interp_count = sum(1 for p in cleaned if p["interp"])
    print(f"Interpolated outlier epochs: {interp_count}/{len(cleaned)}")
    print(f"Raw phone Fix points: {len(phone_raw)}")

    print(f"Saved: {OUTPUT_CSV}")
    print(f"Saved: {OUTPUT_HTML}")

    webbrowser.open("file://" + os.path.realpath(OUTPUT_HTML))


if __name__ == "__main__":
    main()
