
import csv
import math
import statistics
from pathlib import Path

BASE = Path(__file__).parent
DATASET = BASE / "email_test_cases.csv"
RESULTS = BASE / "evaluation_results.csv"
REPORT = BASE / "evaluation_report.md"


def percentile(values, p):
    values = sorted(values)
    if not values:
        return None

    position = (len(values) - 1) * p / 100
    lower = math.floor(position)
    upper = math.ceil(position)

    return (
        values[lower]
        + (values[upper] - values[lower])
        * (position - lower)
    )


with DATASET.open(encoding="utf-8", newline="") as f:
    total_cases = len(list(csv.DictReader(f)))

with RESULTS.open(encoding="utf-8", newline="") as f:
    rows = list(csv.DictReader(f))

# Keep one result per test case
ids = [r["test_id"] for r in rows]
if len(ids) != len(set(ids)):
    raise ValueError("Duplicate test IDs found in results")

successful = [
    r for r in rows
    if r["http_status"] == "200"
    and r["schema_valid"].lower() == "true"
]

latencies = [
    float(r["latency_ms"])
    for r in successful
    if r["latency_ms"]
]

metrics = [
    "subject_score",
    "tone_score",
    "factual_score",
    "completion_score"
]

lines = [
    "# AI Email Generator — Evaluation Report",
    "",
    f"- Planned cases: {total_cases}",
    f"- Evaluated cases: {len(rows)}",
    f"- Successful valid responses: {len(successful)}",
    (
        f"- Successful response rate: "
        f"{len(successful) / len(rows):.1%}"
        if rows else "- Successful response rate: N/A"
    ),
    ""
]

if latencies:
    lines.extend([
        "## End-to-end API latency",
        f"- Average: {statistics.mean(latencies):.2f} ms",
        f"- p50: {percentile(latencies, 50):.2f} ms",
        f"- p95: {percentile(latencies, 95):.2f} ms",
        ""
    ])

lines.append("## Human quality review")

for metric in metrics:
    scores = [
        int(r[metric])
        for r in successful
        if r[metric].strip().isdigit()
        and 1 <= int(r[metric]) <= 5
    ]

    if scores:
        passing = sum(s >= 4 for s in scores)

        lines.append(
            f"- {metric}: mean {statistics.mean(scores):.2f}/5; "
            f"pass rate {passing / len(scores):.1%}; "
            f"reviewed {len(scores)}/{len(successful)}"
        )
    else:
        lines.append(f"- {metric}: not yet reviewed")

lines.extend([
    "",
    "## Interpretation",
    "Metrics are descriptive for this fixed evaluation dataset.",
    "The p95 calculation uses linear interpolation.",
    "Quality scores represent human review, not an automated judge.",
    "Incomplete review coverage must be disclosed.",
    "These results do not establish overall production reliability."
])

REPORT.write_text(
    "\n".join(lines) + "\n",
    encoding="utf-8"
)

print(REPORT.read_text(encoding="utf-8"))
