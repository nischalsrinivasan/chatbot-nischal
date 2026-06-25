import streamlit as st
import fitz  # PyMuPDF
import requests

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Nischal Chat Bot",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Styling ───────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=EB+Garamond:wght=400;600&family=Inter:wght=400;500;600&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
    background-color: #0f1117;
    color: #e8e8e8;
}
.main-title {
    font-family: 'EB Garamond', serif;
    font-size: 2.4rem;
    font-weight: 600;
    color: #c9a84c;
    letter-spacing: 0.02em;
    margin-bottom: 0.2rem;
}
.subtitle {
    font-size: 0.9rem;
    color: #888;
    margin-bottom: 1.5rem;
    letter-spacing: 0.05em;
    text-transform: uppercase;
}
.card {
    background: #1a1d27;
    border: 1px solid #2a2d3a;
    border-radius: 10px;
    padding: 1.2rem 1.4rem;
    margin-bottom: 1rem;
}
.card-label {
    font-size: 0.72rem;
    font-weight: 600;
    color: #c9a84c;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    margin-bottom: 0.4rem;
}
.card-content {
    font-size: 0.92rem;
    color: #d4d4d4;
    line-height: 1.65;
}
.chat-bubble-user {
    background: #1e2235;
    border-left: 3px solid #c9a84c;
    border-radius: 8px;
    padding: 0.7rem 1rem;
    margin: 0.5rem 0;
    font-size: 0.9rem;
}
.chat-bubble-bot {
    background: #151820;
    border-left: 3px solid #4a7c9e;
    border-radius: 8px;
    padding: 0.7rem 1rem;
    margin: 0.5rem 0;
    font-size: 0.9rem;
    color: #d4d4d4;
}
.divider { border: none; border-top: 1px solid #2a2d3a; margin: 1.2rem 0; }
.stButton > button {
    background: #c9a84c; color: #0f1117; border: none;
    border-radius: 6px; font-weight: 600; font-size: 0.88rem;
    padding: 0.5rem 1.2rem; transition: background 0.2s;
}
.stButton > button:hover { background: #e0bf6a; color: #0f1117; }
.stTextInput > div > div > input {
    background: #1a1d27; border: 1px solid #2a2d3a;
    color: #e8e8e8; border-radius: 6px;
}
section[data-testid="stSidebar"] {
    background-color: #13151f; border-right: 1px solid #2a2d3a;
}
</style>
""", unsafe_allow_html=True)

# ── Constants ─────────────────────────────────────────────────────────────────
MAX_PAGES = 100
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# ── OpenRouter API Call ───────────────────────────────────────────────────────
def call_openrouter(api_key: str, system_prompt: str, user_message: str, max_tokens: int = 1200) -> str:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://nischal-chatbot.streamlit.app",
        "X-Title": "Nischal Chat Bot",
    }
    payload = {
        "model": "openrouter/free",
        "max_tokens": max_tokens,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
    }
    try:
        resp = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=45)
        if resp.status_code == 200:
            return resp.json()["choices"][0]["message"]["content"].strip()
        else:
            raise RuntimeError(f"OpenRouter returned Status {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        raise RuntimeError(f"Network or API Error: {str(e)}")

# ── PDF helpers ───────────────────────────────────────────────────────────────
def extract_pdf_text(file) -> tuple[str, int]:
    doc = fitz.open(stream=file.read(), filetype="pdf")
    pages = min(len(doc), MAX_PAGES)
    text = ""
    for i in range(pages):
        text += doc[i].get_text()
    return text.strip(), pages


# ── Prompts ───────────────────────────────────────────────────────────────────
ANALYSIS_SYSTEM = """You are a senior legal analyst. Produce a structured case analysis.
CRITICAL: Do not include formatting meta-text explanation examples like 'sentence1, sentence2 => 2 sentences'. 
Output exactly the requested content sections immediately following the exact title labels below. 
Each section must contain 2 to 5 standard analytical sentences. Do not use blank lines between headers or add meta-commentary padding.

CASE NAME:
PARTIES:
MATERIAL FACTS:
LEGAL ISSUES:
RATIO DECIDENDI:
DECISION / HOLDING:
KEY TAKEAWAY:"""

CHAT_SYSTEM = """You are a sharp legal assistant helping a user understand a specific legal document.
Answer questions clearly and concisely — 2 to 5 sentences maximum.
Do not repeat the question. Get straight to the point. Do not make up facts not in the document."""


# ── Parse analysis output ─────────────────────────────────────────────────────
def parse_analysis(raw: str) -> dict:
    labels = [
        "CASE NAME", "PARTIES", "MATERIAL FACTS",
        "LEGAL ISSUES", "RATIO DECIDENDI", "DECISION / HOLDING", "KEY TAKEAWAY",
    ]
    result = {l: "" for l in labels}
    lines = raw.splitlines()
    current = None
    buffer = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        matched = False
        for label in labels:
            if stripped.upper().startswith(label):
                if current:
                    # Clear out meta expressions or placeholder leaks from text
                    content = " ".join(buffer).strip()
                    for pattern in ["=>", "sentences.", "sentence1", "sentence2"]:
                        if pattern in content and len(content) < 100:
                            content = ""
                    result[current] = content
                current = label
                after = stripped[len(label):].lstrip(":").strip()
                buffer = [after] if after else []
                matched = True
                break
        if not matched and current and stripped:
            buffer.append(stripped)

    if current:
        content = " ".join(buffer).strip()
        for pattern in ["=>", "sentences.", "sentence1", "sentence2"]:
            if pattern in content and len(content) < 100:
                content = ""
        result[current] = content
    return result


def render_analysis(sections: dict):
    icons = {
        "CASE NAME": "🏛️", "PARTIES": "👥", "MATERIAL FACTS": "📋",
        "LEGAL ISSUES": "⚖️", "RATIO DECIDENDI": "📐",
        "DECISION / HOLDING": "🔨", "KEY TAKEAWAY": "💡",
    }
    for label, content in sections.items():
        if content:
            st.markdown(f"""
            <div class="card">
                <div class="card-label">{icons.get(label, '•')} {label}</div>
                <div class="card-content">{content}</div>
            </div>
            """, unsafe_allow_html=True)


# ── Session state ─────────────────────────────────────────────────────────────
for key, default in [
    ("doc_text", ""), ("analysis", {}),
    ("chat_history", []), ("page_count", 0),
]:
    if key not in st.session_state:
        st.session_state[key] = default


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="main-title">⚖️ Nischal</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Legal Document Analyser</div>', unsafe_allow_html=True)
    st.markdown('<hr class="divider">', unsafe_allow_html=True)

    uploaded = st.file_uploader("Upload a PDF (max 100 pages)", type=["pdf"])

    if uploaded:
        with st.spinner("Reading PDF…"):
            text, pages = extract_pdf_text(uploaded)
        st.session_state.doc_text = text
        st.session_state.page_count = pages
        st.session_state.analysis = {}
        st.session_state.chat_history = []
        st.success(f"✅ Loaded {pages} page{'s' if pages != 1 else ''}")

    if st.session_state.doc_text:
        st.markdown('<hr class="divider">', unsafe_allow_html=True)
        if st.button("🔍 Analyse Document"):
            api_key = st.secrets.get("OPENROUTER_API_KEY", "")
            if not api_key:
                st.error("⚠️ Add OPENROUTER_API_KEY to Streamlit secrets.")
            else:
                with st.spinner("Analysing via OpenRouter Free..."):
                    try:
                        raw = call_openrouter(
                            api_key,
                            system_prompt=ANALYSIS_SYSTEM,
                            user_message=f"Analyse this legal document:\n\n{st.session_state.doc_text[:24000]}",
                            max_tokens=1400,
                        )
                        st.session_state.analysis = parse_analysis(raw)
                    except Exception as e:
                        st.error(f"Error: {e}")

        st.markdown('<hr class="divider">', unsafe_allow_html=True)
        if st.button("🗑️ Clear Everything"):
            st.session_state.doc_text = ""
            st.session_state.analysis = {}
            st.session_state.chat_history = []
            st.session_state.page_count = 0
            st.rerun()

    st.markdown('<hr class="divider">', unsafe_allow_html=True)
    st.markdown(
        '<div style="font-size:0.75rem;color:#555;">Powered by OpenRouter Auto-Free Router</div>',
        unsafe_allow_html=True,
    )


# ── Main layout ───────────────────────────────────────────────────────────────
col_analysis, col_chat = st.columns([1.1, 0.9], gap="large")

# Left — Analysis
with col_analysis:
    st.markdown('<div class="main-title" style="font-size:1.6rem;">Case Analysis</div>', unsafe_allow_html=True)
    st.markdown('<hr class="divider">', unsafe_allow_html=True)

    if not st.session_state.doc_text:
        st.markdown("""
        <div class="card">
            <div class="card-content" style="color:#666;">
                Upload a PDF from the sidebar, then click
                <strong style="color:#c9a84c;">Analyse Document</strong>.
            </div>
        </div>""", unsafe_allow_html=True)
    elif not st.session_state.analysis:
        st.markdown("""
        <div class="card">
            <div class="card-content" style="color:#888;">
                Document loaded. Click <strong style="color:#c9a84c;">Analyse Document</strong> in the sidebar.
            </div>
        </div>""", unsafe_allow_html=True)
    else:
        render_analysis(st.session_state.analysis)


# Right — Chat
with col_chat:
    st.markdown('<div class="main-title" style="font-size:1.6rem;">Ask Nischal</div>', unsafe_allow_html=True)
    st.markdown('<hr class="divider">', unsafe_allow_html=True)

    if not st.session_state.doc_text:
        st.markdown("""
        <div class="card">
            <div class="card-content" style="color:#666;">
                Upload a document first to start asking questions.
            </div>
        </div>""", unsafe_allow_html=True)
    else:
        # Chat history
        if not st.session_state.chat_history:
            st.markdown("""
            <div class="card" style="border-color:#2a2d3a;">
                <div class="card-content" style="color:#666;font-size:0.85rem;">
                    Ask anything — parties, jurisdiction, ratio, outcome…
                </div>
            </div>""", unsafe_allow_html=True)
        for turn in st.session_state.chat_history:
            st.markdown(f'<div class="chat-bubble-user">🧑 {turn["q"]}</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="chat-bubble-bot">🤖 {turn["a"]}</div>', unsafe_allow_html=True)

        st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)

        with st.form("chat_form", clear_on_submit=True):
            question = st.text_input(
                "Your question",
                placeholder="e.g. What was the main legal issue?",
                label_visibility="collapsed",
            )
            submitted = st.form_submit_button("Send →")

        if submitted and question.strip():
            api_key = st.secrets.get("OPENROUTER_API_KEY", "")
            if not api_key:
                st.error("⚠️ Add OPENROUTER_API_KEY to Streamlit secrets.")
            else:
                with st.spinner("Thinking…"):
                    try:
                        context = st.session_state.doc_text[:16000]
                        user_msg = f"Document:\n{context}\n\nQuestion: {question.strip()}"
                        answer = call_openrouter(
                            api_key,
                            system_prompt=CHAT_SYSTEM,
                            user_message=user_msg,
                            max_tokens=400,
                        )
                        st.session_state.chat_history.append({"q": question.strip(), "a": answer})
                    except Exception as e:
                        st.error(f"Error: {e}")
                st.rerun()

        if st.session_state.chat_history:
            if st.button("Clear chat"):
                st.session_state.chat_history = []
                st.rerun()
