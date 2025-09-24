import matplotlib.pyplot as plt
import numpy as np
import io
import random

def render_angle(angle: int, show_label: bool = False) -> bytes:
    """
    Render an angle image (0–359°).
    - Base ray is randomly oriented.
    - Draws the actual angle span (reflex if >180°).
    - Correctly handles wraparound across 0°.
    - Optionally shows the angle label (for reveal phase).
    Returns PNG bytes buffer.
    """
    fig, ax = plt.subplots(figsize=(4, 4))
    ax.set_aspect('equal')
    ax.axis('off')

    # Circle outline
    circle = plt.Circle((0, 0), 1, fill=False, linestyle="--", alpha=0.3)
    ax.add_artist(circle)

    # Random base orientation
    base_angle_deg = random.randint(0, 359)
    rad1 = np.deg2rad(base_angle_deg)

    # Second ray = base + angle (unwrapped)
    rad2 = rad1 + np.deg2rad(angle)

    # Normalize both to [0, 2π) for plotting rays
    rad1_mod = rad1 % (2*np.pi)
    rad2_mod = rad2 % (2*np.pi)

    # Draw rays
    ax.plot([0, np.cos(rad1_mod)], [0, np.sin(rad1_mod)], color="black", lw=2)
    ax.plot([0, np.cos(rad2_mod)], [0, np.sin(rad2_mod)], color="black", lw=2)

    # Draw arc for true angle (may exceed 2π)
    theta = np.linspace(rad1, rad2, 400)  # use unwrapped values
    ax.plot(0.3*np.cos(theta), 0.3*np.sin(theta), color="red", lw=2)

    # Optional label at midpoint of arc
    if show_label:
        mid_angle = (rad1 + rad2) / 2
        ax.text(0.4*np.cos(mid_angle), 0.4*np.sin(mid_angle),
                f"{angle}°", ha="center", va="center",
                color="red", fontsize=12, weight="bold")

    # Save as PNG buffer
    buf = io.BytesIO()
    plt.savefig(buf, format="png", bbox_inches="tight", transparent=True)
    plt.close(fig)
    buf.seek(0)
    return buf