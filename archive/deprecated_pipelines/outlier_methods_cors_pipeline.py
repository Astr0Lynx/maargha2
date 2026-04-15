#!/usr/bin/env python3
"""
Logger/3 + Order4 pipeline:
- Parse raw phone trajectory
- Parse NMEA + Status quality metrics
- Filter rover epochs using industry-style thresholds
- Run CORS on raw and NMEA-filtered rover RINEX
- Plot 4 requested trajectories on one PNG and one Leaflet HTML map
"""

import csv
import datetime as dt
import json
import math
import os
import subprocess
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

try:
    import matplotlib.pyplot as plt
except Exception:
    plt = None

WORKDIR = r"C:\Users\Guntesh\Desktop\foo\gsd"
RTKLIB_EXE = r"C:\tools\RTKLIB_EX_2.5.0\rnx2rtkp.exe"

ROVER_RINEX = r"logger\3\gnss_log_2026_04_04_17_53_31.26o"
RAW_FIX_LOG = r"logger\3\gnss_log_2026_04_04_17_53_31.txt"
NMEA_LOG = r"logger\3\gnss_log_2026_04_04_17_53_31.nmea"

BASE_FILES = [
    r"cors\Order4\HYDE094M.26o",
    r"cors\Order4\HYDE094M.26n",
    r"cors\Order4\HYDE094M.26g",
    r"cors\Order4\HYDE094M.26l",
    r"cors\Order4\HYDE094M.26c",
    r"cors\Order4\HYDE094M.26j",
]

OUT_DIR = r"out"
OUT_ROVER_FILTERED = r"out\rover_nmea_filtered_order4.26o"
OUT_CORS_RAW_POS = r"out\solution_cors_raw_order4.pos"
OUT_CORS_FILTERED_POS = r"out\solution_cors_nmea_filtered_order4.pos"
OUT_RAW_CSV = r"out\raw_logger3.csv"
OUT_NMEA_FILTERED_CSV = r"out\raw_nmea_filtered_logger3.csv"
OUT_MAP_PNG = r"out\logger3_order4_4traj.png"
OUT_MAP_HTML = r"out\logger3_order4_4traj.html"
OUT_METRICS = r"out\logger3_order4_metrics.txt"

# Thresholds
CN0_MIN = 28.0
ELEV_MIN_DEG = 10.0
HDOP_MAX = 5.0
PDOP_MAX = 10.0
MIN_PASSING_SATS = 6

GPS_EPOCH = dt.datetime(1980, 1, 6)
GPST_MINUS_UTC_SECONDS = 18


@dataclass
class SatObs:
    cn0: Optional[float]
    elev: Optional[float]
    used: Optional[bool]


@dataclass
class EpochQuality:
    sat_total: int = 0
    sat_pass: int = 0
    hdop: Optional[float] = None
    pdop: Optional[float] = None
    has_data: bool = False



def ensure_out_dir() -> None:
    os.makedirs(os.path.join(WORKDIR, OUT_DIR), exist_ok=True)



def sec_key_from_datetime(t: dt.datetime) -> int:
    return int(round(t.timestamp()))



def sec_key_from_unix_ms(ms: int) -> int:
    return int(round(ms / 1000.0))



def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371000.0
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dphi = p2 - p1
    dl = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))



def parse_raw_fix(path: str) -> List[Dict]:
    rows: List[Dict] = []
    with open(path, "r", errors="ignore") as f:
        for line in f:
            if not line.startswith("Fix,"):
                continue
            p = line.strip().split(",")
            if len(p) < 9:
                continue
            try:
                t_ms = int(p[8])
                rows.append(
                    {
                        "t": dt.datetime.utcfromtimestamp(t_ms / 1000.0),
                        "lat": float(p[2]),
                        "lon": float(p[3]),
                        "h": float(p[4]) if p[4] else 0.0,
                    }
                )
            except Exception:
                continue
    return rows



def parse_status_records(path: str) -> Dict[int, List[SatObs]]:
    by_sec: Dict[int, List[SatObs]] = defaultdict(list)
    with open(path, "r", errors="ignore") as f:
        for line in f:
            if not line.startswith("Status,"):
                continue
            p = line.strip().split(",")
            if len(p) < 11:
                continue
            try:
                t_sec = sec_key_from_unix_ms(int(p[1]))
                cn0 = float(p[7]) if p[7] else None
                elev = float(p[9]) if p[9] else None
                used_s = p[10].strip().lower()
                used = True if used_s in ("1", "true", "t", "yes") else False
                by_sec[t_sec].append(SatObs(cn0=cn0, elev=elev, used=used))
            except Exception:
                continue
    return by_sec



def parse_nmea_quality(path: str) -> Tuple[Dict[int, List[SatObs]], Dict[int, Dict[str, float]]]:
    sats_by_sec: Dict[int, List[SatObs]] = defaultdict(list)
    dop_by_sec: Dict[int, Dict[str, float]] = defaultdict(dict)

    with open(path, "r", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if not line.startswith("NMEA,"):
                continue
            p = line.split(",")
            if len(p) < 3:
                continue
            if len(p[-1]) >= 10 and p[-1].isdigit():
                t_sec = sec_key_from_unix_ms(int(p[-1]))
                nmea_fields = p[1:-1]
            else:
                t_sec = None
                nmea_fields = p[1:]
            if t_sec is None or not nmea_fields:
                continue

            sentence = nmea_fields[0]
            if not sentence.startswith("$"):
                continue
            stype = sentence[-3:]
            fields = [x.split("*")[0] for x in nmea_fields]

            if stype == "GSV":
                # GSV groups of 4: svid, elev, az, snr
                i = 4
                while i + 3 < len(fields):
                    elev = None
                    snr = None
                    try:
                        elev = float(fields[i + 1]) if fields[i + 1] else None
                        snr = float(fields[i + 3]) if fields[i + 3] else None
                    except Exception:
                        pass
                    sats_by_sec[t_sec].append(SatObs(cn0=snr, elev=elev, used=None))
                    i += 4

            elif stype == "GSA":
                # Take last 3 numeric fields as PDOP, HDOP, VDOP (ignore trailing system id)
                vals = []
                for x in fields:
                    try:
                        vals.append(float(x))
                    except Exception:
                        continue
                if len(vals) >= 3:
                    pdop, hdop, _vdop = vals[-3], vals[-2], vals[-1]
                    dop_by_sec[t_sec]["pdop"] = pdop
                    dop_by_sec[t_sec]["hdop"] = hdop

            elif stype == "GGA":
                # GGA: quality at idx 6, nsat idx 7, hdop idx 8
                if len(fields) > 8:
                    try:
                        hdop = float(fields[8]) if fields[8] else None
                        if hdop is not None:
                            dop_by_sec[t_sec]["hdop"] = hdop
                    except Exception:
                        pass

    return sats_by_sec, dop_by_sec



def build_epoch_quality(
    status_by_sec: Dict[int, List[SatObs]],
    nmea_sats_by_sec: Dict[int, List[SatObs]],
    dop_by_sec: Dict[int, Dict[str, float]],
) -> Dict[int, EpochQuality]:
    all_secs = set(status_by_sec.keys()) | set(nmea_sats_by_sec.keys()) | set(dop_by_sec.keys())
    out: Dict[int, EpochQuality] = {}

    for s in sorted(all_secs):
        q = EpochQuality()
        sats = status_by_sec.get(s)
        if not sats:
            sats = nmea_sats_by_sec.get(s, [])

        q.sat_total = len(sats)
        pass_count = 0
        for sat in sats:
            cn0_ok = (sat.cn0 is not None and sat.cn0 >= CN0_MIN)
            elev_ok = (sat.elev is not None and sat.elev >= ELEV_MIN_DEG)
            used_ok = (sat.used is not False)
            if cn0_ok and elev_ok and used_ok:
                pass_count += 1
        q.sat_pass = pass_count

        if s in dop_by_sec:
            q.hdop = dop_by_sec[s].get("hdop")
            q.pdop = dop_by_sec[s].get("pdop")

        q.has_data = q.sat_total > 0 or q.hdop is not None or q.pdop is not None
        out[s] = q

    return out



def epoch_pass(q: EpochQuality) -> bool:
    # If no quality data exists for that second, keep to avoid aggressive dropping.
    if not q.has_data:
        return True

    sat_ok = q.sat_pass >= MIN_PASSING_SATS
    hdop_ok = (q.hdop is None) or (q.hdop <= HDOP_MAX)
    pdop_ok = (q.pdop is None) or (q.pdop <= PDOP_MAX)
    return sat_ok and hdop_ok and pdop_ok



def parse_rinex_epoch_blocks(path: str) -> Tuple[List[str], List[Tuple[dt.datetime, List[str]]]]:
    with open(path, "r", errors="ignore") as f:
        lines = f.readlines()

    end_idx = None
    for i, ln in enumerate(lines):
        if "END OF HEADER" in ln:
            end_idx = i
            break
    if end_idx is None:
        raise RuntimeError("RINEX header end not found")

    header = lines[: end_idx + 1]
    body = lines[end_idx + 1 :]

    blocks: List[Tuple[dt.datetime, List[str]]] = []
    curr_t: Optional[dt.datetime] = None
    curr_lines: List[str] = []

    for ln in body:
        if ln.startswith(">"):
            if curr_t is not None:
                blocks.append((curr_t, curr_lines))
            curr_lines = [ln]
            p = ln[1:].strip().split()
            y, m, d, hh, mm = map(int, p[:5])
            sec_f = float(p[5])
            sec_i = int(sec_f)
            usec = int(round((sec_f - sec_i) * 1_000_000))
            curr_t = dt.datetime(y, m, d, hh, mm, sec_i, usec)
        else:
            if curr_t is not None:
                curr_lines.append(ln)

    if curr_t is not None:
        blocks.append((curr_t, curr_lines))

    return header, blocks



def write_rinex_without_epochs(src_rel: str, dst_rel: str, drop_secs: set) -> Tuple[int, int]:
    src = os.path.join(WORKDIR, src_rel)
    dst = os.path.join(WORKDIR, dst_rel)
    header, blocks = parse_rinex_epoch_blocks(src)

    total = len(blocks)
    kept = 0
    with open(dst, "w", encoding="utf-8") as f:
        f.writelines(header)
        for t, lines in blocks:
            if sec_key_from_datetime(t) in drop_secs:
                continue
            f.writelines(lines)
            kept += 1
    return total, kept



def run_cors(rover_rinex_rel: str, out_pos_rel: str) -> Tuple[int, str]:
    cmd = [
        RTKLIB_EXE,
        "-p",
        "2",
        "-f",
        "1",
        "-sys",
        "G,R,E,C,J",
        "-o",
        out_pos_rel,
        rover_rinex_rel,
    ] + BASE_FILES

    proc = subprocess.run(
        cmd,
        cwd=WORKDIR,
        capture_output=True,
        text=True,
    )
    tail = (proc.stdout or "")[-2000:] + "\n" + (proc.stderr or "")[-2000:]
    return proc.returncode, tail



def parse_pos(path_rel: str) -> List[Dict]:
    path = os.path.join(WORKDIR, path_rel)
    rows: List[Dict] = []
    if not os.path.exists(path):
        return rows

    with open(path, "r", errors="ignore") as f:
        for line in f:
            if not line.strip() or line.startswith("%") or line.startswith("#"):
                continue
            p = line.split()
            if len(p) < 5:
                continue
            try:
                if "/" in p[0] and ":" in p[1]:
                    d = p[0].split("/")
                    tm = p[1].split(":")
                    sec_f = float(tm[2])
                    sec_i = int(sec_f)
                    usec = int(round((sec_f - sec_i) * 1_000_000))
                    t = dt.datetime(int(d[0]), int(d[1]), int(d[2]), int(tm[0]), int(tm[1]), sec_i, usec)
                    lat_i, lon_i, h_i = 2, 3, 4
                else:
                    week = int(float(p[0]))
                    sow = float(p[1])
                    gpst = GPS_EPOCH + dt.timedelta(weeks=week, seconds=sow)
                    t = gpst - dt.timedelta(seconds=GPST_MINUS_UTC_SECONDS)
                    lat_i, lon_i, h_i = 2, 3, 4
                rows.append(
                    {
                        "t": t,
                        "lat": float(p[lat_i]),
                        "lon": float(p[lon_i]),
                        "h": float(p[h_i]),
                    }
                )
            except Exception:
                continue
    return rows



def write_csv(path_rel: str, rows: List[Dict]) -> None:
    path = os.path.join(WORKDIR, path_rel)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["utc", "lat", "lon", "height"])
        for r in rows:
            w.writerow([r["t"].isoformat(), f"{r['lat']:.10f}", f"{r['lon']:.10f}", f"{r['h']:.3f}"])



def step_stats(rows: List[Dict]) -> Dict[str, float]:
    if len(rows) < 2:
        return {"n": 0, "mean": 0.0, "p95": 0.0, "mx": 0.0, "gt3": 0.0, "gt5": 0.0}
    ds = []
    for i in range(1, len(rows)):
        ds.append(haversine_m(rows[i - 1]["lat"], rows[i - 1]["lon"], rows[i]["lat"], rows[i]["lon"]))
    ds_sorted = sorted(ds)
    p95 = ds_sorted[int(0.95 * (len(ds_sorted) - 1))]
    return {
        "n": float(len(ds)),
        "mean": float(sum(ds) / len(ds)),
        "p95": float(p95),
        "mx": float(max(ds)),
        "gt3": float(sum(1 for x in ds if x > 3.0)),
        "gt5": float(sum(1 for x in ds if x > 5.0)),
    }



def plot_4traj_png(path_rel: str, layers: List[Dict]) -> bool:
    if plt is None:
        return False
    plt.figure(figsize=(9, 7))
    for ly in layers:
        rows = ly["rows"]
        if not rows:
            continue
        plt.plot(
            [r["lon"] for r in rows],
            [r["lat"] for r in rows],
            color=ly["color"],
            linewidth=ly.get("width", 2.0),
            alpha=ly.get("alpha", 0.9),
            linestyle=ly.get("style", "-"),
            label=ly["label"],
        )
    plt.title("Logger3 + Order4: Raw, NMEA-filtered, and CORS comparisons")
    plt.xlabel("Longitude")
    plt.ylabel("Latitude")
    plt.grid(alpha=0.3)
    plt.legend(fontsize=8)
    plt.tight_layout()
    plt.savefig(os.path.join(WORKDIR, path_rel), dpi=180, bbox_inches="tight")
    plt.close()
    return True



def write_leaflet_html(path_rel: str, center: Tuple[float, float], layers: List[Dict], title: str) -> None:
    layer_js = []
    add_js = []
    all_coords = []

    for i, ly in enumerate(layers):
        coords = [[r["lat"], r["lon"]] for r in ly["rows"]]
        all_coords.extend(coords)
        var_name = f"layer_{i}"
        layer_js.append(
            "var "
            + var_name
            + "=L.polyline("
            + json.dumps(coords)
            + ",{color:'"
            + ly["color"]
            + "',weight:"
            + str(ly.get("width", 2.0))
            + ",opacity:"
            + str(ly.get("alpha", 0.9))
            + ",dashArray:'"
            + ly.get("dash", "")
            + "'});"
        )
        add_js.append("overlayMaps['" + ly["label"] + "']=" + var_name + ";")

    html = """<!doctype html>
<html>
<head>
  <meta charset='utf-8'/>
  <meta name='viewport' content='width=device-width, initial-scale=1'/>
  <title>{title}</title>
  <link rel='stylesheet' href='https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css'/>
  <script src='https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js'></script>
  <style>
    html,body,#map{{height:100%;margin:0;}}
    .box{{position:fixed;top:10px;right:10px;z-index:500;background:white;padding:8px;border-radius:6px;font-size:12px;font-family:Arial;max-width:420px;}}
  </style>
</head>
<body>
<div id='map'></div>
<div class='box'><b>{title}</b><br/>Layers: Raw, Filtered using NMEA data, Correction with CORS on RAW, CORS correction on NMEA Filtered</div>
<script>
var map=L.map('map').setView([{clat:.8f},{clon:.8f}],16);
L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png',{{maxZoom:19,attribution:'OpenStreetMap contributors'}}).addTo(map);
var overlayMaps={{}};
{layer_js}
{add_js}
for (const k in overlayMaps) {{ overlayMaps[k].addTo(map); }}
var allCoords = {all_coords};
if (allCoords.length > 1) {{ map.fitBounds(allCoords, {{padding:[20,20]}}); }}
L.control.layers(null, overlayMaps, {{collapsed:false}}).addTo(map);
</script>
</body>
</html>""".format(
        title=title,
        clat=center[0],
        clon=center[1],
        layer_js="".join(layer_js),
        add_js="".join(add_js),
        all_coords=json.dumps(all_coords),
    )

    with open(os.path.join(WORKDIR, path_rel), "w", encoding="utf-8") as f:
        f.write(html)



def main() -> None:
    os.chdir(WORKDIR)
    ensure_out_dir()

    print("Parsing raw and quality sources...")
    raw_rows = parse_raw_fix(RAW_FIX_LOG)
    status_by_sec = parse_status_records(RAW_FIX_LOG)
    nmea_sats_by_sec, dop_by_sec = parse_nmea_quality(NMEA_LOG)
    quality_by_sec = build_epoch_quality(status_by_sec, nmea_sats_by_sec, dop_by_sec)

    print(f"Raw phone fixes: {len(raw_rows)}")
    print(f"Quality epochs: {len(quality_by_sec)}")

    # Filter raw phone trajectory by NMEA quality
    raw_filtered = []
    for r in raw_rows:
        q = quality_by_sec.get(sec_key_from_datetime(r["t"]))
        if q is None or epoch_pass(q):
            raw_filtered.append(r)

    write_csv(OUT_RAW_CSV, raw_rows)
    write_csv(OUT_NMEA_FILTERED_CSV, raw_filtered)
    print(f"NMEA-filtered raw points: {len(raw_filtered)} / {len(raw_rows)}")

    # Build filtered rover RINEX by dropping failing epochs
    header, blocks = parse_rinex_epoch_blocks(os.path.join(WORKDIR, ROVER_RINEX))
    drop_secs = set()
    for t, _lines in blocks:
        q = quality_by_sec.get(sec_key_from_datetime(t))
        if q is not None and not epoch_pass(q):
            drop_secs.add(sec_key_from_datetime(t))

    total_epochs, kept_epochs = write_rinex_without_epochs(ROVER_RINEX, OUT_ROVER_FILTERED, drop_secs)
    print(f"RINEX filtered epochs: kept={kept_epochs}/{total_epochs}, dropped={total_epochs-kept_epochs}")

    print("Running CORS on RAW rover...")
    code_raw, tail_raw = run_cors(ROVER_RINEX, OUT_CORS_RAW_POS)
    if code_raw != 0:
        raise RuntimeError("CORS raw run failed:\n" + tail_raw)

    print("Running CORS on NMEA-filtered rover...")
    code_flt, tail_flt = run_cors(OUT_ROVER_FILTERED, OUT_CORS_FILTERED_POS)
    if code_flt != 0:
        raise RuntimeError("CORS filtered run failed:\n" + tail_flt)

    cors_raw = parse_pos(OUT_CORS_RAW_POS)
    cors_filtered = parse_pos(OUT_CORS_FILTERED_POS)

    print(f"CORS RAW points: {len(cors_raw)}")
    print(f"CORS NMEA-filtered points: {len(cors_filtered)}")

    layers = [
        {"label": "Raw", "rows": raw_rows, "color": "#777777", "width": 2.0, "alpha": 0.6, "style": "--", "dash": "6,4"},
        {"label": "Filtered using NMEA data", "rows": raw_filtered, "color": "#9467bd", "width": 2.2, "alpha": 0.9},
        {"label": "Correction with CORS on RAW", "rows": cors_raw, "color": "#000000", "width": 2.6, "alpha": 0.9},
        {"label": "CORS correction on NMEA Filtered", "rows": cors_filtered, "color": "#d62728", "width": 2.8, "alpha": 0.95},
    ]

    layers = [x for x in layers if x["rows"]]

    # center from first available trajectory
    center_src = layers[0]["rows"][0]
    center = (center_src["lat"], center_src["lon"])

    png_ok = plot_4traj_png(OUT_MAP_PNG, layers)
    write_leaflet_html(OUT_MAP_HTML, center, layers, "Logger3 + Order4: NMEA filtering and CORS comparison")

    s_raw = step_stats(raw_rows)
    s_nmea = step_stats(raw_filtered)
    s_craw = step_stats(cors_raw)
    s_cflt = step_stats(cors_filtered)

    with open(os.path.join(WORKDIR, OUT_METRICS), "w", encoding="utf-8") as f:
        f.write("Logger3 + Order4 metrics\n")
        f.write(f"Thresholds: CN0>={CN0_MIN}, Elev>={ELEV_MIN_DEG}, HDOP<={HDOP_MAX}, PDOP<={PDOP_MAX}, minSat={MIN_PASSING_SATS}\n")
        f.write(f"Raw points: {len(raw_rows)}\n")
        f.write(f"NMEA filtered raw points: {len(raw_filtered)}\n")
        f.write(f"RINEX epochs kept: {kept_epochs}/{total_epochs}\n")
        f.write(f"CORS RAW points: {len(cors_raw)}\n")
        f.write(f"CORS NMEA filtered points: {len(cors_filtered)}\n\n")

        def write_stats(name: str, s: Dict[str, float]) -> None:
            f.write(
                f"{name}: n={int(s['n'])}, mean={s['mean']:.3f}m, p95={s['p95']:.3f}m, max={s['mx']:.3f}m, "
                f">3m={int(s['gt3'])}, >5m={int(s['gt5'])}\n"
            )

        write_stats("Raw", s_raw)
        write_stats("Filtered using NMEA data", s_nmea)
        write_stats("Correction with CORS on RAW", s_craw)
        write_stats("CORS correction on NMEA Filtered", s_cflt)

    print("Saved outputs:")
    print("  " + OUT_RAW_CSV)
    print("  " + OUT_NMEA_FILTERED_CSV)
    print("  " + OUT_ROVER_FILTERED)
    print("  " + OUT_CORS_RAW_POS)
    print("  " + OUT_CORS_FILTERED_POS)
    if png_ok:
        print("  " + OUT_MAP_PNG)
    else:
        print("  PNG skipped (matplotlib unavailable in current environment)")
    print("  " + OUT_MAP_HTML)
    print("  " + OUT_METRICS)


if __name__ == "__main__":
    main()
