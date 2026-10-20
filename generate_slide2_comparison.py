import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches

fig, axes = plt.subplots(1, 3, figsize=(16, 4.2), dpi=300)

# Card 1: Pothole
ax = axes[0]
ax.set_xlim(0, 10)
ax.set_ylim(0, 10)
ax.axis('off')

# Header box
rect = patches.FancyBboxPatch((0.2, 8.4), 9.6, 1.4, boxstyle="round,pad=0.2", facecolor="#DC2626", edgecolor="#B91C1C", linewidth=1.5)
ax.add_patch(rect)
ax.text(5.0, 9.1, "POTHOLE (Structural Cavity)", color="white", fontsize=12.5, fontweight='bold', ha='center', va='center')

# Road profile mini illustration
x_prof = np.linspace(0.8, 9.2, 200)
y_prof = np.zeros_like(x_prof) + 7.1
y_prof[(x_prof >= 3.6) & (x_prof <= 6.4)] = 5.8  # cavity
ax.plot(x_prof, y_prof, color="#1E293B", linewidth=3.8)
ax.fill_between(x_prof, y_prof, 5.0, color="#CBD5E1", alpha=0.55)
ax.text(5.0, 5.3, "Sharp Cavity Drop (-Δh)", color="#DC2626", fontsize=10, fontweight='bold', ha='center')

# Details Card
content_rect = patches.FancyBboxPatch((0.2, 0.1), 9.6, 4.7, boxstyle="round,pad=0.2", facecolor="#FEF2F2", edgecolor="#FECACA", linewidth=1.5)
ax.add_patch(content_rect)
text_pothole = (
    "• Physical Geometry:\n"
    "  Sudden depression / missing chunk of asphalt road\n\n"
    "• Sensor Impact Signature (Z-Axis):\n"
    "  Sharp downward drop (-0.5g) followed by violent\n"
    "  rebound shock (> +3.0g). Transient duration: 150-250ms\n\n"
    "• ML Classification Decision:\n"
    "  High peak-to-peak delta + short duration\n"
    "  → FLAGGED FOR MUNICIPAL ROAD REPAIR"
)
ax.text(0.5, 4.6, text_pothole, color="#7F1D1D", fontsize=9.2, va='top', linespacing=1.2, fontweight='medium')


# Card 2: Speed Breaker
ax = axes[1]
ax.set_xlim(0, 10)
ax.set_ylim(0, 10)
ax.axis('off')

rect = patches.FancyBboxPatch((0.2, 8.4), 9.6, 1.4, boxstyle="round,pad=0.2", facecolor="#D97706", edgecolor="#B45309", linewidth=1.5)
ax.add_patch(rect)
ax.text(5.0, 9.1, "SPEED BREAKER (Engineered Hump)", color="white", fontsize=12.5, fontweight='bold', ha='center', va='center')

# Road profile mini illustration
x_prof2 = np.linspace(0.8, 9.2, 200)
y_prof2 = np.zeros_like(x_prof2) + 5.8
mask = (x_prof2 >= 2.8) & (x_prof2 <= 7.2)
y_prof2[mask] = 5.8 + 1.35 * np.sin(np.pi * (x_prof2[mask] - 2.8) / 4.4)
ax.plot(x_prof2, y_prof2, color="#1E293B", linewidth=3.8)
ax.fill_between(x_prof2, y_prof2, 5.0, color="#CBD5E1", alpha=0.55)
ax.text(5.0, 7.5, "Convex Elevation (+Δh)", color="#D97706", fontsize=10, fontweight='bold', ha='center')

# Details Card
content_rect2 = patches.FancyBboxPatch((0.2, 0.1), 9.6, 4.7, boxstyle="round,pad=0.2", facecolor="#FFFBEB", edgecolor="#FDE68A", linewidth=1.5)
ax.add_patch(content_rect2)
text_bump = (
    "• Physical Geometry:\n"
    "  Engineered rounded asphalt / rubber elevation\n\n"
    "• Sensor Impact Signature (Z-Axis):\n"
    "  Smooth, low-frequency sinusoidal rise & dip\n"
    "  (0.8-1.5 Hz). Sustained duration: 600-900ms\n\n"
    "• ML Classification Decision:\n"
    "  Smooth symmetric profile + extended duration\n"
    "  → NORMAL TRAFFIC CALMING (No Damage Alert)"
)
ax.text(0.5, 4.6, text_bump, color="#78350F", fontsize=9.2, va='top', linespacing=1.2, fontweight='medium')


# Card 3: Rough Road
ax = axes[2]
ax.set_xlim(0, 10)
ax.set_ylim(0, 10)
ax.axis('off')

rect = patches.FancyBboxPatch((0.2, 8.4), 9.6, 1.4, boxstyle="round,pad=0.2", facecolor="#0284C7", edgecolor="#0369A1", linewidth=1.5)
ax.add_patch(rect)
ax.text(5.0, 9.1, "ROUGH ROAD (Surface Texture)", color="white", fontsize=12.5, fontweight='bold', ha='center', va='center')

# Road profile mini illustration
np.random.seed(99)
x_prof3 = np.linspace(0.8, 9.2, 200)
y_prof3 = 6.0 + 0.28 * np.sin(20 * x_prof3) + 0.16 * np.random.normal(0, 0.4, 200)
ax.plot(x_prof3, y_prof3, color="#1E293B", linewidth=2.8)
ax.fill_between(x_prof3, y_prof3, 5.0, color="#CBD5E1", alpha=0.55)
ax.text(5.0, 7.1, "Continuous Irregular Chatter", color="#0284C7", fontsize=10, fontweight='bold', ha='center')

# Details Card
content_rect3 = patches.FancyBboxPatch((0.2, 0.1), 9.6, 4.7, boxstyle="round,pad=0.2", facecolor="#F0F9FF", edgecolor="#BAE6FD", linewidth=1.5)
ax.add_patch(content_rect3)
text_rough = (
    "• Physical Geometry:\n"
    "  Worn aggregate, patchy asphalt tar, micro-cracks\n\n"
    "• Sensor Impact Signature (Z-Axis):\n"
    "  Persistent stochastic multi-frequency vibration\n"
    "  without solitary extreme spikes. RMS ~0.35g\n\n"
    "• ML Classification Decision:\n"
    "  High variance baseline without isolated impulse\n"
    "  → ROAD ROUGHNESS LOG (Prevents False Alarms)"
)
ax.text(0.5, 4.6, text_rough, color="#0C4A6E", fontsize=9.2, va='top', linespacing=1.2, fontweight='medium')

plt.tight_layout()
output_path = 'C:/Users/aryan/.gemini/antigravity/scratch/RoadGuard-AI/assets/comparison_cards.png'
plt.savefig(output_path, dpi=300, bbox_inches='tight')
plt.close()
print("Saved perfectly padded comparison cards to:", output_path)
