import os
import matplotlib.pyplot as plt
import matplotlib.patches as patches

def generate_placeholder():
    os.makedirs('assets', exist_ok=True)
    out_path = 'assets/prototype_placeholder.png'
    
    # 5.7 x 3.65 inches at 300 DPI
    fig, ax = plt.subplots(figsize=(5.7, 3.65), dpi=300)
    fig.patch.set_facecolor('#F8FAFC')
    ax.set_facecolor('#F8FAFC')

    # Dashed outer border
    rect = patches.FancyBboxPatch((0.02, 0.02), 0.96, 0.96,
                                 boxstyle='round,pad=0.02,rounding_size=0.04',
                                 edgecolor='#0284C7', facecolor='#F0F9FF',
                                 linestyle='--', linewidth=2.0)
    ax.add_patch(rect)

    # Viewfinder corner brackets
    bracket_len = 0.08
    col_b = '#0369A1'
    lw_b = 3.0

    # Top-Left
    ax.plot([0.05, 0.05 + bracket_len], [0.93, 0.93], color=col_b, lw=lw_b, solid_capstyle='round')
    ax.plot([0.05, 0.05], [0.93 - bracket_len, 0.93], color=col_b, lw=lw_b, solid_capstyle='round')

    # Top-Right
    ax.plot([0.95 - bracket_len, 0.95], [0.93, 0.93], color=col_b, lw=lw_b, solid_capstyle='round')
    ax.plot([0.95, 0.95], [0.93 - bracket_len, 0.93], color=col_b, lw=lw_b, solid_capstyle='round')

    # Bottom-Left
    ax.plot([0.05, 0.05 + bracket_len], [0.07, 0.07], color=col_b, lw=lw_b, solid_capstyle='round')
    ax.plot([0.05, 0.05], [0.07, 0.07 + bracket_len], color=col_b, lw=lw_b, solid_capstyle='round')

    # Bottom-Right
    ax.plot([0.95 - bracket_len, 0.95], [0.07, 0.07], color=col_b, lw=lw_b, solid_capstyle='round')
    ax.plot([0.95, 0.95], [0.07, 0.07 + bracket_len], color=col_b, lw=lw_b, solid_capstyle='round')

    # Draw a stylized Camera Graphic with vector patches
    # Camera body
    cam_body = patches.FancyBboxPatch((0.43, 0.64), 0.14, 0.11,
                                     boxstyle='round,pad=0.01,rounding_size=0.02',
                                     edgecolor='#0284C7', facecolor='#0F172A', lw=1.5)
    ax.add_patch(cam_body)
    # Camera top hump / flash
    cam_top = patches.Rectangle((0.475, 0.76), 0.05, 0.025,
                                edgecolor='#0284C7', facecolor='#1E293B', lw=1.2)
    ax.add_patch(cam_top)
    # Camera lens outer ring
    cam_lens_out = patches.Circle((0.50, 0.70), 0.038,
                                  edgecolor='#38BDF8', facecolor='#1E293B', lw=1.5)
    ax.add_patch(cam_lens_out)
    # Camera lens inner circle
    cam_lens_in = patches.Circle((0.50, 0.70), 0.022,
                                 edgecolor='#0284C7', facecolor='#0284C7')
    ax.add_patch(cam_lens_in)
    # Flash dot
    cam_dot = patches.Circle((0.545, 0.725), 0.007,
                             edgecolor='none', facecolor='#38BDF8')
    ax.add_patch(cam_dot)

    # Text annotations
    ax.text(0.50, 0.52, 'SPACE RESERVED FOR PROTOTYPE PHOTO',
            fontsize=12.5, fontweight='bold', color='#0F2942', ha='center', va='center', family='sans-serif')

    ax.text(0.50, 0.42, "[ Right-Click Image > 'Change Picture' or Paste Photo Here ]",
            fontsize=9.8, fontweight='bold', color='#0284C7', ha='center', va='center', family='sans-serif')

    ax.text(0.50, 0.31, 'Recommended: Physical photo of MPU-6050 + ESP32 / Arduino breadboard,\nenclosure casing, or vehicle chassis test setup',
            fontsize=8.5, color='#475569', ha='center', va='center', family='sans-serif', style='italic')

    # Hardware module chips at the bottom
    chip_y = 0.14
    chip_texts = ['MPU-6050 6-Axis IMU', 'ESP32 / Arduino MCU', 'Vibration-Damped Mount', 'Power Unit']
    xs = [0.17, 0.40, 0.65, 0.85]
    ws = [0.21, 0.21, 0.25, 0.13]

    for x, w, t in zip(xs, ws, chip_texts):
        chip = patches.FancyBboxPatch((x - w/2, chip_y - 0.035), w, 0.07,
                                     boxstyle='round,pad=0.01,rounding_size=0.02',
                                     edgecolor='#BAE6FD', facecolor='#E0F2FE')
        ax.add_patch(chip)
        ax.text(x, chip_y, t, fontsize=7.2, fontweight='bold', color='#0369A1', ha='center', va='center', family='sans-serif')

    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis('off')

    plt.subplots_adjust(left=0, right=1, top=1, bottom=0)
    plt.savefig(out_path, dpi=300, facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close()
    print(f"Generated {out_path} cleanly.")

if __name__ == '__main__':
    generate_placeholder()
