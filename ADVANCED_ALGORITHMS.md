# Advanced Lane-Level Trajectory Correction Algorithms

## Problem Assessment

**Current limitation:** 1.56m mean step with Robust Kalman is still too coarse for lane-level matching
- Typical Indian lane width: 2.5-3.5m
- Need: ~0.5-1.0m RMS accuracy for reliable lane assignment
- Have: Code-only GNSS from phone (fundamentally limited to ~1-2m without carrier phase)

**Root cause:** Phone GNSS code observables suffer from:
1. Multipath in urban/campus environment
2. Limited constellation geometry (not true RTK baseline geometry)
3. No carrier-phase observations for cm-level refinement
4. Code bias from receiver hardware (~0.5-1m systematic)

---

## Algorithm Options (Ranked by Feasibility & Impact)

### ⭐ **TIER 1: Most Practical (Can implement immediately)**

#### 1. **Pedestrian Dead Reckoning (PDR) + GNSS Fusion** 🚶‍♂️
**What it does:** Use phone accelerometer/gyro to detect steps and walking direction between GNSS fixes

**How it works:**
```
For each epoch:
1. Detect step from accelerometer spike pattern
2. Estimate step length from motion signature
3. Estimate heading from gyroscope integration
4. Dead reckon from last GNSS fix
5. GNSS provides periodic corrections (prevents drift)
6. Fuse via extended Kalman filter (EKF) or particle filter
```

**Why it helps:**
- ✅ Phone accelerometer/gyro have ~0.1-0.5m step-level accuracy
- ✅ Between GNSS fixes, PDR fills gaps with high accuracy
- ✅ Can detect when GNSS is unreliable (sudden acceleration spikes)
- ✅ Can improve from 1.5m → 0.5-0.8m RMS

**Data needed:** Check your Android GnssLogger log for:
```
GnssNavigationMessage (contains accelerometer?)
SensorEvent (if available)
```

**Complexity:** Medium - Need to detect step patterns from raw IMU

---

#### 2. **Map-Constrained Particle Filter** 🗺️
**What it does:** Enforce trajectory to snap to valid road graph, using GNSS as measurement constraint

**How it works:**
```
For each GNSS epoch:
1. Sample N particles along road network near GNSS measurement
2. Weight each particle by:
   - Likelihood of GNSS measurement at that location
   - Plausibility of movement from previous position
   - Walking speed constraint (0.5-1.5 m/s)
3. Resample high-weight particles (keep good hypotheses)
4. Continue to next epoch, constrained to road graph
5. Output: Most likely path through road network
```

**Why it helps:**
- ✅ Directly projects trajectory onto road geometry
- ✅ Road constraints absorb GNSS noise
- ✅ Can recover from large spikes (will snap back to road)
- ✅ Can improve from 1.5m → 0.3-0.5m RMS (within lane)

**Data needed:** 
- OpenStreetMap road network (freely available)
- GNSS uncertainty at each epoch (you have this from RTK solution std-dev)

**Complexity:** Medium - Particle filter implementation relatively straightforward

---

#### 3. **Viterbi Path Fitting with B-Spline Smoothing** 📊
**What it does:** Find optimal path through road graph maximizing smoothness + GNSS fit

**How it works:**
```
1. Discretize road network into candidate nodes
2. Build trellis: (epoch t) → (road node k)
3. Compute edge weights:
   - Distance from GNSS to node k at epoch t
   - Distance constraint (max step speed 1.4 m/s)
   - Heading change penalty (penalize sharp turns)
4. Run Viterbi algorithm (dynamic programming)
5. Extract path with maximum weight
6. Fit B-spline through selected nodes (smooth)
```

**Why it helps:**
- ✅ Global optimization (Viterbi finds optimal path jointly)
- ✅ Smoother than greedy nearest-point matching
- ✅ Can handle large spikes without breaking
- ✅ Deterministic (no sampling like particle filter)
- ✅ Can improve from 1.5m → 0.3-0.5m RMS

**Data needed:** Same as particle filter (road network + GNSS positions)

**Complexity:** Medium-High - Requires road network pre-processing

---

### ⭐⭐ **TIER 2: High-Impact (Requires additional data)**

#### 4. **Tightly-Coupled GNSS/INS (Inertial Measurement Unit) Fusion** 🔄
**What it does:** Combine GNSS with phone's accelerometer+gyroscope for trajectory refinement

**Technique:** Extended Kalman Filter (EKF) with:
- **State:** [lat, lon, height, v_north, v_east, v_down, bias_accel, bias_gyro]
- **Measurements:** GNSS position + IMU accelerations
- **Process model:** Kinematic equations (velocity → position, acceleration → velocity)

**Why it helps:**
- ✅ IMU provides high-rate (100Hz) constraint on smooth motion
- ✅ Can detect and suppress GNSS spikes in real-time
- ✅ Fills gaps between GNSS fixes
- ✅ Can improve from 1.5m → 0.5-1.0m RMS

**Data needed:**
```
SensorEvent or SENSOR_ACCELEROMETER data from GnssLogger
SENSOR_GYROSCOPE data
```
**Check:** Look in your log for `Sensor,` lines

**Complexity:** High - Requires IMU calibration (biases, scale factors)

---

#### 5. **Carrier-Phase Integer Ambiguity Resolution (RTK-Integer)** 🎯
**What it does:** Resolve L1/L2 carrier phase ambiguities for cm-level accuracy

**Why it could work:**
- ✅ RTK with integer ambiguities = 2-5 cm accuracy (vs 75cm for float)
- ✅ Would transform your problem entirely

**Reality check:**
```
❌ Your phone GNSS logs: Code only (C1C, C2I, C5Q)
❌ Missing: Carrier phase (L1, L2, L5)
❌ Solution: Cannot recover what wasn't logged
```
**Unless:** You have multi-frequency phase data stored elsewhere? Check your logger output format.

**If phase exists:** Use RTKLIB integer mode:
```bash
rnx2rtkp -m 0 -r ... -b ...  # -m 0 = DGPS, -m 1 = Static, -m 2 = Kinematic+integer
```

---

### ⭐⭐⭐ **TIER 3: Research-Grade (Most powerful)**

#### 6. **Factor Graph Optimization with Map Constraints** 🧮
**What it does:** Joint optimization of entire trajectory with GNSS measurements + road constraints

**Framework:** GTSAM (Georgia Tech Smoothing and Mapping) or Ceres Solver

```python
# Pseudocode
graph = FactorGraph()

for t in range(n_epochs):
    # Add pose node
    pose_t = Pose2(x[t], y[t], heading[t])
    graph.add(pose_t)
    
    # GNSS measurement factor
    graph.add(GaussianFactor(
        keys=[pose_t],
        measurement=gnss[t],
        covariance=sigma_gnss[t]**2
    ))
    
    # Road constraint factor (enforce pose near road)
    nearest_road = get_nearest_road(pose_t)
    graph.add(PriorFactor(
        keys=[pose_t],
        prior=nearest_road,
        covariance=0.1  # tight constraint
    ))
    
    # Motion constraint (smooth trajectory)
    graph.add(BetweenFactor(
        keys=[pose_t, pose_t+1],
        relative_pose=motion_model[t],
        covariance=Q  # process noise
    ))

result = graph.optimize()  # Joint optimization
```

**Why it helps:**
- ✅ Global optimization of entire trajectory
- ✅ Naturally handles map constraints
- ✅ Propagates information across entire trajectory
- ✅ Can improve from 1.5m → 0.2-0.5m RMS

**Complexity:** Very High - Requires factor graph optimization knowledge

---

## Recommended Implementation Path

### **Quick Win (1-2 hours):** Map-Constrained Particle Filter
```python
# Pseudocode for simplest approach
import osmium  # read OpenStreetMap data
from filterpy.monte_carlo import ParticleFilter

# 1. Load road network
roads = load_osm_roads(bbox)  # Get from OpenStreetMap
road_nodes = discretize_roads(roads, step=5)  # Every 5m node

# 2. For each GNSS epoch
for t in range(len(gnss_trajectory)):
    gnss_pos = gnss_trajectory[t]
    gnss_std = solution_std[t]  # Your RTK solution std-dev
    
    # 3. Sample particles near GNSS position
    particles = sample_near_roads(gnss_pos, gnss_std, road_nodes)
    weights = []
    for particle in particles:
        dist = haversine(gnss_pos, particle)
        likelihood = exp(-dist**2 / (2 * gnss_std**2))
        
        # Penalize if far from road or unrealistic speed
        speed = distance(particles_t_minus_1, particle) / dt
        if speed > 1.5:  # > 1.5 m/s = unrealistic walking
            likelihood *= 0.5
            
        weights.append(likelihood)
    
    # 4. Resample and continue
    particles = resample(particles, weights)

# Output: cleaned_trajectory = [particle.mean() for t in range(n)]
```

**Expected improvement:** 1.5m → 0.5-0.7m RMS

---

### **Better (4-6 hours):** Viterbi Matching  
Similar to above but uses dynamic programming instead of particle filter
- Deterministic (no randomness)
- Slightly faster
- More predictable results

---

### **Best (8+ hours):** PDR + GNSS Fusion
If your GnssLogger has accelerometer data:
```python
# Step 1: Detect steps from accelerometer
steps = detect_steps_from_accel(accel_data)  # ML/signal processing

# Step 2: Estimate heading from gyroscope
heading = integrate_gyro(gyro_data)

# Step 3: Fuse PDR with GNSS via EKF
ekf = ExtendedKalmanFilter(
    motion_model=pdr_motion,
    measurement_model=gnss_measurement,
    process_noise=Q_pdr,
    measurement_noise=R_gnss
)

# Output: fused_trajectory
```

**Expected improvement:** 1.5m → 0.4-0.6m RMS (best possibility with code-only data)

---

## Quick Check: Do You Have Additional Data?

Check your `gnss_log_2026_03_15_11_10_23.txt` file for:

```bash
# Look for these lines:
grep "^Sensor," gnss_log_2026_03_15_11_10_23.txt | wc -l
# If > 0: You have accelerometer/gyro data! → Use PDR fusion

grep "^UltraWideband" gnss_log_2026_03_15_11_10_23.txt | wc -l  
# If > 0: You have UWB ranging! → Could improve significantly

grep "L1\|L2\|L5" gnss_log_2026_03_15_11_10_23.26o
# If present: You have carrier phase! → Could do RTK-integer
```

---

## Summary: What to Try First

| Your Constraint | Best Algorithm | Expected Result |
|---|---|---|
| **Code-only GNSS, no motion data** | **Map-Constrained Particle Filter** | 1.5m → 0.5-0.7m RMS |
| **Code-only + Accel/Gyro available** | **PDR + GNSS Fusion (EKF)** | 1.5m → 0.4-0.6m RMS ⭐ **BEST** |
| **Code-only + Complex codebase OK** | **Viterbi/HMM Matching** | 1.5m → 0.4-0.6m RMS |
| **Time-unlimited, high accuracy needed** | **Factor Graph (GTSAM)** | 1.5m → 0.2-0.4m RMS |

---

## Reality Check for Your MAARGHA System

**Lane-level matching requires ~0.5m accuracy:**
```
Current (Robust Kalman): 1.56m mean → Can assign to road, but not reliable lane
With Map Particle Filter: 0.5-0.7m mean → Marginal lane assignment  
With PDR Fusion: 0.4-0.6m mean → Good lane reliance (if IMU available)
With RTK-Integer: 0.05-0.10m mean → Would be perfect (if phase logged)
```

**For MAARGHA 2.0 production:** I'd recommend:
1. Modify **GnssLogger to save carrier phase** (if device supports)
2. Collect **IMU data alongside GNSS** (accelerometer/gyroscope always available)
3. Implement **PDR detector + EKF fusion** (most practical hardware-agnostic approach)
4. Fall back to **map-constrained particle filter** if IMU unreliable

Would you like me to implement any of these?
