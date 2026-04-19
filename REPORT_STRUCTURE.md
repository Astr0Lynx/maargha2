# MAARGHA 2.0 — Progress & Scope Redefinition Report

## 1. Executive Summary & Deliverables
*Clearly state what you have functionally delivered so the advisor knows work was completed.*
* **Delivered 1:** Rebuilt the Android App to natively capture raw hardware NMEA baseband strings and IMU telemetry asynchronously, removing the need for external logging apps.
* **Delivered 2:** Python Integration Pipeline that dynamically cleans GNSS drift (via HDOP/SNR gating) and ports it perfectly backwards to the ancient 2014 C++ engine format (`ANDGPSLA.csv`).
* **Delivered 3:** A functional **Viterbi Hidden Markov Model (HMM)** engine that mathematically snaps noisy GNSS clouds onto topological OpenStreetMap lane vectors.

## 2. Redefining the Scope (The Narrative Pivot)
*This is where you guide the listener from what we planned, to what we discovered, to how we solved it.*

### A. The Original Plan: Pure Hardware Correction (CORS)
We originally hypothesized that post-processing smartphone GNSS data against the HYDE CORS Base Station using RTKLIB would yield lane-level accuracy.

### B. The Discovery: Smartphone Hardware Bottlenecks
* **Carrier vs Non-Carrier:** We tested both the OnePlus 11R (Code-phase only) and Samsung A35 (Carrier-phase).
* **The Multipath Explosion:** When we applied CORS correction to the OnePlus, the trajectory length doubled (from 1500m to 3300m) with massive zig-zag spikes. 
* **Conclusion:** The issue isn't our methodology, nor is it the distance to the HYDE station (~22km baseline is negligible). The issue is **urban multipath**. Smartphone antennas capture highly reflected, noisy signals. When RTKLIB attempts precise differential math on distorted signals, the equations fracture. Excluding single "bad" satellites doesn't fix it, because the noise is systemic to the environment.

### C. The Solution: Algorithmic Map Matching (HMM)
Since we cannot rely on raw hardware accuracy from cheap antennas, we pivoted the scope to **Software-Level Geometry**. We built the Viterbi HMM map matcher. By trading hardware dependency for topological logic, we successfully forced the trajectory to snap strictly to physical road bounds regardless of GNSS spikes.

## 3. Sub-Objectives Discussed
* **CORS Post-Processing:** Viable *only* if the device supports high-quality Carrier-Phase tracking (like the Samsung A35). For legacy/cheap devices, it damages the data.
* **NMEA Direct Access:** We bypassed Android's heavy internal smoothing (LocationManager) to feed our HMM pure, untouched hardware tuples.
* **Legacy Compatibility:** We successfully updated the data pipeline without needing to rewrite thousands of lines of old 2014 C++ code.

## 4. Future Feature: Sensor Fusion (IMU + Viterbi)
*How to hit sub-lane accuracy?*
GNSS is too blunt to confirm if a car switched from the left lane to the right lane. We will inject the **IMU Accelerometer (Y-Axis Lateral forces)** into the Viterbi Transition Matrix. 
* **Normal Driving:** HMM strictly rewards staying perfectly straight on current lane vector.
* **Lane Switch:** A sudden spike in lateral IMU G-force acts as a trigger, instantly commanding the HMM to boost the probability of transitioning to adjusting parallel sub-lanes.

## 5. Conclusion
**Where we planned to go:** Perfecting GNSS via CORS.
**What we delivered:** A robust, hybrid system that accepts noisy hardware data and fixes it algorithmically using topological Map Matching and NMEA Native Capture.
