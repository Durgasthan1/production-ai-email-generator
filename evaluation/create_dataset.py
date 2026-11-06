
import csv
from pathlib import Path

OUTPUT = Path(__file__).parent / "email_test_cases.csv"

# Ten business scenarios x three tones = 30 test cases.
# All scenarios use fictional or generic information.
scenarios = [
    ("Request two days of leave", "Manager"),
    ("Follow up on a job interview", "HR"),
    ("Request an update on a project proposal", "Client"),
    ("Thank someone for helping with a project", "Colleague"),
    ("Request a meeting to discuss project progress", "Manager"),
    ("Apologize for a delayed response", "Client"),
    ("Ask for clarification about project requirements", "Client"),
    ("Request permission to work from home tomorrow", "Manager"),
    ("Inform a colleague about a project milestone", "Colleague"),
    ("Politely decline a meeting invitation", "Manager"),
]

tones = ["Formal", "Professional", "Friendly"]

with OUTPUT.open("w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(
        f,
        fieldnames=[
            "test_id",
            "purpose",
            "tone",
            "recipient"
        ]
    )
    writer.writeheader()

    test_number = 1

    for purpose, recipient in scenarios:
        for tone in tones:
            writer.writerow({
                "test_id": f"TC{test_number:03d}",
                "purpose": purpose,
                "tone": tone,
                "recipient": recipient
            })
            test_number += 1

print(f"Created {test_number - 1} cases at {OUTPUT}")
