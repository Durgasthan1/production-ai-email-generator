
import argparse
import csv
import os
import time
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv()

BASE = Path(__file__).parent
DATASET = BASE / "email_test_cases.csv"
RESULTS = BASE / "evaluation_results.csv"

API_URL = os.getenv(
    "EMAIL_API_URL",
    "http://127.0.0.1:8000/api/v1/emails/generate"
)

API_KEY = os.getenv("APP_API_KEY")

FIELDS = [
    "test_id", "purpose", "tone", "recipient",
    "http_status", "schema_valid",
    "latency_ms", "request_id",
    "subject", "body", "error_type",
    "subject_score", "tone_score",
    "factual_score", "completion_score",
    "review_notes"
]


def evaluate_case(client, row):
    payload = {
        "purpose": row["purpose"],
        "tone": row["tone"],
        "recipient": row["recipient"]
    }

    result = dict.fromkeys(FIELDS, "")
    result.update(row)

    start = time.perf_counter()

    try:
        response = client.post(
            API_URL,
            json=payload,
            headers={"X-API-Key": API_KEY},
        )

        result["latency_ms"] = round(
            (time.perf_counter() - start) * 1000,
            2
        )
        result["http_status"] = response.status_code
        result["request_id"] = response.headers.get(
            "X-Request-ID", ""
        )

        if response.status_code != 200:
            result["schema_valid"] = False
            result["error_type"] = f"HTTP_{response.status_code}"
            return result

        data = response.json()

        valid = (
            isinstance(data, dict)
            and isinstance(data.get("subject"), str)
            and bool(data["subject"].strip())
            and isinstance(data.get("body"), str)
            and bool(data["body"].strip())
            and set(data.keys()) == {"subject", "body"}
        )

        result["schema_valid"] = valid

        if valid:
            result["subject"] = data["subject"]
            result["body"] = data["body"]
        else:
            result["error_type"] = "INVALID_SCHEMA"

    except (httpx.RequestError, ValueError) as exc:
        result["latency_ms"] = round(
            (time.perf_counter() - start) * 1000,
            2
        )
        result["schema_valid"] = False
        result["error_type"] = type(exc).__name__

    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--pause", type=float, default=15)
    args = parser.parse_args()

    if not API_KEY:
        raise RuntimeError("APP_API_KEY is not configured")

    with DATASET.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))

    selected = rows[args.start:args.start + args.limit]

    # Append without overwriting previously collected results.
    existing = set()
    if RESULTS.exists():
        with RESULTS.open(encoding="utf-8", newline="") as f:
            existing = {
                r["test_id"] for r in csv.DictReader(f)
            }

    new_file = not RESULTS.exists()

    with httpx.Client(
        timeout=httpx.Timeout(
            connect=20.0,
            read=150.0,
            write=20.0,
            pool=10.0
        )
    ) as client:

        with RESULTS.open("a", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDS)

            if new_file:
                writer.writeheader()

            pending = [
                row for row in selected
                if row["test_id"] not in existing
            ]

            for index, row in enumerate(pending):
                result = evaluate_case(client, row)
                writer.writerow(result)
                f.flush()

                print(
                    f'{row["test_id"]}: '
                    f'HTTP {result["http_status"] or "N/A"}, '
                    f'Schema={result["schema_valid"]}, '
                    f'Latency={result["latency_ms"]} ms'
                )

                if index < len(pending) - 1:
                    time.sleep(args.pause)

    print(f"Results saved to: {RESULTS}")


if __name__ == "__main__":
    main()
