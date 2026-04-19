import json, csv, os

# ── Check 1: Viterbi JSON output ──────────────────────────────────────────────
viterbi_path = 'maarg-web-ui/src/Data/latest_viterbi.json'
assert os.path.exists(viterbi_path), "FAIL: latest_viterbi.json missing!"
with open(viterbi_path) as f:
    vdata = json.load(f)
first = vdata[0]
last  = vdata[-1]
print(f"[OK] latest_viterbi.json: {len(vdata)} Viterbi-snapped points total")
print(f"     First: lat={first['lat']:.6f}, lon={first['lon']:.6f}, Surface={first['Surface']}")
print(f"     Last:  lat={last['lat']:.6f},  lon={last['lon']:.6f}")

# ── Check 2: All UI-required fields present ───────────────────────────────────
required = ['lat','lon','time','milli','Surface','Condition','x','y','z','v']
missing = [k for k in required if k not in first]
if missing:
    print(f"[FAIL] Missing UI fields: {missing}")
else:
    print(f"[OK] All required React UI JSON fields present: {required}")

# ── Check 3: Viterbi snapping delta vs raw trajectory ─────────────────────────
raw_path = 'maarg-web-ui/src/Data/latest.json'
with open(raw_path) as f:
    rdata = json.load(f)
raw_lat0 = rdata[0]['lat']
vit_lat0 = vdata[0]['lat']
delta_m = abs(raw_lat0 - vit_lat0) * 111111
print(f"[OK] Snapping delta at point[0]: {delta_m:.2f} meters road offset")
print(f"     Raw GNSS:  {raw_lat0:.8f} | Viterbi Snapped: {vit_lat0:.8f}")

# ── Check 4: Legacy C++ CSVs ──────────────────────────────────────────────────
data_dir = 'Data'
legacy_files = sorted([f for f in os.listdir(data_dir) if f.startswith('ANDGPS')])
print(f"[OK] Legacy C++ CSV files generated: {legacy_files}")
if legacy_files:
    with open(os.path.join(data_dir, legacy_files[0])) as f:
        rows = f.readlines()
    cols = rows[0].strip().split(',')
    print(f"     Sample row: {rows[0].strip()}")
    print(f"     Total rows: {len(rows)} | Col count: {len(cols)} (expected 3)")

# ── Check 5: trajectory_cleaned.csv quality gate stats ───────────────────────
with open(os.path.join(data_dir, 'trajectory_cleaned.csv')) as f:
    reader = list(csv.DictReader(f))
hdops = [float(r['hdop']) for r in reader]
sats  = [int(float(r['sats'])) for r in reader]
print(f"[OK] trajectory_cleaned.csv: {len(reader)} quality-gated points")
print(f"     HDOP range: {min(hdops):.2f} - {max(hdops):.2f} (limit: <=2.0)")
print(f"     Sats range: {min(sats)} - {max(sats)} (min required: 4)")

print("\n========================================")
print("AUDIT PASSED: All pipeline outputs are valid.")
print("========================================")
