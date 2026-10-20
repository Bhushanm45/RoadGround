import matplotlib.pyplot as plt
import matplotlib.patches as patches

# -------------------------------------------------------------
# 1. Slide 2: Problem -> Solution -> Innovation Concept Flowchart
# -------------------------------------------------------------
fig, ax = plt.subplots(figsize=(18, 1.8), dpi=300)
ax.set_xlim(0, 18)
ax.set_ylim(0, 1.8)
ax.axis('off')

cards = [
    ("1. THE CHALLENGE (PROBLEM)", 
     "• Potholes cause accidents & vehicle damage\n• Manual road surveys are slow & expensive\n• Speed breakers cause false pothole alarms", 
     "#DC2626", "#FEF2F2", "#FECACA"),
    ("2. ROADGUARD AI (SOLUTION)", 
     "• Mount MPU6050 sensor on PMPML transit buses\n• Capture 6-DOF acceleration & gyro telemetry\n• ML classifier categorizes road event types", 
     "#0284C7", "#EFF6FF", "#BFDBFE"),
    ("3. CORE INNOVATION (UNIQUENESS)", 
     "• Public buses act as autonomous crowd-sensors\n• Classifies waveform patterns vs raw thresholds\n• Highly scalable, sub-$10 low-cost hardware", 
     "#0D9488", "#F0FDFA", "#99F6E4")
]

w = 4.8
h = 1.6
gap = 1.3
start_x = 0.5

for i, (title, points, color_h, color_bg, color_b) in enumerate(cards):
    x = start_x + i * (w + gap)
    y = 0.1
    # Main box
    box = patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.08,rounding_size=0.12",
                                facecolor=color_bg, edgecolor=color_b, linewidth=1.5)
    ax.add_patch(box)
    # Header bar
    h_box = patches.FancyBboxPatch((x, y + h - 0.44), w, 0.44, boxstyle="round,pad=0.08,rounding_size=0.12",
                                  facecolor=color_h, edgecolor=color_h, linewidth=1.0)
    ax.add_patch(h_box)
    ax.text(x + w/2, y + h - 0.22, title, color="white", fontsize=10.5, fontweight='bold', ha='center', va='center')
    ax.text(x + 0.25, y + (h - 0.44)/2, points, color="#1E293B", fontsize=9.2, fontweight='medium', va='center', linespacing=1.35)
    
    # Connecting arrow
    if i < len(cards) - 1:
        arr_x = x + w + 0.15
        arr_y = y + h/2
        ax.annotate('', xy=(arr_x + gap - 0.3, arr_y), xytext=(arr_x, arr_y),
                    arrowprops=dict(facecolor='#0284C7', edgecolor='#0369A1', width=3.0, headwidth=8, headlength=9))
        label_text = "SOLVED BY" if i == 0 else "DELIVERS"
        ax.text(arr_x + (gap - 0.3)/2, arr_y + 0.25, label_text, color='#0369A1', fontsize=7.8, fontweight='bold', ha='center')

plt.tight_layout()
s2_flow_path = 'C:/Users/aryan/.gemini/antigravity/scratch/RoadGuard-AI/assets/slide2_concept_flowchart.png'
plt.savefig(s2_flow_path, dpi=300, bbox_inches='tight')
plt.close()
print("Saved Slide 2 concept flowchart to:", s2_flow_path)


# -------------------------------------------------------------
# 2. Slide 5: Future Scope Roadmap Flowchart
# -------------------------------------------------------------
fig, ax = plt.subplots(figsize=(10, 1.4), dpi=300)
ax.set_xlim(0, 10)
ax.set_ylim(0, 1.4)
ax.axis('off')

steps_s5 = [
    ("1. GPS Telemetry", "Geotag Potholes"),
    ("2. GIS Dashboard", "Municipal Map"),
    ("3. Fleet Fusion", "Multi-Bus Voting"),
    ("4. Severity Index", "Impact Depth"),
    ("5. Auto-Ticket", "ERP Dispatch")
]

w5 = 1.55
h5 = 1.15
gap5 = 0.45
start_x5 = 0.12

for i, (st, desc) in enumerate(steps_s5):
    x = start_x5 + i * (w5 + gap5)
    y = 0.12
    box = patches.FancyBboxPatch((x, y), w5, h5, boxstyle="round,pad=0.06,rounding_size=0.1",
                                facecolor="#F8FAFC", edgecolor="#0284C7", linewidth=1.2)
    ax.add_patch(box)
    h_box = patches.FancyBboxPatch((x, y + h5 - 0.38), w5, 0.38, boxstyle="round,pad=0.06,rounding_size=0.1",
                                  facecolor="#0284C7", edgecolor="#0284C7", linewidth=1.0)
    ax.add_patch(h_box)
    ax.text(x + w5/2, y + h5 - 0.19, st, color="white", fontsize=8.2, fontweight='bold', ha='center', va='center')
    ax.text(x + w5/2, y + (h5 - 0.38)/2, desc, color="#0F2942", fontsize=7.8, fontweight='semibold', ha='center', va='center')
    
    if i < len(steps_s5) - 1:
        arr_x = x + w5 + 0.05
        arr_y = y + h5/2
        ax.annotate('', xy=(arr_x + gap5 - 0.1, arr_y), xytext=(arr_x, arr_y),
                    arrowprops=dict(facecolor='#64748B', edgecolor='#475569', width=1.5, headwidth=5, headlength=6))

plt.tight_layout()
s5_flow_path = 'C:/Users/aryan/.gemini/antigravity/scratch/RoadGuard-AI/assets/slide5_roadmap_flowchart.png'
plt.savefig(s5_flow_path, dpi=300, bbox_inches='tight')
plt.close()
print("Saved Slide 5 roadmap flowchart to:", s5_flow_path)
