# RAGAS Email Evaluation Report

- Cases attempted: 30
- Evaluations completed: 30
- Evaluation failures: 0

## Quality scores

| Metric | Mean score | Pass rate (>=4) | Reviewed |
|---|---:|---:|---:|
| Subject | 4.73/5 | 90.0% | 30 |
| Tone | 4.93/5 | 100.0% | 30 |
| Factual | 4.70/5 | 93.3% | 30 |
| Completion | 4.97/5 | 100.0% | 30 |

## Methodology

- Evaluator: RAGAS DiscreteMetric
- Scores: LLM-as-a-Judge, 1 to 5
- Pass definition: score >= 4
- Source: existing generated email outputs
- No RAG retrieval metrics were used
- Human agreement has not been measured yet

## Limitations

Scores are model judgments, not ground-truth accuracy.
Review evaluator disagreements against human ratings.
A small evaluation dataset limits generalizability.
