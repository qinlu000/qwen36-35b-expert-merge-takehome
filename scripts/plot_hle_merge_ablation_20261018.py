"""Plot the frozen HLE merge ablation table from a small local CSV."""
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
source = ROOT / "curves" / "source" / "hle_merge_ablation_20261018.csv"
output = ROOT / "curves" / "hle_merge_ablation_20261018.png"

df = pd.read_csv(source)
fig, ax = plt.subplots(figsize=(7.2, 4.0), dpi=180)
bars = ax.bar(df["model"], df["score_percent"], color=["#607D8B", "#2E7D32", "#8E44AD", "#1565C0", "#607D8B", "#EF6C00"])
ax.set_ylabel("HLE accuracy (%)")
ax.set_title("HLE merge ablation (2500-question disclosed view)")
ax.set_ylim(0, max(df["score_percent"]) * 1.25)
ax.grid(axis="y", alpha=0.25)
ax.set_axisbelow(True)
ax.tick_params(axis="x", rotation=25)
for bar, value in zip(bars, df["score_percent"]):
    ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.05, f"{value:.2f}", ha="center", va="bottom", fontsize=8)
fig.tight_layout()
fig.savefig(output, bbox_inches="tight")
print(output)
