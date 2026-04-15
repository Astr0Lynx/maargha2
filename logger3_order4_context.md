# Logger3 + Order4 CORS Execution Context

## Objective
Run a full NMEA-informed filtering workflow for logger/3 and compare four trajectories on one map:
1. Raw
2. Filtered using NMEA data
3. Correction with CORS on RAW
4. CORS correction on NMEA Filtered

## Input Data
- Rover RINEX: logger/3/gnss_log_2026_04_04_17_53_31.26o
- GnssLogger text: logger/3/gnss_log_2026_04_04_17_53_31.txt
- NMEA: logger/3/gnss_log_2026_04_04_17_53_31.nmea
- CORS base files (Order4):
  - cors/Order4/HYDE094M.26o
  - cors/Order4/HYDE094M.26n
  - cors/Order4/HYDE094M.26g
  - cors/Order4/HYDE094M.26l
  - cors/Order4/HYDE094M.26c
  - cors/Order4/HYDE094M.26j

## Time Window (UTC)
- Rover RINEX epochs: 2026-04-04 12:23:49.424912 to 2026-04-04 12:37:37.424912
- Duration: 13m48s

## Thresholds (Initial)
- CN0 >= 28 dB-Hz
- Elevation >= 10 deg
- HDOP <= 5.0
- PDOP <= 10.0
- Minimum satellites passing quality checks >= 6
- UsedInFix preferred (from Status records)

## Execution Plan (What I am doing now)
1. Rewrite outlier_methods_cors_pipeline.py into a clean logger/3 + Order4 pipeline.
2. Parse quality from GnssLogger Status + NMEA (GSV/GSA/GGA) and build per-second quality table.
3. Filter rover epochs by thresholds and write filtered rover RINEX.
4. Run RTKLIB CORS twice:
   - Raw rover RINEX
   - NMEA-filtered rover RINEX
5. Parse outputs, compute quality metrics, and generate one combined map with all 4 requested trajectories.

## Expected Outputs
- out/rover_nmea_filtered_order4.26o
- out/solution_cors_raw_order4.pos
- out/solution_cors_nmea_filtered_order4.pos
- out/logger3_order4_4traj.png
- out/logger3_order4_4traj.html
- out/logger3_order4_metrics.txt

## Execution Status (Completed)
- Rewrote `outlier_methods_cors_pipeline.py` into a clean logger/3 + Order4 pipeline.
- Parsed NMEA + Status quality sources, applied configured thresholds, and built filtered rover epochs.
- Ran dual CORS processing successfully on RAW and NMEA-filtered rover observations.
- Generated required combined map with exactly these layers:
  1. Raw
  2. Filtered using NMEA data
  3. Correction with CORS on RAW
  4. CORS correction on NMEA Filtered

## Actual Output Summary
- Raw phone fixes: 1737
- NMEA-filtered raw fixes: 1737
- Rover RINEX epochs kept after filtering: 829/829
- CORS RAW points: 827
- CORS NMEA-filtered points: 827

## Important Observation
- With current thresholds and this session's logger/3 quality data, no epochs were rejected.
- Therefore, trajectories (2) and (1) are identical, and trajectories (4) and (3) are identical for this run.
- If stronger differentiation is needed, tighten thresholds (e.g., CN0>=30, Elev>=15, HDOP<=3.5).

## Notes for Fresh AI Instance
- Use RTKLIB executable: C:/tools/RTKLIB_EX_2.5.0/rnx2rtkp.exe
- Keep map labels exactly as user requested.
- Preserve UTC alignment by nearest-second matching between quality metrics and rover epochs.
