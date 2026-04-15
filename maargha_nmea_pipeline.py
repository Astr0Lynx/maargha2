import os
import re
from collections import defaultdict
import csv
import json
from datetime import datetime

# ── Config ────────────────────────────────────────────────────────────────────
LAT_MIN, LAT_MAX = 17.0, 19.0
LON_MIN, LON_MAX = 77.0, 82.0

# Environmental Quality Gates (NMEA Filtering)
MIN_SNR_DB    = 25      # minimum Signal-to-Noise ratio for a satellite to count
MIN_GOOD_SATS = 4       # minimum number of good satellites required
MAX_HDOP      = 2.0     # maximum allowed Horizontal Dilution of Precision
MIN_FIX_QUAL  = 1       # 1=GPS Fix, 2=DGPS/Float, etc.

# ──────────────────────────────────────────────────────────────────────────────

def nmea_ll(lat_s, lat_h, lon_s, lon_h):
    """Convert NMEA ddmm.mmmm format to decimal degrees"""
    ld  = int(float(lat_s) / 100)
    lat = ld + (float(lat_s) - ld * 100) / 60.0
    if lat_h.upper() == 'S': lat = -lat
    lo  = int(float(lon_s) / 100)
    lon = lo + (float(lon_s) - lo * 100) / 60.0
    if lon_h.upper() == 'W': lon = -lon
    return lat, lon

def process_nmea_file(filepath, output_csv, output_json):
    print(f"Processing NMEA file: {filepath}")
    
    sec_snr = defaultdict(list)
    sec_gga = {}
    
    with open(filepath, 'r', encoding='ascii', errors='replace') as f:
        for line in f:
            line = line.strip()
            if not line.startswith('NMEA,'): continue
            
            parts = line.split(',')
            try:
                # GnssLogger format: NMEA,$GPGGA,...,*CS,TimestampMs
                ts = int(parts[-1])
                sec = ts // 1000
                nmea_str = ','.join(parts[1:-1]) # Exclude NMEA and Timestamp
            except: 
                continue

            # Parse GGA for Location and HDOP
            m = re.search(r'\$G.GGA,[\d.]+,([\d.]+),([NS]),([\d.]+),([EW]),(\d),\d+,([\d.]+)', nmea_str)
            if m:
                try:
                    lat, lon = nmea_ll(m.group(1), m.group(2), m.group(3), m.group(4))
                    q    = int(m.group(5))
                    hdop = float(m.group(6))
                    
                    if (LAT_MIN <= lat <= LAT_MAX and LON_MIN <= lon <= LON_MAX and q >= MIN_FIX_QUAL):
                        # Keep highest quality reading for this second
                        if sec not in sec_gga or q > sec_gga[sec]['q']:
                            sec_gga[sec] = {'lat': lat, 'lon': lon, 'hdop': hdop, 'q': q, 'ts': ts}
                except: 
                    pass
            
            # Parse GSV for Signal-to-Noise Ratio (SNR)
            elif 'GSV' in nmea_str:
                gm = re.search(r'\$G.GSV,\d+,\d+,\d+((?:,\d*,\d*,\d*,\d*)+)', nmea_str.split('*')[0])
                if gm:
                    sf = gm.group(1).strip(',').split(',')
                    for i in range(0, len(sf) - 3, 4):
                        s = sf[i + 3] if i + 3 < len(sf) else ''
                        if s.isdigit() and int(s) > 0:
                            sec_snr[sec].append(int(s))

    # Apply Quality Gating
    filtered_points = []
    filtered_json = []
    total_gga = len(sec_gga)
    
    for sec in sorted(sec_gga):
        data = sec_gga[sec]
        
        # Aggregate SNR data from surrounding seconds to be safe
        snrs = (sec_snr.get(sec, []) or sec_snr.get(sec - 1, []) or sec_snr.get(sec + 1, []))
        good_sats = sum(1 for s in snrs if s >= MIN_SNR_DB)
        
        if data['hdop'] <= MAX_HDOP and good_sats >= MIN_GOOD_SATS:
            # CSV Entry
            filtered_points.append({
                'lat': data['lat'],
                'lon': data['lon'],
                'timestamp': data['ts'],
                'hdop': data['hdop'],
                'sats': good_sats
            })
            
            # JSON Entry for MAARG React UI
            dt = datetime.fromtimestamp(data['ts'] / 1000.0)
            filtered_json.append({
                "x": 0.0, "y": 0.0, "z": 1.0, "v": 10.0, # IMU defaults if missing
                "lat": data['lat'],
                "lon": data['lon'],
                "time": dt.strftime("%H-%M-%S"),
                "milli": data['ts'],
                "file": "", 
                "Surface": "t",
                "Condition": "g"
            })

    print(f"Total RAW points: {total_gga}")
    print(f"Points passing strict quality gate: {len(filtered_points)}")
    
    # Export to MAARGHA standardized formats
    if filtered_points:
        os.makedirs(os.path.dirname(output_csv), exist_ok=True)
        with open(output_csv, 'w', newline='') as csvfile:
            fieldnames = ['lat', 'lon', 'timestamp', 'hdop', 'sats']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for pt in filtered_points:
                writer.writerow(pt)
        print(f"Cleaned trajectory saved to: {output_csv}")
        
        os.makedirs(os.path.dirname(output_json), exist_ok=True)
        with open(output_json, 'w') as jsonfile:
            json.dump(filtered_json, jsonfile, indent=2)
        print(f"React UI Data saved to: {output_json}")
    else:
        print("Warning: No points passed the quality gate!")

if __name__ == '__main__':
    # Example Usage: run on the optimal carrier-phase dataset
    input_file = r'logger\8_Samsung\gnss_log_2026_04_11_11_40_39.nmea'
    output_csv = r'Data\trajectory_cleaned.csv'
    output_json = r'maarg-web-ui\src\Data\latest.json'
    
    if os.path.exists(input_file):
        process_nmea_file(input_file, output_csv, output_json)
    else:
        print(f"File not found: {input_file}")
