# CORS Correction Progress Report

## Completed So Far
- Set up CORS-based post-processing pipeline using RTKLIB with rover and HYDE074 base station RINEX files.
- Generated corrected trajectory outputs and interactive maps for visual inspection.
- Built raw vs corrected vs smoothed trajectory comparisons and exported CSV outputs.
- Quantified trajectory quality with step-distance metrics (mean, P95, max, counts above 3m/5m).
- Ran single-satellite exclusion sweep across multiple PRNs; confirmed spikes were not caused by one bad satellite.
- Implemented and compared multiple cleaning methods:
  - Kinematic constraints
  - Adaptive median filtering
  - RAIM-style gating
  - Robust Kalman filtering
- Added map-constrained particle filtering to further reduce jump spikes and improve lane-level readiness.

## Methodology (Approaches Used So Far)
1. **CORS/RTK post-processing (baseline):** Raw rover GNSS data was converted to RINEX and processed in RTKLIB against HYDE074 base station files. We used multi-constellation navigation inputs to improve geometry and solution continuity. The resulting baseline CORS trajectory (`solution_first.pos`) is the reference for all later comparisons.

2. **Kinematic constraints:** We detected physically unrealistic jumps using step-distance and implied-speed checks between consecutive epochs. Points violating motion plausibility were clipped or corrected toward local motion-consistent values. This reduced abrupt spikes while preserving trajectory direction.

3. **Adaptive median filtering:** A sliding local window was applied to latitude/longitude sequences to suppress impulse-like outliers. The filter adapted to local variability so straight and curving segments were both retained reasonably well. This gave a robust denoised trajectory without heavy global smoothing.

4. **RAIM-style gating:** Residual-like consistency checks were used to reject measurements that deviated strongly from neighborhood expectations. Epochs failing the gate were either down-weighted or replaced using nearby valid trend information. The method targeted integrity by isolating suspect fixes instead of smoothing everything.

5. **Robust Kalman filtering:** A motion-model Kalman filter was used with outlier-robust update behavior to limit the influence of large innovations. Prediction and correction were balanced to retain temporal continuity and reduce noise. This became one of the strongest practical smoothers before map matching.

6. **Map-constrained particle filtering:** Multiple state hypotheses (particles) were propagated and reweighted using GNSS likelihood and motion constraints. Particles inconsistent with likely road motion were naturally down-weighted during resampling. The posterior mean trajectory (`trajectory_particle_filter.csv`) produced the best lane-readiness in our comparisons.

7. **Innovation Filtering (outlier-only):** For each epoch, we predicted position from recent motion and computed innovation magnitude. A robust threshold (median + k*scale via MAD) flagged spikes, then those epochs were excluded before rerunning CORS. This method targets outlier removal rather than full smoothing.

8. **Adaptive Weighting (outlier-only):** Residual magnitudes were converted into adaptive weights so high-residual epochs contributed less. In pre-CORS mode, strongly down-weighted/flagged epochs were removed from rover epochs and CORS was recomputed. This preserves most data while reducing the influence of anomalous fixes.

9. **Mahalanobis Distance (outlier-only):** Local covariance of trajectory deltas was estimated and each epoch's deviation was scored in a multivariate sense. Epochs with high Mahalanobis distance were treated as outliers and excluded for a CORS rerun. This captures direction-aware anomalies better than scalar thresholds.

10. **Discard-spike-then-CORS (Set 3):** Spike epochs were detected on aligned raw data using robust innovation thresholding only, then removed directly. CORS was rerun on the reduced rover epoch set to produce `solution_discard_outliers.pos`. We also visualize the pre-CORS spike-removed trajectory separately to show what was discarded.

## Currently Doing
- Consolidating the CORS-corrected processing path for stable use in MAARGHA map matching.
- Reviewing which cleaned output should be the default production input (currently `trajectory_particle_filter.csv`, with `trajectory_app4_kalman.csv` as fallback).
- Validating remaining edge cases where residual deviation can still affect strict lane assignment.

## Near-Term Plan
- Integrate cleaned trajectory output into lane-level HMM/Viterbi map-matching workflow.
- Add confidence scoring and epoch-level anomaly flags for safer downstream matching.
- Compare matched path against known road/lane geometry and tune thresholds.

## Future Plan
- Improve data collection settings to log higher-quality observables (carrier phase if device supports it, plus IMU streams).
- Add tightly-coupled GNSS+IMU fusion (PDR/EKF) for better short-term stability in noisy segments.
- Move toward a robust production pipeline with automatic quality checks, fallback strategies, and reproducible reports.

## Limitations and Feasibility
- Current rover data is mostly code-based GNSS quality, which is fundamentally sensitive to multipath and urban reflection noise.
- Single-satellite exclusion did not materially improve spikes, indicating errors are systemic (environment + receiver constraints), not one bad PRN.
- Post-processing filters (Kalman/RAIM/particle constraints) reduce spikes significantly but cannot create true centimeter-grade accuracy from noisy code-only observations.
- Lane-level matching is partly achievable with current pipeline when combined with map constraints, but not guaranteed at every epoch in difficult segments.

### Is Target Accuracy Fully Possible Right Now?
- For reliable lane-level assignment at all times: Not fully guaranteed with current data quality.
- For strong road-level and near-lane-level behavior most of the time: Yes, current cleaned outputs are usable.
- For consistent, production-grade lane-level certainty: Likely requires better observables (carrier phase if supported) and/or GNSS+IMU fusion.
