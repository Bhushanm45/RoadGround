import numpy as np
import matplotlib.pyplot as plt
import os

plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')
fig, axes = plt.subplots(1, 3, figsize=(15, 4.2), dpi=300)

time = np.linspace(0, 2.0, 1000)

# 1. Pothole: Sudden sharp negative drop followed by high positive rebound spike
np.random.seed(42)
noise1 = np.random.normal(0, 0.04, len(time))
t_pothole = time - 0.95
drop = -1.5 * np.exp(-((t_pothole + 0.06)**2) / 0.002)
spike = 2.4 * np.exp(-((t_pothole - 0.06)**2) / 0.003)
ring = 0.4 * np.exp(-t_pothole**2 / 0.02) * np.sin(40 * t_pothole)
az_pothole = 1.0 + drop + spike + ring + noise1

ax1 = axes[0]
ax1.plot(time, az_pothole, color='#DC2626', linewidth=2.4)
ax1.axhline(1.0, color='#64748B', linestyle='--', linewidth=1.2, alpha=0.8)
ax1.set_title("POTHOLE (Illustrative Model Profile)", fontsize=11.5, fontweight='bold', color='#991B1B', pad=8)
ax1.set_xlabel("Time (s)", fontsize=9.5, fontweight='bold')
ax1.set_ylabel("Vertical Acceleration (g)", fontsize=9.5, fontweight='bold')
ax1.set_ylim(-1.0, 4.3)
ax1.grid(True, linestyle=':', alpha=0.6)
ax1.annotate('Illustrative Rebound', xy=(1.01, 3.4), xytext=(1.05, 3.7),
             arrowprops=dict(facecolor='#DC2626', shrink=0.08, width=1.5, headwidth=5),
             fontsize=8.5, fontweight='bold', color='#991B1B')
ax1.annotate('Sharp Drop', xy=(0.89, -0.5), xytext=(0.20, -0.1),
             arrowprops=dict(facecolor='#DC2626', shrink=0.08, width=1.5, headwidth=5),
             fontsize=8.5, fontweight='bold', color='#991B1B')
ax1.text(0.04, 0.65, "Illustrative Features:\n• Duration: ~150–250 ms (typical)\n• Rebound Shock: Δg > 3.0g\n• High Kurtosis & Crest Factor\n*Subject to empirical sensor calibration", 
         transform=ax1.transAxes, fontsize=8.0, fontweight='semibold',
         bbox=dict(boxstyle='round,pad=0.4', facecolor='#FEF2F2', edgecolor='#FECACA', alpha=0.95))

# 2. Speed Breaker: Smooth, low-frequency sinusoidal pulse
noise2 = np.random.normal(0, 0.03, len(time))
t_bump = time - 1.0
bump = 0.95 * np.sin(np.pi * (t_bump + 0.35) / 0.7) * (np.abs(t_bump) <= 0.35)
az_bump = 1.0 + bump + noise2

ax2 = axes[1]
ax2.plot(time, az_bump, color='#D97706', linewidth=2.4)
ax2.axhline(1.0, color='#64748B', linestyle='--', linewidth=1.2, alpha=0.8)
ax2.set_title("SPEED BREAKER (Illustrative Model Profile)", fontsize=11.5, fontweight='bold', color='#B45309', pad=8)
ax2.set_xlabel("Time (s)", fontsize=9.5, fontweight='bold')
ax2.set_ylabel("Vertical Acceleration (g)", fontsize=9.5, fontweight='bold')
ax2.set_ylim(-1.0, 4.3)
ax2.grid(True, linestyle=':', alpha=0.6)
ax2.annotate('Illustrative Crest', xy=(1.0, 1.95), xytext=(1.10, 2.7),
             arrowprops=dict(facecolor='#D97706', shrink=0.08, width=1.5, headwidth=5),
             fontsize=8.5, fontweight='bold', color='#B45309')
ax2.text(0.04, 0.65, "Illustrative Features:\n• Duration: ~600–900 ms (speed-dependent)\n• Smooth, Symmetric Curve\n• Low Frequency (~1.2–2.0 Hz)\n*Varies by bus speed & hump geometry", 
         transform=ax2.transAxes, fontsize=8.0, fontweight='semibold',
         bbox=dict(boxstyle='round,pad=0.4', facecolor='#FFFBEB', edgecolor='#FDE68A', alpha=0.95))

# 3. Rough Road: Continuous high-frequency stochastic vibration
noise3 = np.random.normal(0, 0.28, len(time))
texture = 0.18 * np.sin(25 * time) + 0.12 * np.cos(45 * time)
az_rough = 1.0 + texture + noise3

ax3 = axes[2]
ax3.plot(time, az_rough, color='#0284C7', linewidth=1.6)
ax3.axhline(1.0, color='#64748B', linestyle='--', linewidth=1.2, alpha=0.8)
ax3.set_title("ROUGH ROAD (Illustrative Model Profile)", fontsize=11.5, fontweight='bold', color='#0369A1', pad=8)
ax3.set_xlabel("Time (s)", fontsize=9.5, fontweight='bold')
ax3.set_ylabel("Vertical Acceleration (g)", fontsize=9.5, fontweight='bold')
ax3.set_ylim(-1.0, 4.3)
ax3.grid(True, linestyle=':', alpha=0.6)
ax3.text(0.04, 0.65, "Illustrative Features:\n• Duration: Continuous / Texture\n• Moderate Spread (±0.4g typical)\n• High Variance, No Single Peak\n*Baseline depends on vehicle suspension", 
         transform=ax3.transAxes, fontsize=8.0, fontweight='semibold',
         bbox=dict(boxstyle='round,pad=0.4', facecolor='#F0F9FF', edgecolor='#BAE6FD', alpha=0.95))

plt.figtext(0.5, 0.01, "*Note: Waveforms and threshold values are illustrative model profiles from road-vibration literature; exact operational values will be empirically calibrated using onboard bus sensor data.", 
            ha='center', fontsize=8.2, style='italic', color='#475569')

plt.subplots_adjust(bottom=0.15, top=0.90, left=0.06, right=0.97, wspace=0.22)

os.makedirs('assets', exist_ok=True)
plt.savefig('assets/waveforms.png', dpi=300)
plt.savefig('vibration_waveforms.png', dpi=300)
plt.close()
print("Saved illustrative waveforms to assets/waveforms.png and vibration_waveforms.png")
