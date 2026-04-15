#!/usr/bin/env python3
"""
Create comparison visualizations of all 4 approaches.
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from math import radians, cos, sin, asin, sqrt

def haversine(lat1, lon1, lat2, lon2):
    R = 6371000
    dLat = radians(lat2 - lat1)
    dLon = radians(lon2 - lon1)
    a = sin(dLat/2) * sin(dLat/2) + cos(radians(lat1)) * cos(radians(lat2)) * sin(dLon/2) * sin(dLon/2)
    c = 2 * asin(sqrt(a))
    return R * c

def read_pos_for_plot(path):
    """Read POS file and compute metrics."""
    rows = []
    with open(path) as f:
        for line in f:
            if line.startswith('%') or line.startswith('#'):
                continue
            parts = line.split()
            if len(parts) < 8:
                continue
            try:
                date_parts = parts[0].split('/')
                time_parts = parts[1].split(':')
                lat, lon, height = float(parts[2]), float(parts[3]), float(parts[4])
                rows.append({'lat': lat, 'lon': lon, 'height': height})
            except:
                continue
    
    # Compute step distances
    steps = []
    for i in range(1, len(rows)):
        dist = haversine(rows[i-1]['lat'], rows[i-1]['lon'], rows[i]['lat'], rows[i]['lon'])
        steps.append(dist)
    
    return rows, steps

def read_csv_trajectory(path):
    """Read our generated CSV files."""
    df = pd.read_csv(path)
    rows = [{'lat': lat, 'lon': lon} for lat, lon in zip(df['lat'], df['lon'])]
    steps = []
    for i in range(1, len(rows)):
        dist = haversine(rows[i-1]['lat'], rows[i-1]['lon'], rows[i]['lat'], rows[i]['lon'])
        steps.append(dist)
    return rows, steps

# Read all datasets
print("Loading trajectories...")
baseline_rows, baseline_steps = read_pos_for_plot('out/solution_first.pos')
app1_rows, app1_steps = read_csv_trajectory('trajectory_app1_kinematic.csv')
app2_rows, app2_steps = read_csv_trajectory('trajectory_app2_median.csv')
app3_rows, app3_steps = read_csv_trajectory('trajectory_app3_raim.csv')
app4_rows, app4_steps = read_csv_trajectory('trajectory_app4_kalman.csv')

# Create comprehensive comparison figure
fig = plt.figure(figsize=(18, 12))

# 1. Maps overlay (all trajectories on one map)
ax1 = plt.subplot(2, 3, 1)
baseline_lons = [r['lon'] for r in baseline_rows]
baseline_lats = [r['lat'] for r in baseline_rows]
app1_lons = [r['lon'] for r in app1_rows]
app1_lats = [r['lat'] for r in app1_rows]
app2_lons = [r['lon'] for r in app2_rows]
app2_lats = [r['lat'] for r in app2_rows]
app3_lons = [r['lon'] for r in app3_rows]
app3_lats = [r['lat'] for r in app3_rows]
app4_lons = [r['lon'] for r in app4_rows]
app4_lats = [r['lat'] for r in app4_rows]

ax1.plot(baseline_lons, baseline_lats, 'o-', linewidth=2, markersize=3, label='Baseline', alpha=0.7)
ax1.plot(app4_lons, app4_lats, 'x-', linewidth=2.5, markersize=4, label='Robust Kalman (BEST)', alpha=0.9, color='GREEN')
ax1.plot(app3_lons, app3_lats, 's--', linewidth=1.5, markersize=3, label='RAIM Gate', alpha=0.6, color='ORANGE')
ax1.set_xlabel('Longitude')
ax1.set_ylabel('Latitude')
ax1.set_title('Trajectory Comparison (All Methods)')
ax1.legend(fontsize=8)
ax1.grid(True, alpha=0.3)

# 2. Step distance histogram
ax2 = plt.subplot(2, 3, 2)
bins = np.arange(0, 15, 0.5)
ax2.hist([s for s in baseline_steps if s <= 12], bins=bins, alpha=0.5, label='Baseline', edgecolor='black')
ax2.hist([s for s in app4_steps if s <= 12], bins=bins, alpha=0.6, label='Robust Kalman', color='GREEN', edgecolor='black')
ax2.set_xlabel('Step Distance (m)')
ax2.set_ylabel('Frequency')
ax2.set_title('Step Distance Distribution')
ax2.legend()
ax2.grid(True, alpha=0.3, axis='y')

# 3. Step distance over time (epoch)
ax3 = plt.subplot(2, 3, 3)
ax3.plot(baseline_steps, 'o-', linewidth=1, markersize=2, label='Baseline', alpha=0.7)
ax3.plot(app4_steps, 's-', linewidth=1.5, markersize=2.5, label='Robust Kalman', color='GREEN', alpha=0.8)
ax3.axhline(y=3, color='red', linestyle='--', linewidth=1, alpha=0.5, label='3m threshold')
ax3.axhline(y=5, color='darkred', linestyle='--', linewidth=1, alpha=0.5, label='5m threshold')
ax3.set_xlabel('Epoch')
ax3.set_ylabel('Step Distance (m)')
ax3.set_title('Spikes Over Time')
ax3.legend(fontsize=8)
ax3.grid(True, alpha=0.3)
ax3.set_ylim([0, 14])

# 4. Box plot comparison
ax4 = plt.subplot(2, 3, 4)
data_to_plot = [
    [s for s in baseline_steps if s <= 12],
    [s for s in app3_steps if s <= 12],
    [s for s in app4_steps if s <= 12]
]
bp = ax4.boxplot(data_to_plot, labels=['Baseline', 'RAIM Gate', 'Robust Kalman'], patch_artist=True)
colors = ['lightblue', 'orange', 'lightgreen']
for patch, color in zip(bp['boxes'], colors):
    patch.set_facecolor(color)
ax4.set_ylabel('Step Distance (m)')
ax4.set_title('Step Distance Comparison (Box Plot)')
ax4.grid(True, alpha=0.3, axis='y')

# 5. Cumulative distribution
ax5 = plt.subplot(2, 3, 5)
baseline_sorted = np.sort(baseline_steps)
app4_sorted = np.sort(app4_steps)
ax5.plot(np.arange(len(baseline_sorted))/len(baseline_sorted)*100, baseline_sorted, 'o-', linewidth=2, markersize=3, label='Baseline', alpha=0.7)
ax5.plot(np.arange(len(app4_sorted))/len(app4_sorted)*100, app4_sorted, 's-', linewidth=2.5, markersize=3, label='Robust Kalman', color='GREEN', alpha=0.8)
ax5.axhline(y=3, color='red', linestyle='--', alpha=0.5)
ax5.axhline(y=5, color='darkred', linestyle='--', alpha=0.5)
ax5.set_xlabel('Percentile')
ax5.set_ylabel('Step Distance (m)')
ax5.set_title('Cumulative Distribution Function')
ax5.legend()
ax5.grid(True, alpha=0.3)
ax5.set_ylim([0, 14])

# 6. Metrics table
ax6 = plt.subplot(2, 3, 6)
ax6.axis('off')

metrics_data = [
    ['Metric', 'Baseline', 'RAIM Gate', 'Robust Kalman'],
    ['Epochs', f'{len(baseline_steps)}', f'{len(app3_steps)}', f'{len(app4_steps)}'],
    ['Mean (m)', f'{np.mean(baseline_steps):.2f}', f'{np.mean(app3_steps):.2f}', f'{np.mean(app4_steps):.2f}'],
    ['Median (m)', f'{np.median(baseline_steps):.2f}', f'{np.median(app3_steps):.2f}', f'{np.median(app4_steps):.2f}'],
    ['P95 (m)', f'{np.percentile(baseline_steps, 95):.2f}', f'{np.percentile(app3_steps, 95):.2f}', f'{np.percentile(app4_steps, 95):.2f}'],
    ['Max (m)', f'{np.max(baseline_steps):.2f}', f'{np.max(app3_steps):.2f}', f'{np.max(app4_steps):.2f}'],
    ['Steps >3m', f'{sum(1 for s in baseline_steps if s > 3)}', f'{sum(1 for s in app3_steps if s > 3)}', f'{sum(1 for s in app4_steps if s > 3)}'],
    ['Steps >5m', f'{sum(1 for s in baseline_steps if s > 5)}', f'{sum(1 for s in app3_steps if s > 5)}', f'{sum(1 for s in app4_steps if s > 5)}'],
]

table = ax6.table(cellText=metrics_data, cellLoc='center', loc='center', 
                  colWidths=[0.25, 0.25, 0.25, 0.25])
table.auto_set_font_size(False)
table.set_fontsize(9)
table.scale(1, 2)

# Style header row
for i in range(4):
    table[(0, i)].set_facecolor('#4CAF50')
    table[(0, i)].set_text_props(weight='bold', color='white')

# Style best result column
for i in range(1, len(metrics_data)):
    table[(i, 3)].set_facecolor('#C8E6C9')

ax6.set_title('Metrics Comparison', fontsize=11, weight='bold', pad=20)

plt.tight_layout()
plt.savefig('trajectory_comparison_all_methods.png', dpi=150, bbox_inches='tight')
print("Saved: trajectory_comparison_all_methods.png")

# Also create a zoomed-in view of best results
fig2, axes = plt.subplots(1, 2, figsize=(14, 5))

# Left: Map with spikes highlighted
ax = axes[0]
ax.plot(baseline_lons, baseline_lats, 'o-', linewidth=1.5, markersize=2, label='Baseline (with spikes)', alpha=0.6, color='GRAY')
ax.plot(app4_lons, app4_lats, 's-', linewidth=2, markersize=3, label='Robust Kalman (cleaned)', color='GREEN', alpha=0.9)

# Highlight large spikes in baseline
for i in range(len(baseline_steps)):
    if baseline_steps[i] > 5:
        ax.plot(baseline_lons[i:i+2], baseline_lats[i:i+2], 'r-', linewidth=2.5, alpha=0.7)

ax.set_xlabel('Longitude (deg)', fontsize=10)
ax.set_ylabel('Latitude (deg)', fontsize=10)
ax.set_title('Trajectory with Spikes Highlighted (Red)', fontsize=11, weight='bold')
ax.legend(fontsize=9)
ax.grid(True, alpha=0.3)

# Right: Before/After step distance
ax = axes[1]
epochs_baseline = range(len(baseline_steps))
epochs_app4 = range(len(app4_steps))

# Plot baseline with color coding for spikes
colors = ['red' if s > 5 else 'black' if s > 3 else 'gray' for s in baseline_steps]
for i, (x, y, c) in enumerate(zip(epochs_baseline, baseline_steps, colors)):
    ax.scatter(x, y, color=c, s=30, alpha=0.6)

ax.plot(epochs_app4, app4_steps, 's-', linewidth=2, markersize=3, label='After Robust Kalman', color='GREEN', alpha=0.8)
ax.axhline(y=3, color='orange', linestyle='--', linewidth=1.5, alpha=0.7, label='3m threshold')
ax.axhline(y=5, color='red', linestyle='--', linewidth=1.5, alpha=0.7, label='5m threshold')

# Add legend with color meanings
from matplotlib.patches import Patch
legend_elements = [
    plt.Line2D([0], [0], marker='o', color='w', markerfacecolor='red', markersize=6, label='Baseline >5m (spike)'),
    plt.Line2D([0], [0], marker='o', color='w', markerfacecolor='black', markersize=6, label='Baseline >3m'),
    plt.Line2D([0], [0], marker='o', color='w', markerfacecolor='gray', markersize=6, label='Baseline normal'),
    plt.Line2D([0], [0], marker='s', color='w', markerfacecolor='green', markersize=6, label='Kalman result'),
]
ax.legend(handles=legend_elements, loc='upper right', fontsize=8)

ax.set_xlabel('Epoch', fontsize=10)
ax.set_ylabel('Step Distance (m)', fontsize=10)
ax.set_title('Before/After: Spike Removal', fontsize=11, weight='bold')
ax.grid(True, alpha=0.3)
ax.set_ylim([0, 14])

plt.tight_layout()
plt.savefig('trajectory_before_after_detail.png', dpi=150, bbox_inches='tight')
print("Saved: trajectory_before_after_detail.png")

print("\n✓ All visualizations created successfully!")
