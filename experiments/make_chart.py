"""Chart: correct matches vs false matches across thresholds (reads <lib>_sweep.csv).
Usage: python experiments/make_chart.py uniface
"""
import os, sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

lib = sys.argv[1]
res = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
d = pd.read_csv(os.path.join(res, f"{lib}_sweep.csv"))
fig, ax = plt.subplots(figsize=(9, 6))
ax.plot(d.threshold, 100 * d.A_correct / d.A_total, color="#1b7f3b", lw=2.2,
        label=f"Correct matches - test A (of {d.A_total[0]} known people)")
ax.plot(d.threshold, 100 * d.B_false_matches / d.B_total, color="#c0392b", lw=2.2,
        label=f"False matches - test B (of {d.B_total[0]} unknown people)")
ax.plot(d.threshold, 100 * d.D_wrong_names / d.D_total, color="#c0392b", lw=1.5, ls="--",
        label=f"Wrong names - test D groups (of {d.D_total[0]} faces)")
ax.set_xlabel("Threshold (cosine distance; a face gets a name only if distance <= threshold)")
ax.set_ylabel("% of test faces")
ax.set_ylim(-3, 103)
ax.set_title(f"{lib}: correct vs false matches across thresholds")
ax.grid(alpha=0.3)
ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.16), frameon=False)
fig.tight_layout()
fig.savefig(os.path.join(res, f"{lib}_threshold_chart.png"), dpi=150)
