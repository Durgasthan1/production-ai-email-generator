
import argparse
import asyncio
import csv
import json
import os
from pathlib import Path

from dotenv import load_dotenv
from openai import AsyncOpenAI

from ragas.llms import llm_factory
from ragas.metrics import DiscreteMetric


load_dotenv()

BASE = Path(__file__).parent
INPUT_FILE = BASE / "evaluation_results.csv"
OUTPUT_FILE = BASE / "ragas_results.csv"

MODEL = os.getenv(
    "RAGAS_JUDGE_MODEL",
    "openai/gpt-oss-20b"
)

METRIC_RULES = {
    "subject": """
Evaluate whether the subject accurately describes
the user's requested email purpose.

5 = precise and clear
4 = relevant with minor wording issues
3 = relevant but vague
2 = misleading or mostly irrelevant
1 = completely incorrect
""",
    "tone": """
Evaluate whether the generated email follows
the requested tone.

5 = fully matches tone
4 = mostly appropriate
3 = mixed or inconsistent
2 = mostly incorrect tone
1 = completely wrong tone
""",
    "factual": """
Evaluate whether the email introduces unsupported
facts, dates, names, amounts, or commitments.

A placeholder such as [Date] is acceptable.
An invented specific date is not acceptable.

5 = no unsupported claims
4 = very minor unsupported implications
3 = noticeable unsupported assumptions
2 = material unsupported facts
1 = serious fabrication
""",
    "completion": """
Evaluate whether the email fulfills the purpose
requested by the user, with an appropriate greeting,
message, and closing.

5 = fully completes the task
4 = completes with minor omissions
3 = partially completes
2 = major requirements missing
1 = does not complete the task
"""
}

OUTPUT_FIELDS = [
    "test_id", "judge_model",
    "subject_score", "subject_reason",
    "tone_score", "tone_reason",
    "factual_score", "factual_reason",
    "completion_score", "completion_reason",
    "evaluation_status", "error"
]


def create_metrics():
    metrics = {}

    for name, rules in METRIC_RULES.items():
        metrics[name] = DiscreteMetric(
            name=f"email_{name}",
            allowed_values=["1", "2", "3", "4", "5"],
            prompt=f"""
You are evaluating an AI-generated business email.

Use the following scoring rubric:
{rules}

Assess the output against the user instructions.
Do not reward fluent writing if it violates
the user's requirements.

The evaluation input is:
{{response}}

Select exactly one allowed score:
1, 2, 3, 4, or 5.

Give a concise reason grounded in the input.
"""
        )

    return metrics


def create_judge():
    api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        raise RuntimeError(
            "GROQ_API_KEY is missing from .env"
        )

    client = AsyncOpenAI(
        api_key=api_key,
        base_url="https://api.groq.com/openai/v1",
        timeout=45.0,
        max_retries=1
    )

    judge_llm = llm_factory(
        MODEL,
        provider="openai",
        client=client
    )

    return client, judge_llm


async def evaluate_email(row, metrics, judge, pause):
    output = {
        "test_id": row["test_id"],
        "judge_model": MODEL
    }

    evaluation_input = json.dumps(
        {
            "user_instructions": {
                "purpose": row["purpose"],
                "tone": row["tone"],
                "recipient": row["recipient"]
            },
            "generated_email": {
                "subject": row["subject"],
                "body": row["body"]
            }
        },
        ensure_ascii=False
    )

    for name, metric in metrics.items():
        try:
            result = await metric.ascore(
                llm=judge,
                response=evaluation_input
            )

            score = int(result.value)

            if not 1 <= score <= 5:
                raise ValueError("Score outside 1-5 range")

            output[f"{name}_score"] = score
            output[f"{name}_reason"] = (
                result.reason or ""
            )

        except Exception as exc:
            output[f"{name}_score"] = ""
            output[f"{name}_reason"] = ""
            output["error"] = (
                f"{name}: {type(exc).__name__}"
            )
            output["evaluation_status"] = "failed"
            return output

        # Avoid sending evaluator requests in a burst
        if pause > 0:
            await asyncio.sleep(pause)

    output["evaluation_status"] = "success"
    output["error"] = ""

    return output


async def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--limit", type=int, default=2)
    parser.add_argument("--pause", type=float, default=3)

    args = parser.parse_args()

    with INPUT_FILE.open(
        encoding="utf-8",
        newline=""
    ) as f:
        all_rows = list(csv.DictReader(f))

    # Avoid treating failed generation as a valid sample.
    valid_rows = [
        row for row in all_rows
        if row["http_status"] == "200"
        and row["schema_valid"].lower() == "true"
        and row["subject"].strip()
        and row["body"].strip()
    ]

    # Sort by test ID, so batches are reproducible
    valid_rows.sort(key=lambda r: r["test_id"])

    selected = valid_rows[
        args.start:args.start + args.limit
    ]

    previous = {}
    if OUTPUT_FILE.exists():
        with OUTPUT_FILE.open(
            encoding="utf-8", newline=""
        ) as f:
            for row in csv.DictReader(f):
                previous[row["test_id"]] = row

    client, judge = create_judge()
    metrics = create_metrics()

    try:
        for row in selected:
            test_id = row["test_id"]

            # Successful cases are checkpointed and skipped.
            if (
                test_id in previous
                and previous[test_id].get(
                    "evaluation_status"
                ) == "success"
            ):
                print(f"{test_id}: Already evaluated")
                continue

            result = await evaluate_email(
                row, metrics, judge, args.pause
            )

            previous[test_id] = result

            # Save after every case.
            # Preserve all results from earlier batches.
            with OUTPUT_FILE.open(
                "w", encoding="utf-8", newline=""
            ) as f:
                writer = csv.DictWriter(
                    f, fieldnames=OUTPUT_FIELDS
                )
                writer.writeheader()

                for saved in sorted(
                    previous.values(),
                    key=lambda r: r["test_id"]
                ):
                    writer.writerow(saved)

            print(
                f"{test_id}: "
                f"Subject={result.get('subject_score', '')}, "
                f"Tone={result.get('tone_score', '')}, "
                f"Factual={result.get('factual_score', '')}, "
                f"Completion={result.get('completion_score', '')}, "
                f"Status={result['evaluation_status']}"
            )

    finally:
        await client.close()

    print(f"RAGAS results saved to {OUTPUT_FILE}")


if __name__ == "__main__":
    asyncio.run(main())
