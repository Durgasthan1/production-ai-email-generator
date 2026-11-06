
# AI Email Generator

A production-style Generative AI email-writing application
using FastAPI, Streamlit, and a managed open-weight LLM.

## Architecture

Streamlit → FastAPI → Groq Managed LLM → JSON Response

## Features

- Professional email generation
- Formal, professional, and friendly tones
- Pydantic input/output validation
- API-key authentication
- Single-process sliding-window rate limiting
- Structured logging and request IDs
- LLM latency and token usage metrics
- Automated Pytest suite

## Technology Stack

Python 3.13, Streamlit, FastAPI, Pydantic,
Groq SDK, HTTPX, Pytest, GitHub Actions

## Local Setup

1. Clone the repository.
2. Create a Python virtual environment.
3. Install requirements:

   pip install -r requirements.txt

4. Copy .env.example to .env.
5. Configure your Groq API key and application API key.
6. Start FastAPI:

   python -m uvicorn main:app --reload

7. In another terminal, start Streamlit:

   python -m streamlit run frontend.py

## API

POST /api/v1/emails/generate

Requires X-API-Key authentication.

## Tests

python -m pytest -v

## Security

Secrets are stored in environment variables and excluded
from Git. The API validates requests and applies rate limits.

## Limitations

- Shared application API key rather than user authentication
- In-memory rate limiting is not distributed
- No production deployment or uptime guarantees yet
- Observability currently uses application logs

## License

Choose and add a license before public release.
