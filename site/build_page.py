"""Stage 10: build site/index.html from outputs/results.json and outputs/model_results.json.

Every figure on the page is read from those files, so the page cannot drift from the
numbers. Run it after run_all.py. The page is one static file with its styles inside
(the design tokens are copied from Personal-Website/styles.css).
"""
import html
import json
import subprocess
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
SITE_DIR = Path(__file__).resolve().parent
RESULTS_PATH = PROJECT_DIR / "outputs" / "results.json"
MODEL_PATH = PROJECT_DIR / "outputs" / "model_results.json"
PAGE_PATH = SITE_DIR / "index.html"

HOME_URL = "https://alven-yuka.vercel.app"
REPO_URL = "https://github.com/alvenyuka/kenya-aid-flows"
IATI_BUDGET_URL = "https://iatistandard.org/en/iati-standard/203/activity-standard/iati-activities/iati-activity/budget/"

STYLE = """
:root{--bg:#ffffff;--bg-2:#f6f7f3;--card:#ffffff;--fg:#1d222b;--fg-2:#323944;--muted:#4a5361;
--border:rgba(29,34,43,.11);--border-strong:rgba(29,34,43,.20);--lime:#d9f23a;--lime-line:#9fbc00;
--lime-wash:#f6fbd9;--on-lime:#1d222b;--accent:#3d5a00;--orange:#c2410c;--ring:#3d5a00;
--card-shadow:0 1px 2px rgba(29,34,43,.04),0 8px 24px -14px rgba(29,34,43,.12);
--font:"Cabinet Grotesk",system-ui,-apple-system,"Segoe UI",sans-serif;
--font-display:"Clash Display","Cabinet Grotesk",system-ui,sans-serif;
--font-mono:"JetBrains Mono",ui-monospace,"Cascadia Code",Consolas,monospace;color-scheme:light}
*,*::before,*::after{box-sizing:border-box}
html{-webkit-text-size-adjust:100%;scroll-behavior:smooth;scroll-padding-top:4.5rem}
@media (prefers-reduced-motion:reduce){html{scroll-behavior:auto}}
body{margin:0;background:var(--bg);color:var(--fg);font-family:var(--font);font-size:1.0625rem;line-height:1.6;font-weight:500;-webkit-font-smoothing:antialiased;overflow-x:hidden}
a{color:inherit;text-decoration-color:var(--border-strong);text-underline-offset:.16em}
a:hover{text-decoration-color:currentColor}
:focus-visible{outline:2px solid var(--ring);outline-offset:3px;border-radius:4px}
::selection{background:var(--lime);color:var(--on-lime)}
h1,h2,h3{margin:0;font-weight:500;line-height:1.15;text-wrap:balance}
p{margin:0}ul{margin:0;padding:0;list-style:none}
strong{font-weight:700}
.display{font-family:var(--font-display);font-weight:500;letter-spacing:-.02em}
.mono{font-family:var(--font-mono);font-weight:400}
.wrap{width:min(1180px,100% - 2rem);margin-inline:auto}
.skip{position:absolute;left:1rem;top:-3rem;padding:.5rem .75rem;background:var(--lime);color:var(--on-lime);border-radius:.5rem;z-index:50}
.skip:focus{top:1rem}
.top{position:sticky;top:0;z-index:40;background:rgba(255,255,255,.92);backdrop-filter:blur(14px);-webkit-backdrop-filter:blur(14px);border-bottom:1px solid var(--border)}
.top-row{display:flex;align-items:center;gap:1.5rem;height:4rem}
.brand{display:inline-flex;align-items:center;gap:.4rem;font-family:var(--font-display);font-weight:600;font-size:1.125rem;text-decoration:none}
.brand .dot{width:.4rem;height:.4rem;border-radius:50%;background:var(--lime-line)}
.nav{display:flex;gap:1.5rem;margin-inline:auto;font-size:.975rem;color:var(--fg-2)}
.nav a{text-decoration:none}.nav a:hover{color:var(--accent)}
.btn{display:inline-flex;align-items:center;justify-content:center;padding:.8rem 1.4rem;border-radius:999px;font-weight:600;font-size:1rem;text-decoration:none;border:1px solid transparent}
.btn-sm{padding:.5rem 1.05rem;font-size:.925rem}
.btn-lime{background:var(--lime);color:var(--on-lime);border-color:var(--lime-line)}.btn-lime:hover{background:#cbe62a}
.btn-outline{border-color:var(--border-strong);color:var(--fg);background:var(--card)}.btn-outline:hover{border-color:var(--fg)}
.nav-cta{margin-left:auto;border-color:var(--orange);color:var(--orange)}.nav-cta:hover{background:rgba(194,65,12,.08);border-color:var(--orange);color:var(--orange)}
.pill{display:inline-flex;align-items:center;gap:.55rem;padding:.4rem .9rem;border-radius:999px;border:1px solid var(--border-strong);background:var(--card);font-family:var(--font-mono);font-size:.8125rem;color:var(--fg-2);max-width:100%}
.hero{border-bottom:1px solid var(--border)}
.hero-inner{padding-block:clamp(3rem,7vw,5rem) clamp(2.5rem,5vw,4rem)}
.hero .pill{margin-bottom:1.5rem}
.hero h1{font-size:clamp(2.25rem,1.6rem + 2.4vw,3rem);line-height:1.05;letter-spacing:-.03em;max-width:22ch}
.lede{margin-top:1.25rem;color:var(--fg-2);font-size:clamp(1.0625rem,.95rem + .4vw,1.25rem);line-height:1.55;max-width:62ch}
.actions{display:flex;flex-wrap:wrap;gap:.75rem;margin-top:1.75rem}
.facts{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:1.25rem;margin-top:2.25rem;padding-top:1.5rem;border-top:1px solid var(--border)}
.facts li{display:grid;gap:.35rem;align-content:start}
.stat-num{font-size:2.1rem;line-height:1;letter-spacing:-.02em;justify-self:start;background:linear-gradient(transparent 58%,var(--lime) 58%,var(--lime) 92%,transparent 92%);padding-inline:.06em}
.stat-label{font-size:.9rem;color:var(--muted);line-height:1.35}
.section{padding-block:clamp(3rem,6vw,5rem)}
.section:nth-of-type(even){background:var(--bg-2)}
.section+.section{border-top:1px solid var(--border)}
.section-head{display:grid;grid-template-columns:minmax(0,1.1fr) minmax(0,1fr);gap:1.25rem 3rem;align-items:end;margin-bottom:clamp(1.5rem,3vw,2.5rem)}
.section-head .pill{margin-bottom:1rem}
.section-head h2{font-size:clamp(1.7rem,1.2rem + 2vw,2.6rem);letter-spacing:-.02em;line-height:1.05}
.section-head>p{color:var(--muted);max-width:56ch}
.card{background:var(--card);border:1px solid var(--border);border-radius:1rem;padding:clamp(1.1rem,3vw,1.75rem);box-shadow:var(--card-shadow)}
.callout{background:var(--lime-wash);border:1px solid var(--lime-line);border-radius:1rem;padding:clamp(1.1rem,3vw,1.5rem);margin-top:1.25rem}
.grid2{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:1.25rem}
.prose p+p{margin-top:.9rem}
.prose{color:var(--fg-2);max-width:70ch}
.table-wrap{overflow-x:auto;-webkit-overflow-scrolling:touch}
table{border-collapse:collapse;width:100%;font-size:.95rem;min-width:30rem}
th,td{padding:.55rem .7rem;text-align:right;border-bottom:1px solid var(--border);white-space:nowrap}
th:first-child,td:first-child{text-align:left;white-space:normal}
th{font-family:var(--font-mono);font-weight:400;font-size:.8rem;color:var(--muted)}
caption{text-align:left;font-family:var(--font-mono);font-size:.8rem;color:var(--muted);padding-bottom:.6rem}
.bars{display:grid;gap:.45rem}
.bar-row{display:grid;grid-template-columns:3rem minmax(0,1fr) 5.5rem;gap:.6rem;align-items:center;font-size:.9rem}
.bar-year{font-family:var(--font-mono);font-size:.8rem;color:var(--muted)}
.bar-pair{display:grid;gap:.2rem}
.bar{height:.55rem;border-radius:3px;min-width:2px}
.bar-planned{background:#1f4e79}.bar-disbursed{background:var(--lime-line)}
.bar-value{font-family:var(--font-mono);font-size:.78rem;color:var(--fg-2);text-align:right}
.legend{display:flex;flex-wrap:wrap;gap:1rem;margin-bottom:1rem;font-size:.85rem;color:var(--muted)}
.key{display:inline-block;width:.8rem;height:.55rem;border-radius:3px;margin-right:.4rem}
.limits li{padding:.55rem 0;border-bottom:1px solid var(--border);color:var(--fg-2)}
.foot{padding-block:2rem;font-size:.8rem;color:var(--muted);display:grid;gap:.4rem;border-top:1px solid var(--border)}
@media (max-width:860px){.section-head{grid-template-columns:minmax(0,1fr)}.facts{grid-template-columns:repeat(2,minmax(0,1fr))}.grid2{grid-template-columns:minmax(0,1fr)}.nav{display:none}}
@media (max-width:480px){.bar-row{grid-template-columns:2.6rem minmax(0,1fr) 4.6rem}.top-row{gap:.75rem}}
"""


def pct(value, digits=0):
    return f"{value * 100:.{digits}f}%"


def whole(value):
    return f"{int(round(value)):,}"


def billions(value):
    return f"${value / 1e9:,.2f} billion"


def millions_number(value):
    return f"{value / 1e6:,.0f}"


def esc(text):
    return html.escape(str(text))


def table(caption, headers, rows):
    """A plain HTML table. rows is a list of lists of already-formatted strings."""
    head_cells = ""
    for header in headers:
        head_cells = head_cells + f"<th scope=\"col\">{esc(header)}</th>"
    body = ""
    for row in rows:
        cells = ""
        for cell in row:
            cells = cells + f"<td>{esc(cell)}</td>"
        body = body + f"<tr>{cells}</tr>\n"
    return (
        f"<div class=\"table-wrap\"><table><caption>{esc(caption)}</caption>"
        f"<thead><tr>{head_cells}</tr></thead><tbody>\n{body}</tbody></table></div>"
    )


def section(section_id, label, heading, intro, body):
    return f"""
<section class="section" id="{section_id}">
<div class="wrap">
<div class="section-head"><div><span class="pill mono">{esc(label)}</span><h2 class="display">{esc(heading)}</h2></div><p>{intro}</p></div>
{body}
</div>
</section>"""


def year_bars(by_year):
    """One row per year: a planned bar and a disbursed bar, drawn with CSS widths."""
    biggest = 0
    for year_row in by_year:
        biggest = max(biggest, year_row["planned_usd"], year_row["disbursed_usd"])
    rows = ""
    for year_row in by_year:
        planned_width = year_row["planned_usd"] / biggest * 100
        disbursed_width = year_row["disbursed_usd"] / biggest * 100
        rows = rows + (
            f"<div class=\"bar-row\"><span class=\"bar-year\">{year_row['year']}</span>"
            f"<div class=\"bar-pair\">"
            f"<div class=\"bar bar-planned\" style=\"width:{planned_width:.1f}%\" title=\"planned\"></div>"
            f"<div class=\"bar bar-disbursed\" style=\"width:{disbursed_width:.1f}%\" title=\"disbursed\"></div></div>"
            f"<span class=\"bar-value\">{pct(year_row["arrived_share"])}</span></div>\n"
        )
    legend = (
        "<div class=\"legend\"><span><span class=\"key bar-planned\"></span>Planned (original annual budget)</span>"
        "<span><span class=\"key bar-disbursed\"></span>Disbursed</span><span>Figure at right: share that arrived</span></div>"
    )
    return legend + f"<div class=\"bars\" role=\"img\" aria-label=\"Planned and disbursed aid by year, with the share that arrived\">{rows}</div>"


def model_sentence(model):
    """A plain sentence on whether the model beat the rule, chosen from the numbers."""
    model_auc = model["model"]["pr_auc"]
    rule_auc = model["baseline"]["pr_auc"]
    matched = model["model"]["same_number_of_flags_as_baseline"]
    rule = model["baseline"]["flags"]
    if matched["precision"] > rule["precision"] and matched["recall"] > rule["recall"]:
        verdict = "The model beats the rule of thumb on both precision and recall at the same number of flags."
    elif model_auc > rule_auc:
        verdict = (
            "The model ranks the activity-years a little better than the rule (a higher PR-AUC), "
            "but at the same number of flags it is not more precise and does not catch more, so it does not beat the rule on the flags themselves."
        )
    else:
        verdict = "The model does not beat the rule of thumb."
    return verdict


def git_commit():
    """Short hash of the repository's latest commit, or None if there is no commit yet."""
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"], cwd=PROJECT_DIR, capture_output=True, text=True
        )
    except OSError:
        return None
    if completed.returncode != 0:
        return None
    return completed.stdout.strip()


def build_page():
    results = json.loads(RESULTS_PATH.read_text())
    model = json.loads(MODEL_PATH.read_text())

    h = results["headline"]
    fetch = results["fetch"]
    fetch_date = fetch["fetch_date"]
    window = results["year_window"]
    ay = results["activity_years"]
    inc = results["sensitivity_needs_based_publisher_included"]
    un = results["needs_based_publisher_rows"][0]
    em = results["emergency_response_sector"]
    zero = results["sensitivity_zero_disbursed_lower_bound"]
    expenditure = results["sensitivity_expenditure_counted"]
    typed = results["sensitivity_typed_lines_only"]
    cover = {}
    for row in results["sensitivity_coverage"]:
        cover[row["coverage_class"]] = row
    baseline = results["baseline"]["headline"]
    zero_fill = results["baseline"]["zero_fill"]
    min_years = results["ranking_rule"]["min_comparable_activity_years"]
    # Settings read from the outputs, not typed here.
    threshold = model["threshold"]
    test_first_year = model["test_first_year"]
    cutoff = model["decision_cutoff"]
    checks_run = results["checks_run"]
    next_year_check = results["next_year_against_last_year"]
    peak_budget_year = results["original_budget_by_year"][0]["year"]
    peak_budget = 0
    for budget_row in results["original_budget_by_year"]:
        if budget_row["planned_usd"] > peak_budget:
            peak_budget = budget_row["planned_usd"]
            peak_budget_year = budget_row["year"]
    thresholds = results["publisher_rule_thresholds"]

    publishers = {}
    for row in results["publishers_left_out"]:
        publishers[row["reporting_ref"]] = row
    gates = publishers["DAC-1601"]
    cgiar = publishers["XM-DAC-47015"]

    # Hero
    facts = [
        (pct(h["arrived_share"]), "of scheduled aid arrived in its own year"),
        (f"{h['ratio']:.2f}", "disbursed divided by planned"),
        (pct(h["share_under_70"], 1), f"of activity-years got under {pct(threshold)} of plan"),
        (whole(h["activity_years"]), f"activity-years compared, from {whole(h['activities'])} activities"),
    ]
    fact_items = ""
    for number, label in facts:
        fact_items = fact_items + f"<li><span class=\"stat-num display\">{esc(number)}</span><span class=\"stat-label\">{esc(label)}</span></li>"

    hero = f"""
<header class="hero" id="top"><div class="wrap hero-inner">
<span class="pill mono">IATI data via d-portal.org, retrieved {esc(fetch_date)}</span>
<h1 class="display">How much of the aid scheduled for Kenya arrives in its year?</h1>
<p class="lede">For {whole(h['activity_years'])} activity-years with a full-year annual budget, {pct(h['arrived_share'])} of the {billions(h['planned_usd'])} scheduled was disbursed in the year it was scheduled for, {window['first_year']} to {window['last_year']}. A data pipeline built step by step from open aid records: download, clean, SQL models, checks, a simple rule and a model.</p>
<div class="actions"><a class="btn btn-lime" href="#results">See the results</a><a class="btn btn-outline" href="{REPO_URL}">Repository</a></div>
<ul class="facts">{fact_items}</ul>
</div></header>"""

    # Results
    results_body = f"""
<div class="grid2">
<div class="card prose"><h3 class="display">The headline</h3>
<p><strong>{pct(h['arrived_share'])}</strong> of the scheduled money arrived in its own year: {billions(h['arrived_usd'])} of {billions(h['planned_usd'])}. Any amount above plan is not counted, so one project that over-spent cannot hide another that fell short. A variant that also penalises overshoot gives {pct(h['arrived_share_overshoot_penalised'])}.</p>
<p>Total disbursements were {billions(h['disbursed_usd'])}, a ratio of {h['ratio']:.2f} to plan. The middle activity-year sent {h['median_ratio']:.2f} of its plan, {pct(h['share_shortfall'], 1)} fell short (under 99%), {pct(h['share_overshoot'], 1)} went over (above 101%) and {pct(h['share_on_plan'], 1)} were within 1% of plan.</p></div>
<div class="card prose"><h3 class="display">What the measure is</h3>
<p>A variant inspired by the Paris Declaration and <a href="https://www.effectivecooperation.org/system/files/2021-02/Global%20Partnership%20Monitoring_Indicator%20Framework.pdf">GPEDC indicator 5a</a> (annual predictability: aid disbursed within the year it was scheduled). It uses calendar years, not Kenya's July to June fiscal year, works at activity level, includes NGO publishers, and does not penalise overshoot in the main figure.</p>
<p>An activity-year is one project in one calendar year. It is compared only if the donor's original annual budget lines cover the whole year, the plan is above zero and at least one disbursement is reported.</p></div>
</div>
<div class="callout prose"><p><strong>UNHCR is set aside, and it matters.</strong> The UN refugee agency publishes needs-based budgets and reports most of its spending as expenditure, not disbursement. Its {whole(un['activity_years'])} activity-years carry {billions(un['planned_usd'])} of planned money, and only {pct(un['arrived_share'])} of it arrived as disbursement. With UNHCR left in, {pct(inc['arrived_share'])} arrives and the ratio is {inc['ratio']:.2f}. The rule that sets it aside was written after looking at UNHCR's numbers.</p></div>"""

    # By year
    year_rows = []
    with_unhcr = {}
    for row in results["by_year_with_needs_based_publisher"]:
        with_unhcr[row["year"]] = row
    for row in results["by_year"]:
        year_rows.append([
            str(row["year"]), whole(row["comparable_activity_years"]), millions_number(row["planned_usd"]),
            millions_number(row["disbursed_usd"]), pct(row["arrived_share"]), pct(with_unhcr[row["year"]]["arrived_share"]),
            f"{row['ratio']:.2f}", f"{row['median_ratio']:.2f}", pct(row["share_under_70"], 1),
        ])
    by_year_body = (
        "<div class=\"card\">" + year_bars(results["by_year"]) + "</div>"
        "<div class=\"card\" style=\"margin-top:1.25rem\">"
        + table(
            "Planned against disbursed, US dollars in millions",
            ["Year", "Activity-years", "Planned", "Disbursed", "Arrived", "Arrived with UNHCR", "Ratio", "Median ratio", f"Under {pct(threshold)}"],
            year_rows,
        ) + "</div>"
    )

    # Who falls short
    donor_rows = []
    for row in results["lowest_arrived_share_donors"]:
        donor_rows.append([row["donor_name"], whole(row["comparable_activity_years"]), millions_number(row["planned_usd"]), pct(row["arrived_share"]), f"{row['ratio']:.2f}"])
    sector_rows = []
    for row in results["lowest_arrived_share_sectors"]:
        sector_rows.append([row["sector_group_name"], whole(row["comparable_activity_years"]), millions_number(row["planned_usd"]), pct(row["arrived_share"]), f"{row['ratio']:.2f}"])
    who_body = (
        "<div class=\"card\">" + table("Reporting organisations, lowest share arrived first (planned in US dollars, millions)",
                                      ["Reporting organisation", "Activity-years", "Planned", "Arrived", "Ratio"], donor_rows) + "</div>"
        "<div class=\"card\" style=\"margin-top:1.25rem\">" + table("Sector groups, lowest share arrived first (planned in US dollars, millions)",
                                      ["Sector group", "Activity-years", "Planned", "Arrived", "Ratio"], sector_rows) + "</div>"
        f"<p class=\"prose\" style=\"margin-top:1rem\">Only groups with at least {min_years} comparable activity-years are ranked. NGOs and agencies report too, so the first column is a reporting organisation. Several rows rest on little money, so read the planned column first. The Emergency response sector is {pct(em['arrived_share_without_needs_based'])} arrived on {whole(em['activity_years_without_needs_based'])} activity-years, and {pct(em['arrived_share_with_needs_based'])} with UNHCR left in.</p>"
    )

    # Sensitivities
    sensitivity_rows = [
        ["Headline", whole(h["activity_years"]), pct(h["arrived_share"]), f"{h['ratio']:.2f}"],
        ["UNHCR put back", whole(inc["activity_years"]), pct(inc["arrived_share"]), f"{inc['ratio']:.2f}"],
        ["Expenditure counted as arrived too (upper bound)", whole(expenditure["activity_years"]), pct(expenditure["arrived_share"]), f"{expenditure['ratio']:.2f}"],
        ["Budget lines with a stated type only", whole(typed["activity_years"]), pct(typed["arrived_share"]), f"{typed['ratio']:.2f}"],
        ["Part-year annual plans", whole(cover["part_year"]["activity_years"]), pct(cover["part_year"]["arrived_share"]), f"{cover['part_year']['ratio']:.2f}"],
        ["Multi-year budgets split evenly", whole(cover["multi_year_split"]["activity_years"]), pct(cover["multi_year_split"]["arrived_share"]), f"{cover['multi_year_split']['ratio']:.2f}"],
        ["Missing disbursement counted as zero (lower bound)", whole(zero["activity_years"]), pct(zero["arrived_share"]), f"{zero['ratio']:.2f}"],
    ]
    sensitivity_body = (
        "<div class=\"card\">" + table("The answer under other choices", ["Version", "Activity-years", "Arrived", "Ratio"], sensitivity_rows) + "</div>"
        f"<div class=\"card prose\" style=\"margin-top:1.25rem\"><p>Budget lines with no stated type count as original in the main figure, because the IATI standard says &ldquo;If the @type attribute is omitted, then BudgetType code 1 (Original) is assumed&rdquo; (<a href=\"{IATI_BUDGET_URL}\">IATI standard, budget element</a>). The stated-type version drops them.</p>"
        f"<p>The zero-counted version is a lower bound: a zero disbursement can mean the publisher reports spending as expenditure (code E). Multi-year budgets are not a plan for any one year, so their ratio says little.</p></div>"
    )

    # Rule and model
    matched = model["model"]["same_number_of_flags_as_baseline"]
    at_cutoff = model["model"]["at_cutoff"]
    rule_flags = model["baseline"]["flags"]
    model_rows = [
        [f"Rule of thumb: earlier years under {pct(threshold)} of plan", whole(rule_flags["flagged"]), pct(rule_flags["precision"]), pct(rule_flags["recall"]), f"{model['baseline']['pr_auc']:.2f}"],
        ["Logistic regression, same number of flags", whole(matched["flagged"]), pct(matched["precision"]), pct(matched["recall"]), f"{model['model']['pr_auc']:.2f}"],
        [f"Logistic regression, probability above {cutoff}", whole(at_cutoff["flagged"]), pct(at_cutoff["precision"]), pct(at_cutoff["recall"]), f"{model['model']['pr_auc']:.2f}"],
    ]
    model_body = (
        "<div class=\"card\">" + table(
            f"Scored on {whole(model['test_rows'])} activity-years from {test_first_year} to {window['last_year']} ({pct(model['test_base_rate_under_70'])} of them under {pct(threshold)} of plan)",
            ["Method", "Flags", "Precision", "Recall", "PR-AUC"], model_rows) + "</div>"
        f"<div class=\"card prose\" style=\"margin-top:1.25rem\"><p>{esc(model_sentence(model))}</p>"
        f"<p>Both look only at earlier years. The model was trained on {whole(model['train_rows'])} activity-years before {test_first_year}, with the activity's earlier ratio, its number of earlier years, plan size, the publisher's earlier record and the sector. Nothing was tuned on the test years. The publisher's record keeps updating through the test years, using strictly earlier years only, like the activity's own earlier ratio: a {test_first_year + 2} row uses the outcomes of {test_first_year} and {test_first_year + 1}. Precision is the share of flags that were right, recall is the share of true cases caught, and PR-AUC summarises how well the scores rank true cases above others. Accuracy is not shown, because flagging nothing would score well on it.</p>"
        f"<p>The rule of thumb on its own flags {pct(baseline['precision'])} correctly against a {pct(baseline['base_rate_under_70'])} base rate. A second version that counts a missing disbursement as zero reaches {pct(zero_fill['precision'])} precision, but {whole(zero_fill['true_positives_in_years_without_disbursement'])} of its {whole(zero_fill['true_positives'])} correct flags are years with no disbursement row, so it partly detects activities that stop reporting.</p></div>"
    )

    # Method
    method_body = f"""
<div class="card prose">
<p><strong>1. Download.</strong> {whole(fetch['tables']['act']['rows_fetched'])} activities, {whole(fetch['tables']['trans']['rows_fetched'])} transactions and {whole(fetch['tables']['budget']['rows_fetched'])} budget lines for Kenya from the d-portal query API, each table checked against the API's own row count.</p>
<p><strong>2. Clean.</strong> One small rule per function, each logging the rows and dollars it removes: incoming-fund rows that would count money twice, non-aid flow types (private investment such as IFC), impossible dates, exact duplicates, negative corrections and budget rows that are planned disbursements.</p>
<p><strong>3. Load and model in SQL.</strong> The cleaned tables go into DuckDB. Plain numbered SQL files cut each budget line into calendar-year pieces by days, test whether annual lines cover the whole year, and build the activity-year table of planned, disbursed and committed money.</p>
<p><strong>4. Set aside three publishers whose budgets cannot be compared with their spending.</strong> The Gates Foundation's budgets repeat its disbursements ({whole(gates['activity_years_with_plan_and_disbursement'])} activity-years within 1% of plan). CGIAR's budgets cover only a slice of its spending (median ratio {cgiar['median_ratio']:.2f}). UNHCR's are needs-based. The thresholds ({thresholds['min_activity_years']} or more activity-years for the first two; for UNHCR at least {thresholds['needs_based_min_years']} years, under {pct(thresholds['needs_based_every_year_ratio_below'])} disbursed in every year, mostly untyped budget lines, and more expenditure than disbursement) were chosen after looking at the data.</p>
<p><strong>5. Check.</strong> {checks_run} SQL queries that must return no rows, including that cutting budgets into years keeps every dollar and that every compared year is covered day by day. The script fails if any check returns a row.</p>
<p><strong>6. Rule and model.</strong> A rule of thumb first, then a logistic regression judged against it on the same rows.</p>
</div>"""

    # Limits
    late_reporting_limit = (
        f"Years end in {window['last_year']}: disbursements dated {next_year_check['next_year']} are "
        f"{pct(next_year_check['fall_share'])} below {next_year_check['last_year']}"
    )
    if peak_budget_year == next_year_check["next_year"]:
        late_reporting_limit = late_reporting_limit + f" while {peak_budget_year} budgets are the largest of any year"
    late_reporting_limit = late_reporting_limit + ", which looks like late reporting."
    limits = [
        f"Only {whole(h['activity_years'])} of {whole(ay['all_activity_years'])} activity-years can be compared, and publishers that give full-year budgets are not a random sample of aid to Kenya.",
        "The comparison is against the original budget. Budgets are often revised, so a project can look short when its plan changed.",
        "Removing incoming funds does not remove every double count: if a donor and its implementer both report one disbursement, both stay.",
        "Negative disbursements and commitments are dropped, not netted, which raises totals slightly.",
        "A zero disbursement can be a reporting habit, because some publishers report spending only as expenditure.",
        "The publisher thresholds were chosen after seeing the data, and other unusual publishers may remain.",
        "The yearly totals have not been compared with published Kenya aid figures. Sector names come from a list typed from the OECD DAC codes.",
        f"The rule and model are scored on {whole(model['test_rows'])} activity-years, so small differences between them are within noise.",
        late_reporting_limit,
    ]
    limit_items = ""
    for limit in limits:
        limit_items = limit_items + f"<li>{esc(limit)}</li>"
    limits_body = f"<div class=\"card\"><ul class=\"limits\">{limit_items}</ul></div>"

    headline_figures = {}
    for key in ["activity_years", "planned_usd", "disbursed_usd", "arrived_share", "ratio", "median_ratio", "share_under_70"]:
        headline_figures[key] = h[key]
    page_data = {
        "snapshot_date": results["snapshot_date"],
        "headline": headline_figures,
        "with_unhcr": {"arrived_share": inc["arrived_share"], "ratio": inc["ratio"]},
        "model": {"pr_auc": model["model"]["pr_auc"], "baseline_pr_auc": model["baseline"]["pr_auc"]},
    }

    body = (
        hero
        + section("results", "Results", "What arrived, and what did not", "Share of scheduled money that arrived in its own year, on full-year annual budgets.", results_body)
        + section("by-year", "By year", "Planned against disbursed, year by year", "Bars are scaled to the biggest value in any year. The Arrived with UNHCR column shows where the needs-based publisher pulls a year down.", by_year_body)
        + section("who", "Who falls short", "Donors and sectors with the lowest share arrived", f"Ranked by share arrived, not by dollars short, which measures timing more than reliability.", who_body)
        + section("sensitivities", "Sensitivities", "How the answer changes with the choices", "Each row is one decision made differently. The headline is the first row.", sensitivity_body)
        + section("model", "Rule and model", "Can a model beat a simple rule?", f"Flag activity-years likely to arrive under {pct(threshold)} of plan, using only earlier years.", model_body)
        + section("method", "Method", "How it is built, in plain words", "One folder per stage, small scripts, plain SQL files.", method_body)
        + section("limits", "Limits", "What this result does not show", "Read these before quoting a number.", limits_body)
    )

    commit = git_commit()
    commit_text = ""
    if commit is not None:
        commit_text = f" Commit {esc(commit)}."

    footer = f"""
<footer class="foot wrap mono"><span>Alven Yuka &middot; <a href="{HOME_URL}">alven-yuka.vercel.app</a> &middot; <a href="{REPO_URL}">{REPO_URL}</a></span>
<span>Figures read from outputs/results.json and outputs/model_results.json, snapshot of {esc(fetch_date)}, built by site/build_page.py.{commit_text}</span>
<span>IATI publishers via d-portal.org, retrieved {esc(fetch_date)}. Each publisher sets its own licence in the IATI Registry; the raw data is not redistributed here.</span></footer>
<script id="data" type="application/json">{json.dumps(page_data, separators=(',', ':'))}</script>"""

    description = (
        f"{pct(h['arrived_share'])} of scheduled aid to Kenya arrived in its own year across {whole(h['activity_years'])} "
        f"full-year activity-years, {window['first_year']} to {window['last_year']}. A data pipeline built from open IATI data."
    )

    page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Kenya Aid Flows | Alven Yuka</title>
<meta name="description" content="{esc(description)}">
<meta name="theme-color" content="#ffffff">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Crect width='64' height='64' rx='14' fill='%23ffffff'/%3E%3Ccircle cx='32' cy='32' r='12' fill='%23d9f23a'/%3E%3C/svg%3E">
<link rel="preconnect" href="https://api.fontshare.com" crossorigin>
<link rel="stylesheet" href="https://api.fontshare.com/v2/css?f[]=clash-display@500,600&f[]=cabinet-grotesk@400,500,700&display=swap">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500&display=swap">
<style>{STYLE}</style>
</head>
<body>
<a class="skip" href="#results">Skip to results</a>
<div class="top"><div class="wrap top-row">
<a class="brand" href="{HOME_URL}"><span class="dot"></span>Alven Yuka</a>
<nav class="nav" aria-label="Sections"><a href="#results">Results</a><a href="#by-year">By year</a><a href="#who">Who</a><a href="#sensitivities">Sensitivities</a><a href="#model">Model</a><a href="#method">Method</a><a href="#limits">Limits</a></nav>
<a class="btn btn-sm btn-outline nav-cta" href="{REPO_URL}">Repository</a>
</div></div>
<main>{body}
</main>
{footer}
</body>
</html>
"""
    PAGE_PATH.write_text(page, encoding="utf-8")
    return page


def main():
    page = build_page()
    print(f"wrote {PAGE_PATH} ({len(page):,} characters)")


if __name__ == "__main__":
    main()
