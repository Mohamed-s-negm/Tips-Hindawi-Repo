from __future__ import annotations

import html
import json
from io import BytesIO
from typing import Any
from urllib.parse import urlparse, urlunparse

import pypdf
import requests
import streamlit as st


REQUEST_CONNECT_TIMEOUT_SECONDS = 15
REQUEST_READ_TIMEOUT_SECONDS = 600
PREVIEW_CHARACTER_LIMIT = 1_200

st.set_page_config(
    page_title="Career Coach | AI Career Studio",
    page_icon="✦",
    layout="wide",
    initial_sidebar_state="expanded",
)


def inject_styles() -> None:
    st.markdown(
        """
        <style>
        :root {
            color-scheme: dark;
            --canvas: #090d18;
            --surface: rgba(255, 255, 255, 0.035);
            --surface-raised: rgba(255, 255, 255, 0.055);
            --line: rgba(148, 163, 184, 0.16);
            --muted: #9aa8bd;
            --text: #edf3ff;
            --blue: #8ab4ff;
            --green: #6ee7b7;
            --amber: #fbbf72;
            --red: #fda4af;
        }
        .stApp {
            background:
                radial-gradient(ellipse at 8% 0%, rgba(61, 100, 210, 0.18), transparent 32rem),
                radial-gradient(ellipse at 94% 14%, rgba(24, 164, 142, 0.10), transparent 27rem),
                var(--canvas);
            color: var(--text);
        }
        [data-testid="stHeader"] { background: rgba(9, 13, 24, 0.72); }
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #101727 0%, #0c1220 100%);
            border-right: 1px solid var(--line);
        }
        [data-testid="stSidebar"] > div { padding-top: 1.6rem; }
        h1, h2, h3 { letter-spacing: -0.035em; }
        h1 { font-size: clamp(2.1rem, 4vw, 3.2rem) !important; }
        .eyebrow {
            color: #8ab4ff;
            font-size: 0.76rem;
            font-weight: 750;
            letter-spacing: 0.16em;
            text-transform: uppercase;
            margin-bottom: 0.5rem;
        }
        .hero-copy { color: var(--muted); font-size: 1.05rem; max-width: 48rem; }
        .glass-card {
            background: var(--surface);
            border: 1px solid var(--line);
            border-radius: 18px;
            box-shadow: 0 16px 40px rgba(0, 0, 0, 0.18);
            padding: 1.15rem 1.3rem;
        }
        .section-kicker {
            color: var(--muted);
            font-size: 0.78rem;
            font-weight: 700;
            letter-spacing: 0.11em;
            margin: 0 0 0.85rem;
            text-transform: uppercase;
        }
        .status-pill {
            align-items: center;
            border: 1px solid var(--line);
            border-radius: 999px;
            display: inline-flex;
            font-size: 0.84rem;
            font-weight: 650;
            gap: 0.55rem;
            padding: 0.42rem 0.75rem;
        }
        .status-dot {
            border-radius: 50%;
            display: inline-block;
            height: 0.55rem;
            width: 0.55rem;
        }
        .status-ready { color: #a7f3d0; background: rgba(16, 185, 129, 0.09); }
        .status-ready .status-dot { background: #34d399; box-shadow: 0 0 12px rgba(52, 211, 153, .65); }
        .status-missing { color: #fecdd3; background: rgba(244, 63, 94, 0.08); }
        .status-missing .status-dot { background: #fb7185; }
        .skill-wrap { display: flex; flex-wrap: wrap; gap: 0.55rem; }
        .skill-pill {
            border: 1px solid;
            border-radius: 999px;
            display: inline-block;
            font-size: 0.88rem;
            line-height: 1.35;
            padding: 0.38rem 0.72rem;
        }
        .skill-good {
            background: rgba(16, 185, 129, 0.10);
            border-color: rgba(52, 211, 153, 0.26);
            color: #a7f3d0;
        }
        .skill-gap {
            background: rgba(251, 146, 60, 0.09);
            border-color: rgba(251, 146, 60, 0.25);
            color: #fed7aa;
        }
        .job-title {
            background: rgba(138, 180, 255, 0.08);
            border: 1px solid rgba(138, 180, 255, 0.2);
            border-radius: 12px;
            color: #d8e6ff;
            margin: 0.45rem 0;
            padding: 0.75rem 0.9rem;
        }
        .roadmap-step {
            color: #8ab4ff;
            font-size: 0.75rem;
            font-weight: 750;
            letter-spacing: 0.12em;
            margin-bottom: 0.35rem;
            text-transform: uppercase;
        }
        div[data-testid="stMetric"] {
            background: var(--surface);
            border: 1px solid var(--line);
            border-radius: 16px;
            padding: 1rem 1.05rem;
            min-height: 112px;
        }
        div[data-testid="stMetricLabel"] { color: var(--muted); }
        div[data-testid="stMetricValue"] { color: var(--text); overflow-wrap: anywhere; }
        .stButton > button[kind="primary"] {
            background: linear-gradient(100deg, #3568d4, #397dd2);
            border: 1px solid rgba(159, 194, 255, 0.34);
            border-radius: 12px;
            box-shadow: 0 8px 24px rgba(44, 98, 205, 0.24);
            color: white;
            font-weight: 700;
            min-height: 3rem;
        }
        .stButton > button[kind="primary"]:hover { border-color: #b9d2ff; }
        .stTextInput input, .stTextArea textarea {
            background: rgba(255, 255, 255, 0.035);
            border-color: var(--line);
            border-radius: 10px;
        }
        [data-testid="stExpander"] {
            background: rgba(255, 255, 255, 0.025);
            border: 1px solid var(--line);
            border-radius: 12px;
        }
        @media (max-width: 700px) {
            .glass-card { padding: 1rem; }
            [data-testid="stMetric"] { min-height: 96px; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """Extract selectable text from an uploaded PDF."""
    reader = pypdf.PdfReader(BytesIO(pdf_bytes))
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n".join(page for page in pages if page).strip()


def extract_json_block(text: str) -> str:
    """Return the last valid top-level JSON object in a model response."""
    if text is None:
        raise ValueError("The API returned an empty response.")

    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return text.strip()
    except (TypeError, ValueError):
        pass

    candidates: list[str] = []
    depth = 0
    start = 0
    in_string = False
    escaped = False

    for index, character in enumerate(text):
        if depth == 0:
            if character == "{":
                start = index
                depth = 1
                in_string = False
                escaped = False
            continue

        if in_string:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == '"':
                in_string = False
        elif character == '"':
            in_string = True
        elif character == "{":
            depth += 1
        elif character == "}":
            depth -= 1
            if depth == 0:
                candidates.append(text[start : index + 1])

    for candidate in reversed(candidates):
        try:
            if isinstance(json.loads(candidate), dict):
                return candidate
        except json.JSONDecodeError:
            continue

    raise ValueError(
        "The model response did not contain a valid JSON object. "
        "The output may have been truncated or malformed."
    )


def _first_value(data: dict[str, Any], *keys: str, default: Any = "") -> Any:
    for key in keys:
        value = data.get(key)
        if value is not None and value != "":
            return value
    return default


def _as_items(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, (str, dict)):
        return [value]
    return []


def _display_text(value: Any) -> str:
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value).strip()


def _normalize_skill(value: Any) -> str:
    if isinstance(value, dict):
        return _display_text(
            _first_value(value, "name", "skill", "title", "technology", default=value)
        )
    return _display_text(value)


def _normalize_roadmap_step(step: Any) -> tuple[str, str]:
    if isinstance(step, dict):
        title = _display_text(
            _first_value(step, "title", "step", "name", "phase", default="Career milestone")
        )
        details = _first_value(
            step, "description", "details", "action", "focus", "goal", default=""
        )
        duration = _first_value(step, "duration", "timeline", "timeframe", default="")
        detail_text = _display_text(details) if details else ""
        if duration:
            detail_text = f"{detail_text}\n\n**Suggested timing:** {_display_text(duration)}".strip()
        return title, detail_text or "Use this milestone to build evidence of progress."
    return _display_text(step), ""


def _normalize_api_result(response_data: Any) -> dict[str, Any]:
    """Unwrap the existing API's response field and parse its JSON payload."""
    payload = response_data
    if isinstance(response_data, dict) and "response" in response_data:
        payload = response_data["response"]

    if isinstance(payload, str):
        payload = json.loads(extract_json_block(payload))
    elif isinstance(payload, dict):
        # Some endpoints wrap the generated content in another response object.
        for key in ("content", "result", "output"):
            nested = payload.get(key)
            if isinstance(nested, str):
                try:
                    payload = json.loads(extract_json_block(nested))
                except (json.JSONDecodeError, ValueError):
                    continue
                break

    if not isinstance(payload, dict):
        raise ValueError("The API response must contain a JSON object.")
    return payload


def build_generate_url(api_url: str) -> str:
    """Normalize a backend base URL to its /generate endpoint."""
    parsed_url = urlparse(api_url)
    if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
        raise ValueError("Enter a valid backend URL beginning with http:// or https://.")

    path = parsed_url.path.rstrip("/")
    if path.rsplit("/", 1)[-1].casefold() != "generate":
        path = f"{path}/generate"
    return urlunparse(parsed_url._replace(path=path, fragment=""))


def call_backend(
    api_url: str,
    api_key: str,
    cv_text: str,
) -> dict[str, Any]:
    """Send the CV using the Kaggle API's Bearer authorization format."""
    headers = {"Authorization": f"Bearer {api_key}"}
    response = requests.post(
        build_generate_url(api_url),
        headers=headers,
        json={"prompt": cv_text, "max_length": 2048},
        timeout=(REQUEST_CONNECT_TIMEOUT_SECONDS, REQUEST_READ_TIMEOUT_SECONDS),
    )
    response.raise_for_status()
    return _normalize_api_result(response.json())


def skill_pill_markup(items: list[Any], variant: str, empty_message: str) -> str:
    skills = [_normalize_skill(item) for item in items]
    skills = [skill for skill in skills if skill]
    if not skills:
        return f'<span style="color:#9aa8bd">{html.escape(empty_message)}</span>'

    return "".join(
        f'<span class="skill-pill skill-{variant}">{html.escape(skill)}</span>'
        for skill in skills
    )


def render_dashboard(data: dict[str, Any]) -> None:
    full_name = _display_text(_first_value(data, "full_name", "name", "candidate_name", default="Not provided"))
    email = _display_text(_first_value(data, "email", "email_address", default="Not provided"))
    recommendation = data.get("career_recommendation")
    if not isinstance(recommendation, dict):
        recommendation = {}
    career = _display_text(
        _first_value(recommendation, "career_name", default="Not provided")
    )
    score_value = _display_text(
        _first_value(recommendation, "match_score", default="Not provided")
    )

    st.markdown('<div class="section-kicker">Career snapshot</div>', unsafe_allow_html=True)
    first_row = st.columns(2)
    first_row[0].metric("Full name", full_name)
    first_row[1].metric("Email", email)
    second_row = st.columns(2)
    second_row[0].metric("Target career", career)
    second_row[1].metric("Profile match", score_value)

    education = _as_items(data.get("education"))
    experience = _as_items(data.get("experience"))
    all_skills = _as_items(data.get("skills"))
    demonstrated = _as_items(recommendation.get("current_relevant_skills"))
    gaps = _as_items(recommendation.get("missing_skills"))

    st.markdown("### Career recommendation")
    reason = _display_text(recommendation.get("reason", "")).strip()
    if reason:
        st.markdown(
            f'<div class="glass-card">{html.escape(reason)}</div>',
            unsafe_allow_html=True,
        )
    else:
        st.caption("No recommendation rationale was included in this response.")

    st.markdown("### Skills")
    skills_left, skills_right = st.columns(2, gap="large")
    with skills_left:
        st.markdown(
            '<div class="glass-card"><div class="section-kicker">Relevant skills for this career</div>'
            f'<div class="skill-wrap">{skill_pill_markup(demonstrated, "good", "No relevant skills were returned.")}</div></div>',
            unsafe_allow_html=True,
        )
    with skills_right:
        st.markdown(
            '<div class="glass-card"><div class="section-kicker">Missing skills</div>'
            f'<div class="skill-wrap">{skill_pill_markup(gaps, "gap", "No skill gaps were returned.")}</div></div>',
            unsafe_allow_html=True,
        )

    st.markdown("### Skills listed in your CV")
    st.markdown(
        f'<div class="skill-wrap">{skill_pill_markup(all_skills, "good", "No skills were returned.")}</div>',
        unsafe_allow_html=True,
    )

    priorities = _as_items(recommendation.get("skill_priorities"))
    st.markdown("### Skill priorities")
    if priorities:
        for index, priority in enumerate(priorities, start=1):
            st.markdown(f"{index}. {_display_text(priority)}")
    else:
        st.caption("No skill priorities were included in this response.")

    roadmap = _as_items(recommendation.get("roadmap"))
    st.markdown("### Your development roadmap")
    if roadmap:
        for index, step in enumerate(roadmap, start=1):
            title, details = _normalize_roadmap_step(step)
            safe_title = html.escape(title)
            with st.expander(f"{index:02d}  ·  {title}", expanded=index == 1):
                st.markdown(
                    f'<div class="roadmap-step">Milestone {index}</div>',
                    unsafe_allow_html=True,
                )
                st.markdown(details or safe_title)
    else:
        st.info("No roadmap steps were included in this response.")

    projects = _as_items(recommendation.get("suggested_projects"))
    st.markdown("### Suggested projects")
    if projects:
        for project in projects:
            st.markdown(
                f'<div class="job-title">{html.escape(_display_text(project))}</div>',
                unsafe_allow_html=True,
            )
    else:
        st.caption("No project ideas were included in this response.")

    job_titles = _as_items(recommendation.get("suggested_job_titles"))
    st.markdown("### Suggested search titles")
    if job_titles:
        title_columns = st.columns(min(3, len(job_titles)))
        for index, title in enumerate(job_titles):
            title_text = _display_text(title)
            title_columns[index % len(title_columns)].markdown(
                f'<div class="job-title">{html.escape(title_text)}</div>',
                unsafe_allow_html=True,
            )
    else:
        st.caption("No search titles were included in this response.")

    st.markdown("### Education")
    if education:
        for index, item in enumerate(education, start=1):
            if isinstance(item, dict):
                heading = _display_text(
                    _first_value(item, "degree", "field", "qualification", default=f"Education {index}")
                )
                detail = " · ".join(
                    _display_text(item[key])
                    for key in ("institution", "year")
                    if item.get(key) not in (None, "")
                )
                st.markdown(
                    f'<div class="job-title"><strong>{html.escape(heading)}</strong>'
                    f'{"<br>" + html.escape(detail) if detail else ""}</div>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(f'<div class="job-title">{html.escape(_display_text(item))}</div>', unsafe_allow_html=True)
    else:
        st.caption("No education details were returned.")

    st.markdown("### Experience")
    if experience:
        for index, item in enumerate(experience, start=1):
            if isinstance(item, dict):
                role = _display_text(_first_value(item, "role", "title", "position", default=f"Experience {index}"))
                company = _display_text(_first_value(item, "company", "employer", default=""))
                dates = _display_text(_first_value(item, "dates", "years", "duration", default=""))
                responsibilities = _as_items(item.get("responsibilities"))
                details = " · ".join(value for value in (company, dates) if value)
                content = (
                    f'<div class="job-title"><strong>{html.escape(role)}</strong>'
                    f'{"<br>" + html.escape(details) if details else ""}'
                )
                if responsibilities:
                    content += "<ul>" + "".join(
                        f"<li>{html.escape(_display_text(value))}</li>"
                        for value in responsibilities
                    ) + "</ul>"
                content += "</div>"
                st.markdown(content, unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="job-title">{html.escape(_display_text(item))}</div>', unsafe_allow_html=True)
    else:
        st.caption("No experience details were returned.")

def render_input() -> tuple[str, str]:
    upload_tab, paste_tab = st.tabs(("📄  Upload Resume (PDF)", "✍️  Paste Raw CV Text"))

    with upload_tab:
        uploaded_file = st.file_uploader(
            "Choose a PDF resume",
            type=["pdf"],
            accept_multiple_files=False,
            help="Text-based PDFs work best. Scanned image-only PDFs may not contain extractable text.",
            key="resume_pdf",
        )
        pdf_text = ""
        if uploaded_file is not None:
            try:
                pdf_text = extract_text_from_pdf(uploaded_file.getvalue())
                with st.expander(
                    f"Resume text · {len(pdf_text):,} characters",
                    expanded=False,
                ):
                    if pdf_text:
                        st.text(pdf_text[:PREVIEW_CHARACTER_LIMIT])
                        if len(pdf_text) > PREVIEW_CHARACTER_LIMIT:
                            st.caption("Preview truncated. The complete extracted text will be analyzed.")
                    else:
                        st.warning("No selectable text was found in this PDF.")
            except (pypdf.errors.PdfReadError, OSError, ValueError) as error:
                st.error(f"Could not read this PDF: {error}")

    with paste_tab:
        pasted_text = st.text_area(
            "Paste your CV or resume text",
            placeholder="Include your experience, education, skills, and the roles you are targeting…",
            height=220,
            key="resume_text",
        )

    if pdf_text.strip() and pasted_text.strip():
        chosen_source = st.radio(
            "Choose which resume input to analyze",
            ("Uploaded PDF", "Pasted text"),
            horizontal=True,
            key="resume_source",
        )
        return (pdf_text, "PDF") if chosen_source == "Uploaded PDF" else (pasted_text, "Text")
    if pdf_text.strip():
        return pdf_text, "PDF"
    if pasted_text.strip():
        return pasted_text, "Text"
    return "", ""


def main() -> None:
    inject_styles()

    with st.sidebar:
        st.markdown("## ⚙️ Connection")
        st.caption("Connect your career-analysis service.")
        api_url = st.text_input(
            "Backend API URL",
            placeholder="https://api.example.com",
            help="Enter the backend base URL; /generate is appended automatically.",
        ).strip()
        api_key = st.text_input(
            "API Key (Kaggle API_KEY)",
            type="password",
            placeholder="Enter your API key",
            help='Sent as {"Authorization": f"Bearer {API_KEY}"}; enter the key only, without the Bearer prefix.',
        ).strip()
        is_ready = bool(api_url and api_key)
        status_class = "status-ready" if is_ready else "status-missing"
        status_text = "Ready to connect" if is_ready else "Missing connection details"
        st.markdown(
            f'<div class="status-pill {status_class}"><span class="status-dot"></span>{status_text}</div>',
            unsafe_allow_html=True,
        )
        if api_url:
            try:
                st.caption(f"Request endpoint: `{build_generate_url(api_url)}`")
            except ValueError:
                st.caption("Enter a valid HTTP or HTTPS backend URL.")
        st.divider()
        st.caption("Your API key is sent as a Bearer authorization value and is not displayed in the dashboard.")

    st.markdown('<div class="eyebrow">AI Career Studio</div>', unsafe_allow_html=True)
    st.title("Make your next career move with clarity.")
    st.markdown(
        '<p class="hero-copy">Turn your experience into a focused career plan. Add your resume, connect your analysis service, and get a practical view of your strengths and next steps.</p>',
        unsafe_allow_html=True,
    )
    st.write("")

    cv_text, input_kind = render_input()
    st.write("")
    analyze_clicked = st.button(
        "🚀  Analyze Career Path",
        type="primary",
        use_container_width=True,
        disabled=not bool(cv_text.strip()),
    )

    if analyze_clicked:
        st.session_state.pop("career_result", None)
        if not is_ready:
            st.error("Add the backend API URL and Kaggle API_KEY in the sidebar before analyzing.")
        elif not cv_text.strip():
            st.error("Add resume text or upload a readable PDF before analyzing.")
        else:
            with st.spinner(f"Analyzing your {input_kind.lower()} and building your career plan…"):
                try:
                    st.session_state["career_result"] = call_backend(
                        api_url,
                        api_key,
                        cv_text.strip(),
                    )
                    st.session_state["career_result_source"] = input_kind
                except requests.Timeout:
                    st.error(
                        "No response was received from Kaggle within 10 minutes. "
                        "Model generation may still be running there; check the Kaggle output before retrying "
                        "to avoid starting duplicate work."
                    )
                except requests.HTTPError as error:
                    status = error.response.status_code if error.response is not None else "unknown"
                    if status == 401:
                        endpoint = build_generate_url(api_url)
                        st.error(
                            f"The server at {endpoint} rejected the request (HTTP 401). "
                            "The URL includes /generate. Check that the API key matches the Kaggle API_KEY. "
                            "Enter the key only; the app adds the Bearer prefix."
                        )
                    else:
                        st.error(
                            f"The career-analysis service returned HTTP {status} from "
                            f"{build_generate_url(api_url)}. Check the endpoint and try again."
                        )
                except requests.ConnectionError:
                    st.error("Could not connect to the career-analysis service. Check the URL and your network.")
                except requests.RequestException as error:
                    st.error(f"The career-analysis request failed: {error}")
                except (json.JSONDecodeError, ValueError) as error:
                    st.error(f"The service response could not be understood: {error}")

    result = st.session_state.get("career_result")
    if isinstance(result, dict):
        st.write("")
        st.markdown("---")
        render_dashboard(result)


if __name__ == "__main__":
    main()
