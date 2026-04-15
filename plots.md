# MAARGHA — All Plots Index

---

## Logger/3 × CORS Order4 (April 4, 2026)

### Interactive HTML Maps

| Label | File |
|---|---|
| **Set 1** — Raw + filter methods, then CORS correction | [set1_raw_methods_then_cors.html](file:///c:/Users/Guntesh/Desktop/foo/gsd/out/set1_raw_methods_then_cors.html) |
| **Set 2** — Raw + all filtering methods overlaid on CORS | [set2_raw_and_methods_on_cors.html](file:///c:/Users/Guntesh/Desktop/foo/gsd/out/set2_raw_and_methods_on_cors.html) |
| **Set 3** — Discard-outliers method vs CORS | [set3_discard_outliers_then_cors.html](file:///c:/Users/Guntesh/Desktop/foo/gsd/out/set3_discard_outliers_then_cors.html) |
| **4-trajectory combined** — Raw / NMEA-filtered / CORS-raw / CORS-NMEA | [logger3_order4_4traj.html](file:///c:/Users/Guntesh/Desktop/foo/gsd/out/logger3_order4_4traj.html) |

### Static PNG Exports

| Label | File |
|---|---|
| Set 1 PNG | [set1_raw_methods_then_cors.png](file:///c:/Users/Guntesh/Desktop/foo/gsd/out/set1_raw_methods_then_cors.png) |
| Set 2 PNG | [set2_raw_and_methods_on_cors.png](file:///c:/Users/Guntesh/Desktop/foo/gsd/out/set2_raw_and_methods_on_cors.png) |
| Set 3 PNG | [set3_discard_outliers_then_cors.png](file:///c:/Users/Guntesh/Desktop/foo/gsd/out/set3_discard_outliers_then_cors.png) |

---

## Logger/7 — Samsung A35 Carrier Phase Walk (April 7, 2026)

| Label | File |
|---|---|
| **Raw vs NMEA-filtered trajectory** (302 pts, 6-min walk, outdoor, carrier phase) | [logger7_trajectory.html](file:///c:/Users/Guntesh/Desktop/foo/gsd/out/logger7_trajectory.html) |

---

## Notes

- All HTML maps are interactive Leaflet maps — open in any browser
- Logger/3 data: OnePlus 11R, code-only RINEX, CORS = HYDE094M (DOY 094)
- Logger/7 data: Samsung A35, **carrier phase confirmed** (L1C present in RINEX header), CORS pending (DOY 096)
- Logger/8 data: simultaneous walk (DOY 101) – OnePlus 11R (code-only) + Samsung A35 (carrier phase) + Order 8 CORS

---

## Logger/8 — OnePlus vs Samsung Comparison Walk (April 11, 2026)

Simultaneous recording from both devices on the same walk, corrected against **HYDE101G00 (Order 8 CORS)**.

| Label | File |
|---|---|
| **6-Trajectory Comparison** — Raw / NMEA-filtered / CORS for both devices on one map | [logger8_comparison_6traj.html](file:///c:/Users/Guntesh/Desktop/foo/gsd/out/logger8_comparison_6traj.html) |
| **Vertical Split** — Synced two-panel view, OnePlus (top) vs Samsung (bottom) | [logger8_vertical_comparison.html](file:///c:/Users/Guntesh/Desktop/foo/gsd/out/logger8_vertical_comparison.html) |
| **Fwd/Bwd Kalman Combined** — NMEA filtered vs CORS RTS-smoothed, both devices on one map | [logger8_fwdbwd_combined.html](file:///c:/Users/Guntesh/Desktop/foo/gsd/out/logger8_fwdbwd_combined.html) |

**Trajectory point counts & lengths:**

| Trajectory | Points | Length |
|---|---|---|
| OnePlus — Raw GGA | 1241 | ~1572 m |
| OnePlus — NMEA Filtered (SNR≥25, HDOP≤2) | 1241 | ~1572 m |
| OnePlus — CORS Order 8 DGPS | 1246 | ~3326 m |
| Samsung — Raw GGA | 1244 | ~1601 m |
| Samsung — NMEA Filtered (SNR≥25, HDOP≤2) | 1244 | ~1601 m |
| Samsung — CORS Order 8 DGPS | 1250 | ~2044 m |

