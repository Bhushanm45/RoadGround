import matplotlib.pyplot as plt
import matplotlib.patches as patches

fig, ax = plt.subplots(figsize=(4.8, 4.4), dpi=300)
ax.set_xlim(0, 4.8)
ax.set_ylim(0, 4.4)
ax.axis('off')

ml_steps = [
    ("1. DATA ACQUISITION", "Collect 6-DOF accel & gyro streams on routes", "#1E293B"),
    ("2. PREPROCESSING", "Zero-drift calibration & gravity removal (1g)", "#0284C7"),
    ("3. FEATURE EXTRACTION", "Peak-to-peak delta, RMS, duration, kurtosis", "#4F46E5"),
    ("4. MODEL TRAINING", "Random Forest classifier cross-validation", "#7C3AED"),
    ("5. REAL-TIME INFERENCE", "Categorize: Pothole / Speed Breaker / Rough", "#059669")
]

w = 4.4
h = 0.58
gap = 0.16
start_x = 0.2
start_y = 3.65

for i, (title, desc, color) in enumerate(ml_steps):
    y = start_y - i * (h + gap)
    box = patches.FancyBboxPatch((start_x, y), w, h, boxstyle="round,pad=0.04,rounding_size=0.08",
                                facecolor="#FFFFFF", edgecolor=color, linewidth=1.5)
    ax.add_patch(box)
    
    # Left color strip
    strip = patches.FancyBboxPatch((start_x, y), 0.2, h, boxstyle="round,pad=0.04,rounding_size=0.08",
                                  facecolor=color, edgecolor=color, linewidth=1.0)
    ax.add_patch(strip)
    
    # Title
    ax.text(start_x + 0.35, y + h - 0.18, title, color=color, fontsize=8.8, fontweight='bold', va='center')
    # Desc
    ax.text(start_x + 0.35, y + 0.16, desc, color="#334155", fontsize=7.8, fontweight='medium', va='center')
    
    # Connecting down arrow
    if i < len(ml_steps) - 1:
        arr_y = y - 0.02
        ax.annotate('', xy=(start_x + w/2, arr_y - gap + 0.04), xytext=(start_x + w/2, arr_y),
                    arrowprops=dict(facecolor='#64748B', edgecolor='#475569', width=1.5, headwidth=4.5, headlength=5))

plt.tight_layout()
s3_ml_path = 'C:/Users/aryan/.gemini/antigravity/scratch/RoadGuard-AI/assets/slide3_ml_flowchart.png'
plt.savefig(s3_ml_path, dpi=300, bbox_inches='tight')
plt.close()
print("Saved Slide 3 ML flowchart to:", s3_ml_path)
