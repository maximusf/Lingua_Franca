"""
SmartRoute Visualization — Generates pitch-ready accuracy charts from
evaluation metrics produced by evaluate.py.

Reads metrics.json and history.json from data/synthetic/ and produces:
  1. Bar chart: extraction & routing accuracy by file type
  2. Line chart: accuracy improvement over evaluation runs (from history.json)
  3. Per-field accuracy horizontal bar chart

Usage:
  python tests/evaluate.py --label "baseline"    # run eval first
  python tests/visualize.py                       # then generate charts

Output: data/synthetic/charts/ (PNG files ready for slides)
"""

import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.ticker as mtick

PROJECT_ROOT = Path(__file__).resolve().parent.parent
METRICS_PATH = PROJECT_ROOT / "data" / "synthetic" / "metrics.json"
HISTORY_PATH = PROJECT_ROOT / "data" / "synthetic" / "history.json"
CHARTS_DIR = PROJECT_ROOT / "data" / "synthetic" / "charts"

# Clean, presentation-friendly style
plt.rcParams.update({
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "axes.grid": True,
    "grid.alpha": 0.3,
    "font.size": 12,
    "axes.titlesize": 16,
    "axes.labelsize": 13,
})

COLORS = {
    "extraction": "#2196F3",
    "routing": "#4CAF50",
    "accent": "#FF9800",
    "field_bars": "#1976D2",
}


def chart_accuracy_by_file_type(metrics):
    """Bar chart comparing extraction and routing accuracy across file types."""
    by_type = metrics.get("accuracy_by_file_type", {})
    if not by_type:
        print("  Skipped: no file type data")
        return

    types = list(by_type.keys())
    extraction = [by_type[t]["extraction_accuracy"] * 100 for t in types]
    routing = [by_type[t]["routing_accuracy"] * 100 for t in types]
    counts = [by_type[t]["count"] for t in types]

    labels = [f"{t.upper()}\n(n={c})" for t, c in zip(types, counts)]

    fig, ax = plt.subplots(figsize=(10, 6))
    x = range(len(types))
    width = 0.35

    bars1 = ax.bar([i - width / 2 for i in x], extraction, width,
                   label="Extraction Accuracy", color=COLORS["extraction"], edgecolor="white")
    bars2 = ax.bar([i + width / 2 for i in x], routing, width,
                   label="Routing Accuracy", color=COLORS["routing"], edgecolor="white")

    # Value labels on bars
    for bar in bars1:
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 1,
                f"{bar.get_height():.0f}%", ha="center", va="bottom", fontsize=11, fontweight="bold")
    for bar in bars2:
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 1,
                f"{bar.get_height():.0f}%", ha="center", va="bottom", fontsize=11, fontweight="bold")

    ax.set_xticks(list(x))
    ax.set_xticklabels(labels)
    ax.set_ylabel("Accuracy (%)")
    ax.set_title("Pipeline Accuracy by Document Type")
    ax.set_ylim(0, 115)
    ax.yaxis.set_major_formatter(mtick.PercentFormatter())
    ax.legend(loc="upper right")

    fig.tight_layout()
    path = CHARTS_DIR / "accuracy_by_file_type.png"
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"  Saved: {path}")


def chart_history(history):
    """Line chart showing accuracy improvement across evaluation runs."""
    if not history or len(history) < 1:
        print("  Skipped: no history data (run evaluate.py multiple times with --label)")
        return

    labels = []
    for i, entry in enumerate(history):
        label = entry.get("label") or f"Run {i + 1}"
        labels.append(label)

    extraction_rates = [entry["perfect_extraction_rate"] * 100 for entry in history]
    routing_rates = [entry["perfect_routing_rate"] * 100 for entry in history]

    fig, ax = plt.subplots(figsize=(10, 6))
    x = range(len(history))

    ax.plot(list(x), extraction_rates, "o-", color=COLORS["extraction"],
            linewidth=2.5, markersize=8, label="Extraction Accuracy")
    ax.plot(list(x), routing_rates, "s-", color=COLORS["routing"],
            linewidth=2.5, markersize=8, label="Routing Accuracy")

    # Annotate points
    for i, (ext, rout) in enumerate(zip(extraction_rates, routing_rates)):
        ax.annotate(f"{ext:.0f}%", (i, ext), textcoords="offset points",
                    xytext=(0, 12), ha="center", fontsize=10, color=COLORS["extraction"])
        ax.annotate(f"{rout:.0f}%", (i, rout), textcoords="offset points",
                    xytext=(0, -18), ha="center", fontsize=10, color=COLORS["routing"])

    ax.set_xticks(list(x))
    ax.set_xticklabels(labels, rotation=30, ha="right")
    ax.set_ylabel("Accuracy (%)")
    ax.set_title("SmartRoute Accuracy Over Iterations")
    ax.set_ylim(0, 105)
    ax.yaxis.set_major_formatter(mtick.PercentFormatter())
    ax.legend(loc="lower right")

    fig.tight_layout()
    path = CHARTS_DIR / "accuracy_over_time.png"
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"  Saved: {path}")


def chart_per_field_accuracy(metrics):
    """Horizontal bar chart showing accuracy for each extracted field."""
    field_accuracy = metrics.get("field_accuracy", {})
    if not field_accuracy:
        print("  Skipped: no field accuracy data")
        return

    # Sort by accuracy ascending (worst at top for visual impact)
    sorted_fields = sorted(field_accuracy.items(), key=lambda kv: kv[1]["accuracy"])

    fields = [f.replace("_", " ").title() for f, _ in sorted_fields]
    accuracies = [stats["accuracy"] * 100 for _, stats in sorted_fields]

    # Color bars by performance tier
    bar_colors = []
    for acc in accuracies:
        if acc >= 90:
            bar_colors.append("#4CAF50")   # green
        elif acc >= 70:
            bar_colors.append("#FF9800")   # orange
        else:
            bar_colors.append("#F44336")   # red

    fig, ax = plt.subplots(figsize=(10, 7))
    bars = ax.barh(fields, accuracies, color=bar_colors, edgecolor="white", height=0.7)

    # Value labels
    for bar, acc in zip(bars, accuracies):
        ax.text(bar.get_width() + 1.5, bar.get_y() + bar.get_height() / 2,
                f"{acc:.0f}%", va="center", fontsize=11, fontweight="bold")

    ax.set_xlim(0, 110)
    ax.set_xlabel("Accuracy (%)")
    ax.set_title("Per-Field Extraction Accuracy")
    ax.xaxis.set_major_formatter(mtick.PercentFormatter())

    fig.tight_layout()
    path = CHARTS_DIR / "per_field_accuracy.png"
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"  Saved: {path}")


def main():
    if not METRICS_PATH.exists():
        print(f"No metrics found at {METRICS_PATH}")
        print("Run: python tests/evaluate.py first")
        sys.exit(1)

    CHARTS_DIR.mkdir(parents=True, exist_ok=True)

    metrics = json.loads(METRICS_PATH.read_text(encoding="utf-8"))

    # Print headline numbers
    print("\n=== SmartRoute Evaluation Summary ===")
    print(f"  Extraction accuracy: {metrics['perfect_extraction_rate']:.1%}")
    print(f"  Routing accuracy:    {metrics['perfect_routing_rate']:.1%}")
    print(f"  Records processed:   {metrics['successful']}/{metrics['total_records']}")
    print()

    print("Generating charts...")
    chart_accuracy_by_file_type(metrics)
    chart_per_field_accuracy(metrics)

    # History chart (needs at least 1 run)
    history = []
    if HISTORY_PATH.exists():
        history = json.loads(HISTORY_PATH.read_text(encoding="utf-8"))
    chart_history(history)

    print(f"\nAll charts saved to: {CHARTS_DIR}/")


if __name__ == "__main__":
    main()
