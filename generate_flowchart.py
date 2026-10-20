import matplotlib.pyplot as plt
import matplotlib.patches as patches

fig, ax = plt.subplots(figsize=(18, 2.2), dpi=300)
ax.set_xlim(0, 18)
ax.set_ylim(0, 2.2)
ax.axis('off')

steps = [
    ("1. BUS TRAVELS", "PMPML transit bus\nmoves on regular route", "#1E293B"),
    ("2. SENSOR ACQUISITION", "MPU6050 records 6-DOF\naccel (g) & gyro (deg/s)", "#0284C7"),
    ("3. MICROCONTROLLER", "ESP32 / Arduino samples\nraw I2C signals @ 50-100Hz", "#0D9488"),
    ("4. SIGNAL PREPROCESSING", "Bandpass filter, windowing &\nfeature extraction (peak, RMS)", "#4F46E5"),
    ("5. TRAINED ML MODEL", "Random Forest classifies\nextracted feature vector", "#7C3AED"),
    ("6. 3-CLASS DECISION", "Pothole vs Speed Breaker\nvs Rough Road", "#D97706"),
    ("7. LOG & MAPPING", "Pothole timestamped, logged\n& optional GPS mapped", "#DC2626")
]

box_width = 2.15
box_height = 1.85
gap = 0.35
start_x = 0.15

for i, (title, desc, color) in enumerate(steps):
    x = start_x + i * (box_width + gap)
    y = 0.15
    
    # Outer box
    box = patches.FancyBboxPatch((x, y), box_width, box_height,
                                boxstyle="round,pad=0.08,rounding_size=0.15",
                                facecolor="#FFFFFF", edgecolor=color, linewidth=2.0)
    ax.add_patch(box)
    
    # Title bar
    header_box = patches.FancyBboxPatch((x, y + box_height - 0.55), box_width, 0.55,
                                       boxstyle="round,pad=0.08,rounding_size=0.15",
                                       facecolor=color, edgecolor=color, linewidth=1.0)
    ax.add_patch(header_box)
    
    # Title text
    ax.text(x + box_width/2, y + box_height - 0.28, title, color="white",
            fontsize=8.5, fontweight='bold', ha='center', va='center')
    
    # Desc text
    ax.text(x + box_width/2, y + (box_height - 0.55)/2, desc, color="#334155",
            fontsize=7.8, fontweight='medium', ha='center', va='center', linespacing=1.2)
    
    # Arrow to next box
    if i < len(steps) - 1:
        arrow_x = x + box_width + 0.05
        arrow_y = y + box_height/2
        ax.annotate('', xy=(arrow_x + gap - 0.1, arrow_y), xytext=(arrow_x, arrow_y),
                    arrowprops=dict(facecolor='#64748B', edgecolor='#475569', width=2.0, headwidth=6, headlength=7))

plt.tight_layout()
output_path = 'C:/Users/aryan/.gemini/antigravity/scratch/RoadGuard-AI/methodology_flowchart.png'
plt.savefig(output_path, dpi=300, bbox_inches='tight')
plt.close()
print("Saved methodology flowchart to:", output_path)
