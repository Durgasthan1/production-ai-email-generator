
import hmac
import os
import httpx
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

API_URL = os.getenv(
    "EMAIL_API_URL",
    "http://127.0.0.1:8000/api/v1/emails/generate"
)

st.set_page_config(
    page_title="AI Email Generator",
    page_icon="✉️",
    layout="centered"
)

def get_setting(name, default=None):
    # Cloud deployment secrets take precedence
    try:
        return st.secrets[name]
    except (KeyError, FileNotFoundError):
        return os.getenv(name, default)


APP_API_KEY = get_setting("APP_API_KEY")


def require_demo_access():
    expected_password = get_setting("DEMO_PASSWORD")

    if not expected_password:
        st.error("Demo access is not configured.")
        st.stop()

    if st.session_state.get("authenticated", False):
        return

    st.title("AI Email Generator")
    st.info("Enter the demonstration access password.")

    with st.form("demo_login"):
        password = st.text_input(
            "Demo Password",
            type="password"
        )
        submitted = st.form_submit_button("Access Demo")

    if submitted:
        if hmac.compare_digest(
            password,
            expected_password
        ):
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("Incorrect password.")

    st.stop()

require_demo_access()





st.title("AI Email Generator")
st.caption("Powered by FastAPI and an open-weight LLM")

with st.form("email_form"):
    purpose = st.text_area(
        "Email Purpose",
        placeholder="Request two days of leave",
        max_chars=1000
    )

    tone = st.selectbox(
        "Email Tone",
        ["Formal", "Professional", "Friendly"]
    )

    recipient = st.selectbox(
        "Recipient",
        ["Manager", "Client", "HR", "Colleague", "Student"]
    )

    submitted = st.form_submit_button(
        "Generate Email",
        type="primary"
    )

if submitted:
    if not purpose.strip():
        st.warning("Please enter the email purpose.")
    else:
        try:
            with st.spinner("Generating your email..."):
                response = httpx.post(
                    API_URL,
                    json={
                        "purpose": purpose,
                        "tone": tone,
                        "recipient": recipient
                    },
                    headers={"X-API-Key": APP_API_KEY or ""},
                    timeout=httpx.Timeout(
                        connect=20.0,
                        read=150.0,
                        write=20.0,
                        pool=10.0
                    )
                )

            response.raise_for_status()
            result = response.json()

            st.session_state["email_result"] = result
            st.session_state["request_id"] = response.headers.get(
                "X-Request-ID",
                "Not available"
            )

        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code

            if status == 401:
                st.error(
                    "API authentication failed. "
                    "Check the application configuration."
                )
            elif status == 429:
                st.error("Rate limit reached. Please try later.")
            elif status == 422:
                st.error("Please check your input values.")
            else:
                st.error(f"Email generation failed (HTTP {status}).")

        except httpx.RequestError:
            st.error(
                "Cannot connect to the backend. "
                "Please check that FastAPI is running."
            )

        except (ValueError, KeyError):
            st.error("The backend returned an invalid response.")

if "email_result" in st.session_state:
    st.caption(
        f"Request ID: {st.session_state.get('request_id', 'N/A')}"
    )
    result = st.session_state["email_result"]

    st.subheader("Generated Email")

    subject = st.text_input(
        "Subject",
        value=result["subject"]
    )

    body = st.text_area(
        "Email Body",
        value=result["body"],
        height=250
    )

    email_text = f"Subject: {subject}\n\n{body}"

    st.download_button(
        "Download Email",
        data=email_text,
        file_name="generated_email.txt",
        mime="text/plain"
    )
