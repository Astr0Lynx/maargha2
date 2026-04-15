#!/usr/bin/env python3
"""
MAARGHA CORS Pipeline v2 - Lane-Level Accuracy
================================================
Logger/3 rover + cors/Order4 CORS reference station.

Pipeline:
  1. Parse NMEA: per-satellite SNR+elevation from GSV; HDOP/PDOP from GSA; GGA fixes.
  2. Compute per-epoch quality score usng strict thresholds (SNR>=30 dBHz, elev>=15°).
  3. Build Trajectory 1: Raw GGA positions from NMEA (unfiltered).
  4. Build Trajectory 2: Filtered GGA positions (strict per-epoch quality gate).
  5. Write filtered RINEX observation file (drop bad epochs).
  6. Run RTKLIB DGPS on raw RINEX → Trajectory 3 (CORS on raw).
  7. Run RTKLIB DGPS on filtered RINEX → Trajectory 4 (CORS on filtered).
  8. Post-process both CORS outputs:
       a. Bias estimation: compute lat/lon offset between median CORS cluster and
          median filtered-GGA cluster (robust via IQR trimming).
       b. Apply bias correction to align CORS result toward GGA reference.
       c. Spike removal: remove position-step outliers (>3 IQR from median step).
       d. Trend-preserving smoothing (weighted moving average, zero-phase).
  9. Plot all 4 trajectories on an interactive Leaflet HTML map.
"""

import csv
import datetime as dt
import json
import math
import os
import subprocess
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import numpy as np

# ============================================================
# CONFIG
# ============================================================
WORKDIR = r"C:\Users\Guntesh\Desktop\foo\gsd"

ROVER_RINEX  = r"logger\3\gnss_log_2026_04_04_17_53_31.26o"
NMEA_LOG     = r"logger\3\gnss_log_2026_04_04_17_53_31.nmea"

BASE_FILES = [
    r"cors\Order4\HYDE094M.26o",
    r"cors\Order4\HYDE094M.26n",
    r"cors\Order4\HYDE094M.26g",
    r"cors\Order4\HYDE094M.26l",
    r"cors\Order4\HYDE094M.26c",
    r"cors\Order4\HYDE094M.26j",
]

OUT_DIR               = r"out"
OUT_ROVER_FILTERED    = r"out\rover_v2_nmea_filtered.26o"
OUT_CORS_RAW_POS      = r"out\solution_cors_raw_order4.pos"     # may already exist
OUT_CORS_FILT_POS     = r"out\solution_v2_cors_filtered.pos"
OUT_MAP_HTML          = r"out\logger3_order4_4traj.html"        # overwrite existing

RTKLIB_EXE = r"C:\tools\RTKLIB_EX_2.5.0\rnx2rtkp.exe"

# Quality thresholds  (industry standard for lane-level GNSS)
SNR_MIN_DBHz        = 30.0   # C/N0 threshold in dBHz
ELEV_MIN_DEG        = 15.0   # elevation mask
HDOP_MAX            = 2.0    # max HDOP
PDOP_MAX            = 4.0    # max PDOP
MIN_GOOD_SATS       = 5      # min satellites passing the SNR+elev filter

# Post-processing
SPIKE_IQR_MULT      = 2.5    # step distances > this * IQR above Q75 are spikes
SMOOTH_WINDOW_SEC   = 3      # smoothing kernel half-width in seconds (odd total)
BIAS_IQR_TRIM       = 0.25   # trim fraction for robust median

GPS_EPOCH = dt.datetime(1980, 1, 6, tzinfo=dt.timezone.utc)
GPST_LEAP = 18  # GPS-UTC leap seconds at the event date (Apr 2026)


# ============================================================
# DATA STRUCTURES
# ============================================================
@dataclass
class SatInfo:
    svid:  str
    elev:  Optional[float]
    az:    Optional[float]
    snr:   Optional[float]
    used:  bool = False


@dataclass
class EpochQuality:
    sats: List[SatInfo] = field(default_factory=list)
    hdop: Optional[float] = None
    pdop: Optional[float] = None
    vdop: Optional[float] = None
    gga_lat:  Optional[float] = None
    gga_lon:  Optional[float] = None
    gga_alt:  Optional[float] = None
    gga_qual: int = 0
    gga_time: Optional[dt.datetime] = None

    def good_sat_count(self) -> int:
        return sum(
            1 for s in self.sats
            if (s.snr is not None and s.snr >= SNR_MIN_DBHz)
            and (s.elev is not None and s.elev >= ELEV_MIN_DEG)
        )

    def passes(self) -> bool:
        """True if this epoch meets lane-level quality requirements."""
        if self.good_sat_count() < MIN_GOOD_SATS:
            return False
        if self.hdop is not None and self.hdop > HDOP_MAX:
            return False
        if self.pdop is not None and self.pdop > PDOP_MAX:
            return False
        return True


# ============================================================
# HELPERS
# ============================================================
def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(min(1.0, math.sqrt(a)))


def nmea_ll_to_decimal(raw: str, hemi: str) -> float:
    """Convert NMEA DDDMM.MMMMM + hemisphere to decimal degrees."""
    raw = raw.strip()
    if not raw:
        raise ValueError("empty")
    dot = raw.index(".")
    # degrees are everything before the last 2 digits before decimal
    deg_part = int(raw[: dot - 2])
    min_part = float(raw[dot - 2 :])
    val = deg_part + min_part / 60.0
    if hemi.upper() in ("S", "W"):
        val = -val
    return val


def nmea_time_to_datetime(hhmmss: str, date_str: Optional[str] = None) -> dt.datetime:
    """Parse NMEA time field HHMMSS.ss, optionally with DDMMYY date."""
    h = int(hhmmss[0:2])
    m = int(hhmmss[2:4])
    s = float(hhmmss[4:])
    si = int(s)
    us = int((s - si) * 1_000_000)
    if date_str:
        d = int(date_str[0:2])
        mo = int(date_str[2:4])
        yr = 2000 + int(date_str[4:6])
        return dt.datetime(yr, mo, d, h, m, si, us, tzinfo=dt.timezone.utc)
    return dt.datetime(2026, 4, 4, h, m, si, us, tzinfo=dt.timezone.utc)


def unix_ms_to_datetime(ms: int) -> dt.datetime:
    return dt.datetime.utcfromtimestamp(ms / 1000.0).replace(tzinfo=dt.timezone.utc)


def gpst_to_utc(week: int, sow: float) -> dt.datetime:
    t = GPS_EPOCH + dt.timedelta(weeks=week, seconds=sow - GPST_LEAP)
    return t


# ============================================================
# NMEA PARSER
# ============================================================
def parse_nmea(path: str) -> Dict[int, EpochQuality]:
    """
    Parse NMEA file and return a dict keyed by UTC unix-second.
    Handles the proprietary prefix "NMEA," and trailing ",<unix_ms>" 
    that the Android GnssLogger app adds.

    Parses:
      - $G?GSV  → per-satellite SNR + elevation
      - $GNGSA  → DOP + used PRNs per constellation
      - $GNGGA  → position fix + quality
      - $GNRMC  → date for time correlation
    """
    epochs: Dict[int, EpochQuality] = {}

    # We accumulate GSV across multiple sentences per second
    # GSA gives used PRNs; we track them to mark which sats are 'used'
    pending_gsv: Dict[int, List[SatInfo]] = defaultdict(list)
    used_prns_by_sec: Dict[int, set] = defaultdict(set)
    dop_by_sec: Dict[int, dict] = defaultdict(dict)
    gga_by_sec: Dict[int, dict] = defaultdict(dict)
    rmc_date: Optional[str] = None  # DDMMYY from last RMC

    with open(path, "r", errors="ignore") as f:
        for raw_line in f:
            raw_line = raw_line.strip()
            if not raw_line:
                continue

            # Strip the "NMEA," prefix and trailing unix-ms timestamp
            if raw_line.startswith("NMEA,"):
                inner = raw_line[5:]  # remove "NMEA,"
            else:
                continue

            # The last field is unix timestamp in ms (10+ digits)
            parts = inner.split(",")
            if len(parts) < 2:
                continue

            # Extract unix timestamp (last part, possibly with checksum)
            last = parts[-1]
            ts_ms = None
            # It's purely numeric 10+ chars
            ts_candidate = last.split("*")[0].strip()
            if ts_candidate.isdigit() and len(ts_candidate) >= 10:
                ts_ms = int(ts_candidate)
                parts = parts[:-1]  # remove timestamp
            
            if ts_ms is None:
                continue
            
            sec_key = int(ts_ms // 1000)

            # Reconstruct sentence (without trailing timestamp)
            sentence = ",".join(parts)

            # Strip checksum from last field if present
            if "*" in sentence:
                sentence = sentence[: sentence.rfind("*")]

            flds = sentence.split(",")
            if not flds or not flds[0].startswith("$"):
                continue

            msg_type = flds[0][-3:]  # last 3 chars of talker, e.g. "GSV", "GSA"

            # ---- GSV: satellite in view ----
            if msg_type == "GSV":
                # $GPGSV,4,1,13,svid,elev,az,snr,...
                # Groups of 4 starting at index 4
                i = 4
                while i + 3 < len(flds):
                    svid_s = flds[i].strip()
                    elev_s = flds[i+1].strip()
                    az_s   = flds[i+2].strip()
                    snr_s  = flds[i+3].strip()
                    try:
                        elev = float(elev_s) if elev_s else None
                    except ValueError:
                        elev = None
                    try:
                        snr = float(snr_s) if snr_s else None
                    except ValueError:
                        snr = None
                    try:
                        az = float(az_s) if az_s else None
                    except ValueError:
                        az = None
                    # Map talker to constellation prefix
                    talker = flds[0][1:3]  # GP, GL, GA, GB, GQ, GN
                    cons_map = {"GP":"G","GL":"R","GA":"E","GB":"C","GQ":"Q","GN":"G"}
                    prefix = cons_map.get(talker, talker[1])
                    svid = prefix + svid_s if svid_s else ""
                    if svid:
                        pending_gsv[sec_key].append(SatInfo(
                            svid=svid, elev=elev, az=az, snr=snr))
                    i += 4

            # ---- GSA: DOP + used PRNs ----
            elif msg_type == "GSA":
                # $GNGSA,A,3,sv1,sv2,...,sv12,PDOP,HDOP,VDOP,sys_id
                # Used PRNs are fields 3..14 (12 slots), DOP at -4,-3,-2 from end
                try:
                    dop_vals = []
                    for x in reversed(flds):
                        try:
                            v = float(x)
                            dop_vals.insert(0, v)
                            if len(dop_vals) == 3:
                                break
                        except (ValueError, TypeError):
                            if dop_vals:
                                break
                    if len(dop_vals) >= 3:
                        pdop, hdop, vdop = dop_vals[0], dop_vals[1], dop_vals[2]
                        if "pdop" not in dop_by_sec[sec_key]:
                            dop_by_sec[sec_key]["pdop"] = pdop
                        if "hdop" not in dop_by_sec[sec_key]:
                            dop_by_sec[sec_key]["hdop"] = hdop
                        dop_by_sec[sec_key]["vdop"] = vdop
                except Exception:
                    pass
                # Used PRNs (slots 3..14)
                for i in range(3, min(15, len(flds))):
                    prn = flds[i].strip()
                    if prn:
                        try:
                            used_prns_by_sec[sec_key].add(int(prn))
                        except ValueError:
                            pass

            # ---- GGA: position fix ----
            elif msg_type == "GGA":
                # $GNGGA,HHMMSS,lat,N,lon,E,qual,nsats,hdop,alt,M,sep,M,...
                if len(flds) >= 10:
                    try:
                        fix_time = nmea_time_to_datetime(flds[1], None)
                        lat = nmea_ll_to_decimal(flds[2], flds[3])
                        lon = nmea_ll_to_decimal(flds[4], flds[5])
                        qual = int(flds[6]) if flds[6] else 0
                        hdop_gga = float(flds[8]) if flds[8] else None
                        alt = float(flds[9]) if len(flds) > 9 and flds[9] else None
                        gga_by_sec[sec_key] = {
                            "lat": lat, "lon": lon, "alt": alt,
                            "qual": qual, "hdop": hdop_gga,
                            "time": fix_time,
                        }
                        if hdop_gga is not None and "hdop" not in dop_by_sec[sec_key]:
                            dop_by_sec[sec_key]["hdop"] = hdop_gga
                    except Exception:
                        pass

            # ---- RMC: date ----
            elif msg_type == "RMC":
                if len(flds) > 9 and flds[9]:
                    rmc_date = flds[9]  # DDMMYY

    # Now assemble EpochQuality objects
    all_secs = (
        set(pending_gsv.keys()) 
        | set(dop_by_sec.keys()) 
        | set(gga_by_sec.keys())
    )
    for sec in sorted(all_secs):
        eq = EpochQuality()
        eq.sats = list(pending_gsv.get(sec, []))
        # Mark used sats
        used_prns = used_prns_by_sec.get(sec, set())
        for sat in eq.sats:
            try:
                prn_num = int(sat.svid[1:]) if sat.svid else 0
                sat.used = prn_num in used_prns
            except Exception:
                pass
        dops = dop_by_sec.get(sec, {})
        eq.hdop = dops.get("hdop")
        eq.pdop = dops.get("pdop")
        eq.vdop = dops.get("vdop")
        gga = gga_by_sec.get(sec, {})
        eq.gga_lat  = gga.get("lat")
        eq.gga_lon  = gga.get("lon")
        eq.gga_alt  = gga.get("alt")
        eq.gga_qual = gga.get("qual", 0)
        eq.gga_time = gga.get("time")
        epochs[sec] = eq

    return epochs


# ============================================================
# RINEX FILTERING
# ============================================================
def parse_rinex_blocks(path: str):
    """Parse RINEX 3 observation file into (header_lines, [(epoch_dt, lines)])."""
    with open(path, "r", errors="ignore") as f:
        lines = f.readlines()
    
    hdr = []
    body_start = 0
    for i, ln in enumerate(lines):
        hdr.append(ln)
        if "END OF HEADER" in ln:
            body_start = i + 1
            break

    blocks = []
    cur_t = None
    cur_lines = []
    for ln in lines[body_start:]:
        if ln.startswith(">"):
            if cur_t is not None:
                blocks.append((cur_t, cur_lines))
            cur_lines = [ln]
            p = ln[1:].strip().split()
            try:
                yr, mo, dy, hh, mm = map(int, p[:5])
                sf = float(p[5])
                si = int(sf)
                us = int(round((sf - si) * 1e6))
                cur_t = dt.datetime(yr, mo, dy, hh, mm, si, us, tzinfo=dt.timezone.utc)
            except Exception:
                cur_t = None
        else:
            if cur_t is not None:
                cur_lines.append(ln)
    if cur_t is not None:
        blocks.append((cur_t, cur_lines))
    return hdr, blocks


def write_filtered_rinex(src_path: str, dst_path: str, drop_secs: set) -> Tuple[int, int]:
    """Write RINEX without epochs whose UTC second is in drop_secs."""
    hdr, blocks = parse_rinex_blocks(src_path)
    kept = 0
    with open(dst_path, "w", encoding="utf-8") as f:
        f.writelines(hdr)
        for epoch_t, lns in blocks:
            key = int(epoch_t.timestamp())
            if key in drop_secs:
                continue
            f.writelines(lns)
            kept += 1
    return len(blocks), kept


# ============================================================
# RTKLIB RUNNER
# ============================================================
def run_rtklib(rover: str, out_pos: str, workdir: str) -> Tuple[int, str]:
    """Run rnx2rtkp DGPS with all constellations, elev mask 10°."""
    cmd = [
        RTKLIB_EXE,
        "-p", "2",          # DGPS
        "-f", "1",          # L1 only (typical for phone)
        "-sys", "G,R,E,C,J",
        "-m", "10",         # elevation mask 10°
        "-o", out_pos,
        rover,
    ] + BASE_FILES

    proc = subprocess.run(
        cmd, cwd=workdir, capture_output=True, text=True, timeout=300
    )
    out = (proc.stdout or "")[-3000:] + "\n" + (proc.stderr or "")[-3000:]
    return proc.returncode, out


# ============================================================
# POS FILE PARSER
# ============================================================
def parse_pos(path: str) -> List[Dict]:
    """Parse RTKLIB .pos file to list of {lat, lon, h, q, ns, sdn, sde, t}."""
    rows = []
    if not os.path.exists(path):
        return rows
    with open(path, "r", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("%") or line.startswith("#"):
                continue
            p = line.split()
            if len(p) < 7:
                continue
            try:
                # GPS week + SOW format
                week = int(float(p[0]))
                sow  = float(p[1])
                t = gpst_to_utc(week, sow)
                lat = float(p[2])
                lon = float(p[3])
                h   = float(p[4])
                q   = int(p[5])
                ns  = int(p[6]) if len(p) > 6 else 0
                sdn = float(p[7]) if len(p) > 7 else 999.0
                sde = float(p[8]) if len(p) > 8 else 999.0
                rows.append({"t": t, "lat": lat, "lon": lon, "h": h,
                             "q": q, "ns": ns, "sdn": sdn, "sde": sde})
            except Exception:
                continue
    return rows


# ============================================================
# BIAS CORRECTION & SPIKE REMOVAL
# ============================================================
def robust_median(vals: np.ndarray, trim: float = BIAS_IQR_TRIM) -> float:
    """Compute trimmed median."""
    s = np.sort(vals)
    n = len(s)
    lo = int(trim * n)
    hi = n - lo
    if hi <= lo:
        return float(np.median(s))
    return float(np.median(s[lo:hi]))


def estimate_bias(
    cors_rows: List[Dict],
    ref_rows: List[Dict],
) -> Tuple[float, float]:
    """
    Estimate systematic lat/lon offset between CORS output and reference path.
    
    Strategy: match by closest timestamp, compute per-point delta,
    take the trimmed median of all deltas.
    """
    if not cors_rows or not ref_rows:
        return 0.0, 0.0
    
    # Build time-indexed reference
    ref_ts = np.array([r["t"].timestamp() for r in ref_rows])
    ref_lats = np.array([r["lat"] for r in ref_rows])
    ref_lons = np.array([r["lon"] for r in ref_rows])

    dlats, dlons = [], []
    for cr in cors_rows:
        ct = cr["t"].timestamp()
        idx = int(np.argmin(np.abs(ref_ts - ct)))
        if abs(ref_ts[idx] - ct) < 5.0:  # within 5 seconds
            dlats.append(ref_lats[idx] - cr["lat"])
            dlons.append(ref_lons[idx] - cr["lon"])

    if len(dlats) < 10:
        return 0.0, 0.0

    dlat_arr = np.array(dlats)
    dlon_arr = np.array(dlons)

    # Filter outlier deltas (beyond 3σ) before computing median
    def sigma_clip(arr, n_sigma=3):
        med = np.median(arr)
        mad = np.median(np.abs(arr - med))
        std_est = mad * 1.4826  # MAD to σ scaling
        mask = np.abs(arr - med) < n_sigma * std_est
        return arr[mask]

    dlat_clip = sigma_clip(dlat_arr)
    dlon_clip = sigma_clip(dlon_arr)

    bias_lat = robust_median(dlat_clip)
    bias_lon = robust_median(dlon_clip)

    print(f"  Bias correction: Δlat={bias_lat:.7f}° ({bias_lat*111111:.2f}m), "
          f"Δlon={bias_lon:.7f}° ({bias_lon*111111*math.cos(math.radians(ref_lats[0])):.2f}m)")
    return bias_lat, bias_lon


def apply_bias(rows: List[Dict], dlat: float, dlon: float) -> List[Dict]:
    corrected = []
    for r in rows:
        cr = dict(r)
        cr["lat"] = r["lat"] + dlat
        cr["lon"] = r["lon"] + dlon
        corrected.append(cr)
    return corrected


def remove_spikes(rows: List[Dict], iqr_mult: float = SPIKE_IQR_MULT) -> List[Dict]:
    """
    Remove positional spike points using IQR on step-distance distribution.
    
    Steps beyond Q75 + iqr_mult * IQR are flagged as spikes and replaced
    by linear interpolation between the previous and next good points.
    """
    if len(rows) < 4:
        return rows

    # Compute step distances
    lats = np.array([r["lat"] for r in rows])
    lons = np.array([r["lon"] for r in rows])

    steps = np.zeros(len(rows))
    for i in range(1, len(rows)):
        steps[i] = haversine_m(lats[i-1], lons[i-1], lats[i], lons[i])

    q25, q75 = np.percentile(steps[1:], [25, 75])
    iqr = q75 - q25
    thresh = q75 + iqr_mult * iqr

    # Mark spikes
    is_spike = np.zeros(len(rows), dtype=bool)
    for i in range(1, len(rows)):
        if steps[i] > thresh:
            is_spike[i] = True

    # Also mark as spike if this point is suspicious from both sides (velocity spike)
    for i in range(1, len(rows) - 1):
        fwd = haversine_m(lats[i-1], lons[i-1], lats[i+1], lons[i+1])
        if steps[i] > thresh and steps[i] > 2 * fwd:
            is_spike[i] = True

    # Interpolate over spikes
    out_lats = lats.copy()
    out_lons = lons.copy()

    i = 0
    n = len(rows)
    while i < n:
        if is_spike[i]:
            # Find extent of spike region
            j = i
            while j < n and is_spike[j]:
                j += 1
            # interpolate between i-1 and j
            if i > 0 and j < n:
                t0, t1 = i - 1, j
                for k in range(i, j):
                    alpha = (k - t0) / (t1 - t0)
                    out_lats[k] = lats[t0] + alpha * (lats[t1] - lats[t0])
                    out_lons[k] = lons[t0] + alpha * (lons[t1] - lons[t0])
            i = j
        else:
            i += 1

    # Return updated rows
    result = []
    for idx, r in enumerate(rows):
        nr = dict(r)
        nr["lat"] = out_lats[idx]
        nr["lon"] = out_lons[idx]
        result.append(nr)

    n_spikes = int(np.sum(is_spike))
    print(f"  Spikes removed: {n_spikes} / {n} points (threshold {thresh:.2f}m)")
    return result


def smooth_trajectory(rows: List[Dict], window: int = SMOOTH_WINDOW_SEC) -> List[Dict]:
    """
    Zero-phase Gaussian-weighted moving average smoothing.
    window is the half-width in points; total window = 2*window+1.
    
    This preserves the overall path shape while reducing noise.
    """
    if len(rows) < 3:
        return rows

    lats = np.array([r["lat"] for r in rows])
    lons = np.array([r["lon"] for r in rows])

    # Gaussian weights
    sigma = max(1.0, window / 2.0)
    hw = window
    x = np.arange(-hw, hw + 1)
    weights = np.exp(-x**2 / (2 * sigma**2))
    weights /= weights.sum()

    def conv_valid(arr):
        """Zero-phase convolution with edge reflection."""
        n = len(arr)
        # reflect edges
        pad_left  = arr[:hw][::-1]
        pad_right = arr[-hw:][::-1]
        padded = np.concatenate([pad_left, arr, pad_right])
        result = np.convolve(padded, weights, mode="valid")
        return result[:n]

    smooth_lats = conv_valid(lats)
    smooth_lons = conv_valid(lons)

    result = []
    for idx, r in enumerate(rows):
        nr = dict(r)
        nr["lat"] = float(smooth_lats[idx])
        nr["lon"] = float(smooth_lons[idx])
        result.append(nr)
    return result


# ============================================================
# BUILD TRAJECTORY FROM GGA
# ============================================================
def gga_to_rows(epochs: Dict[int, EpochQuality], filtered: bool = False) -> List[Dict]:
    """
    Extract position time series from parsed NMEA GGA fixes.
    If filtered=True, only include epochs passing quality gate.
    """
    rows = []
    for sec in sorted(epochs.keys()):
        eq = epochs[sec]
        if eq.gga_lat is None or eq.gga_lon is None:
            continue
        if filtered and not eq.passes():
            continue
        # Only use GGA quality >= 1 (at least autonomous GNSS fix)
        if eq.gga_qual < 1:
            continue
        rows.append({
            "t": eq.gga_time or dt.datetime(2026, 4, 4, 
                                              sec // 3600 % 24, 
                                              sec // 60 % 60, 
                                              sec % 60, 
                                              tzinfo=dt.timezone.utc),
            "lat": eq.gga_lat,
            "lon": eq.gga_lon,
            "h": eq.gga_alt or 0.0,
        })
    return rows


# ============================================================
# LEAFLET MAP WRITER
# ============================================================
def write_leaflet_html(path: str, layers: List[Dict]) -> None:
    all_lats = []
    all_lons = []
    layer_js = []

    for i, ly in enumerate(layers):
        pts = [[r["lat"], r["lon"]] for r in ly["rows"]]
        all_lats.extend(p[0] for p in pts)
        all_lons.extend(p[1] for p in pts)
        color = ly.get("color", "#888888")
        weight = ly.get("weight", 2.5)
        opacity = ly.get("opacity", 0.9)
        dash = ly.get("dash", "")
        label = ly.get("label", f"Layer {i}")
        var = f"lyr{i}"
        layer_js.append(f"""
var {var} = L.polyline({json.dumps(pts)}, {{
  color: '{color}', weight: {weight}, opacity: {opacity},
  dashArray: '{dash}'
}}).bindTooltip('{label}', {{sticky: true}});""")

    # Compute bounding box
    if all_lats:
        clat = sum(all_lats) / len(all_lats)
        clon = sum(all_lons) / len(all_lons)
        bounds = [[min(all_lats), min(all_lons)], [max(all_lats), max(all_lons)]]
    else:
        clat, clon = 17.46, 78.34
        bounds = [[17.45, 78.33], [17.47, 78.35]]

    # Layer control
    overlay_entries = "".join(
        f"    '{ly['label']}': lyr{i},\n"
        for i, ly in enumerate(layers)
    )
    layer_adds = "".join(f"lyr{i}.addTo(map);\n" for i in range(len(layers)))

    html = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset='utf-8'/>
  <meta name='viewport' content='width=device-width, initial-scale=1'/>
  <title>MAARGHA CORS Accuracy - Logger3 vs Order4</title>
  <link rel='stylesheet' href='https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css'/>
  <script src='https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js'></script>
  <style>
    html, body, #map {{ height: 100%; margin: 0; padding: 0; }}
    .info-box {{
      position: fixed; top: 12px; right: 12px; z-index: 1000;
      background: rgba(255,255,255,0.97); padding: 12px 16px;
      border-radius: 8px; font: 13px/1.6 Arial, sans-serif;
      box-shadow: 0 2px 8px rgba(0,0,0,0.25); max-width: 280px;
    }}
    .info-box h3 {{ margin: 0 0 6px; font-size: 14px; }}
    .leg {{ display: flex; align-items: center; gap: 8px; margin: 3px 0; }}
    .swatch {{ width: 28px; height: 4px; border-radius: 2px; flex-shrink: 0; }}
  </style>
</head>
<body>
<div id='map'></div>
<div class='info-box'>
  <h3>🛰 MAARGHA CORS Pipeline</h3>
  <div style='font-size:11px;color:#555;margin-bottom:8px;'>Logger/3 + Order4 CORS | {len(layers)} trajectories</div>
{"".join(f'''  <div class="leg">
    <div class="swatch" style="background:{ly['color']};{'border-top:2px dashed '+ly['color']+';background:transparent;' if ly.get('dash') else ''}"></div>
    <span>{ly['label']}</span>
  </div>
''' for ly in layers)}
  <div style='margin-top:8px;font-size:10px;color:#888;'>Use layer control (top-right) to toggle trajectories.</div>
</div>
<script>
var map = L.map('map', {{preferCanvas: true}});
L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
  maxZoom: 20, attribution: '© OpenStreetMap'
}}).addTo(map);
{"".join(layer_js)}
{layer_adds}
map.fitBounds({json.dumps(bounds)}, {{padding: [20, 20]}});

var overlayMaps = {{
{overlay_entries}}};
L.control.layers(null, overlayMaps, {{collapsed: false, position: 'topright'}}).addTo(map);
</script>
</body>
</html>"""

    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"  Saved: {path}")


# ============================================================
# MAIN
# ============================================================
def main():
    os.chdir(WORKDIR)
    os.makedirs(OUT_DIR, exist_ok=True)

    print("=" * 60)
    print("MAARGHA CORS Pipeline v2 - Lane-Level Accuracy")
    print("=" * 60)

    # ----------------------------------------------------------
    # 1. Parse NMEA
    # ----------------------------------------------------------
    print("\n[1/6] Parsing NMEA file ...")
    nmea_path = os.path.join(WORKDIR, NMEA_LOG)
    epochs = parse_nmea(nmea_path)
    print(f"  Parsed {len(epochs)} NMEA epochs")

    if epochs:
        sample_secs = sorted(epochs.keys())[:3]
        for s in sample_secs:
            eq = epochs[s]
            print(f"  Epoch {s}: {len(eq.sats)} sats, good={eq.good_sat_count()}, "
                  f"hdop={eq.hdop}, pdop={eq.pdop}, "
                  f"pos={'yes' if eq.gga_lat else 'no'}, pass={eq.passes()}")

    # ----------------------------------------------------------
    # 2. Build raw + filtered GGA trajectories
    # ----------------------------------------------------------
    print("\n[2/6] Building GGA trajectories ...")
    traj_raw = gga_to_rows(epochs, filtered=False)
    traj_filt = gga_to_rows(epochs, filtered=True)
    print(f"  Raw GGA:       {len(traj_raw)} points")
    print(f"  Filtered GGA:  {len(traj_filt)} points "
          f"({100*len(traj_filt)/max(1,len(traj_raw)):.1f}% retained)")

    if not traj_raw:
        print("ERROR: No GGA positions found in NMEA. Check NMEA file path.")
        return

    # Quality stats
    pass_count = sum(1 for eq in epochs.values() if eq.passes())
    print(f"  Epochs passing quality gate: {pass_count}/{len(epochs)} "
          f"({100*pass_count/max(1,len(epochs)):.1f}%)")

    # ----------------------------------------------------------
    # 3. Write filtered RINEX
    # ----------------------------------------------------------
    print("\n[3/6] Writing filtered RINEX ...")
    rover_src = os.path.join(WORKDIR, ROVER_RINEX)
    rover_dst = os.path.join(WORKDIR, OUT_ROVER_FILTERED)

    # Build drop set: seconds where epoch quality fails
    drop_secs = set()
    for sec, eq in epochs.items():
        if not eq.passes():
            drop_secs.add(sec)

    total_eps, kept_eps = write_filtered_rinex(rover_src, rover_dst, drop_secs)
    dropped = total_eps - kept_eps
    print(f"  RINEX epochs: kept={kept_eps}/{total_eps} (dropped={dropped})")

    # ----------------------------------------------------------
    # 4. Run RTKLIB CORS on raw rover
    # ----------------------------------------------------------
    cors_raw_path = os.path.join(WORKDIR, OUT_CORS_RAW_POS)
    if os.path.exists(cors_raw_path) and os.path.getsize(cors_raw_path) > 1000:
        print("\n[4/6] CORS on raw rover -> using existing solution (already computed)")
    else:
        print("\n[4/6] Running RTKLIB CORS on raw rover ...")
        rc, log = run_rtklib(ROVER_RINEX, cors_raw_path, WORKDIR)
        print(f"  Exit code: {rc}")
        if rc != 0:
            print(f"  WARNING: RTKLIB failed:\n{log[-500:]}")

    # ----------------------------------------------------------
    # 5. Run RTKLIB CORS on filtered rover
    # ----------------------------------------------------------
    cors_filt_path = os.path.join(WORKDIR, OUT_CORS_FILT_POS)
    print("\n[5/6] Running RTKLIB CORS on filtered rover ...")
    rc, log = run_rtklib(OUT_ROVER_FILTERED, cors_filt_path, WORKDIR)
    print(f"  Exit code: {rc}")
    if rc != 0:
        print(f"  WARNING: RTKLIB failed:\n{log[-500:]}")

    # ----------------------------------------------------------
    # 6. Post-process CORS results
    # ----------------------------------------------------------
    print("\n[6/6] Post-processing CORS results ...")

    cors_raw  = parse_pos(cors_raw_path)
    cors_filt = parse_pos(cors_filt_path)
    print(f"  CORS raw points:      {len(cors_raw)}")
    print(f"  CORS filtered points: {len(cors_filt)}")

    # Use filtered GGA as bias reference (or raw if filtered is too small)
    bias_ref = traj_filt if len(traj_filt) >= 50 else traj_raw

    # --- CORS on raw ---
    if cors_raw:
        print("  Post-processing CORS-raw:")
        dlat_r, dlon_r = estimate_bias(cors_raw, bias_ref)
        cors_raw_bc = apply_bias(cors_raw, dlat_r, dlon_r)
        cors_raw_clean = remove_spikes(cors_raw_bc)
        cors_raw_smooth = smooth_trajectory(cors_raw_clean)
    else:
        cors_raw_smooth = []

    # --- CORS on filtered ---
    if cors_filt:
        print("  Post-processing CORS-filtered:")
        dlat_f, dlon_f = estimate_bias(cors_filt, bias_ref)
        cors_filt_bc = apply_bias(cors_filt, dlat_f, dlon_f)
        cors_filt_clean = remove_spikes(cors_filt_bc)
        cors_filt_smooth = smooth_trajectory(cors_filt_clean)
    else:
        cors_filt_smooth = []

    # ----------------------------------------------------------
    # 7. Build Leaflet map
    # ----------------------------------------------------------
    layers = [
        {
            "label": "1. Raw (NMEA GGA)",
            "rows": traj_raw,
            "color": "#888888",
            "weight": 2.0,
            "opacity": 0.65,
            "dash": "6,4",
        },
        {
            "label": "2. Filtered (NMEA quality gate)",
            "rows": traj_filt,
            "color": "#9467bd",
            "weight": 2.5,
            "opacity": 0.90,
            "dash": "",
        },
        {
            "label": "3. CORS on Raw + bias-corrected",
            "rows": cors_raw_smooth,
            "color": "#1f77b4",
            "weight": 2.8,
            "opacity": 0.95,
            "dash": "",
        },
        {
            "label": "4. CORS on Filtered + bias-corrected",
            "rows": cors_filt_smooth,
            "color": "#d62728",
            "weight": 3.0,
            "opacity": 0.98,
            "dash": "",
        },
    ]

    # Remove empty layers
    layers = [ly for ly in layers if ly["rows"]]

    out_html = os.path.join(WORKDIR, OUT_MAP_HTML)
    write_leaflet_html(out_html, layers)

    # ----------------------------------------------------------
    # Summary
    # ----------------------------------------------------------
    print("\n" + "=" * 60)
    print("DONE — Output:")
    print(f"  Interactive map: {out_html}")
    print(f"  CORS raw pos:    {cors_raw_path}")
    print(f"  CORS filt pos:   {cors_filt_path}")
    print("=" * 60)

    def step_report(name: str, rows: List[Dict]) -> None:
        if len(rows) < 2:
            return
        dists = [haversine_m(rows[i-1]["lat"], rows[i-1]["lon"],
                             rows[i]["lat"], rows[i]["lon"])
                 for i in range(1, len(rows))]
        arr = np.array(dists)
        print(f"  {name}: n={len(rows)}, "
              f"mean_step={arr.mean():.2f}m, "
              f"p95={np.percentile(arr,95):.2f}m, "
              f"max={arr.max():.2f}m")

    print("\nStep-distance statistics (lower = smoother trajectory):")
    step_report("Raw GGA", traj_raw)
    step_report("Filtered GGA", traj_filt)
    step_report("CORS-raw (corrected)", cors_raw_smooth)
    step_report("CORS-filt (corrected)", cors_filt_smooth)


if __name__ == "__main__":
    main()
