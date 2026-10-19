"""Stage 7: the two README charts, written to figures/."""
from pathlib import Path

import duckdb
import matplotlib

matplotlib.use("Agg")  # draw to files, no window
import matplotlib.pyplot as plt

PROJECT_DIR = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_DIR / "data" / "aid_flows.duckdb"
FIGURES_DIR = PROJECT_DIR / "figures"

PLANNED_COLOUR = "#1f4e79"
DISBURSED_COLOUR = "#d98c1f"
RATIO_CAP = 3.0


def planned_vs_disbursed_by_year(connection):
    by_year = connection.execute(
        "SELECT year, planned_usd / 1e6 AS planned_m, disbursed_usd / 1e6 AS disbursed_m, arrived_share FROM mart_by_year ORDER BY year"
    ).df()

    figure, axis = plt.subplots(figsize=(10, 5))
    width = 0.4
    positions = list(range(len(by_year)))
    left_positions = [p - width / 2 for p in positions]
    right_positions = [p + width / 2 for p in positions]
    axis.bar(left_positions, by_year["planned_m"], width, label="Planned (original annual budget)", color=PLANNED_COLOUR)
    axis.bar(right_positions, by_year["disbursed_m"], width, label="Disbursed", color=DISBURSED_COLOUR)
    axis.set_xticks(positions)
    axis.set_xticklabels(by_year["year"].astype(int), rotation=45)
    axis.set_ylabel("US dollars, millions")
    axis.set_title("Kenya: planned and disbursed aid, activities with a full-year annual budget")
    axis.legend()
    figure.tight_layout()
    figure.savefig(FIGURES_DIR / "planned_vs_disbursed_by_year.png", dpi=150)
    plt.close(figure)


def ratio_distribution(connection):
    ratios = connection.execute("SELECT ratio FROM comparable_activity_years").df()["ratio"]
    above_cap = int((ratios > RATIO_CAP).sum())
    shown = ratios.clip(upper=RATIO_CAP)

    figure, axis = plt.subplots(figsize=(10, 5))
    axis.hist(shown, bins=60, color=PLANNED_COLOUR)
    axis.axvline(1.0, color="black", linestyle="--", label="disbursed = planned")
    axis.axvline(0.7, color=DISBURSED_COLOUR, linestyle="--", label="70% of plan")
    axis.set_xlabel(f"Disbursed divided by planned, one activity-year each (values above {RATIO_CAP:.0f} shown at {RATIO_CAP:.0f}; {above_cap} of them)")
    axis.set_ylabel("Activity-years")
    axis.set_title("How close each activity came to its annual plan")
    axis.legend()
    figure.tight_layout()
    figure.savefig(FIGURES_DIR / "ratio_distribution.png", dpi=150)
    plt.close(figure)


def main():
    FIGURES_DIR.mkdir(exist_ok=True)
    connection = duckdb.connect(str(DB_PATH), read_only=True)
    planned_vs_disbursed_by_year(connection)
    ratio_distribution(connection)
    connection.close()
    print(f"wrote charts to {FIGURES_DIR}")


if __name__ == "__main__":
    main()
