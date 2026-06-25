import streamlit as st
import fitz  # PyMuPDF
import google.generativeai as genai
import textwrap

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Nischal Chat Bot",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Styling ───────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=EB+Garamond:wght@400;600&family=Inter:wght@400;500;600&display=swap');

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

.divider {
    border: none;
    border-top: 1px solid #2a2d3a;
    margin: 1.2rem 0;
}

.stButton > button {
    background: #c9a84c;
    color: #0f1117;
    border: none;
    border-radius: 6px;
    font-weight: 600;
    font-size: 0.88rem;
    padding: 0.5rem 1.2rem;
    transition: background 0.2s;
}

.stButton > button:hover {
    background: #e0bf6a;
    color: #0f1117;
}

.stTextInput > div > div > input {
    background: #1a1d27;
    border: 1px solid #2a2d3a;
    color: #e8e8e8;
    border-radius: 6px;
}

section[data-testid="stSidebar"] {
    background-color: #13151f;
    border-right: 1px solid #2a2d3a;
}

.upload-hint {
    font-size: 0.8rem;
    color: #666;
    margin-top: 0.4rem;
}
</style>
""", unsafe_allow_html=True)

# ── Helpers ───────────────────────────────────────────────────────────────────
MAX_PAGES = 100

def extract_pdf_text(file) -> tuple[str, int]:
    """Extract text from uploaded PDF, capped at MAX_PAGES."""
    doc = fitz.open(stream=file.read(), filetype="pdf")
    pages = min(len(doc), MAX_PAGES)
    text = ""
    for i in range(pages):
        text += doc[i].get_text()
    return text.strip(), pages


def get_gemini_model():
    api_key = st.secrets.get("GEMINI_API_KEY", "")
    if not api_key:
        st.error("⚠️ Add your GEMINI_API_KEY to Streamlit secrets.")
        st.stop()
    genai.configure(api_key=api_key)
    return genai.GenerativeModel("gemini-1.5-flash")


ANALYSIS_PROMPT = """
You are a senior legal analyst. Read the legal document below and produce a structured analysis.
Return EXACTLY these 7 sections, each starting with its label on its own line, followed by the content.
Keep each section concise: 2–5 sentences or a short bulleted list. Do not pad or repeat.

CASE NAME:
PARTIES:
MATERIAL FACTS:
LEGAL ISSUES:
RATIO DECIDENDI:
DECISION / HOLDING:
KEY TAKEAWAY:

Document:
{text}
"""

CHAT_PROMPT = """
You are a sharp legal assistant. The user has uploaded a legal document.
Answer questions about it clearly and concisely — 2 to 5 sentences max.
Do not repeat the question. Get straight to the point.

Document context:
{context}

User question: {question}
"""


def parse_analysis(raw: str) -> dict:
    labels = [
        "CASE NAME", "PARTIES", "MATERIAL FACTS",
        "LEGAL ISSUES", "RATIO DECIDENDI", "DECISION / HOLDING", "KEY TAKEAWAY"
    ]
    result = {l: "" for l in labels}
    lines = raw.splitlines()
    current = None
    buffer = []

    for line in lines:
        stripped = line.strip()
        matched = False
        for label in labels:
            if stripped.upper().startswith(label):
                if current:
                    result[current] = " ".join(buffer).strip()
                current = label
                # Content may follow the colon on the same line
                after = stripped[len(label):].lstrip(":").strip()
                buffer = [after] if after else []
                matched = True
                break
        if not matched and current:
            buffer.append(stripped)

    if current:
        result[current] = " ".join(buffer).strip()

    return result


def render_analysis(sections: dict):
    icons = {
        "CASE NAME": "🏛️",
        "PARTIES": "👥",
        "MATERIAL FACTS": "📋",
        "LEGAL ISSUES": "⚖️",
        "RATIO DECIDENDI": "📐",
        "DECISION / HOLDING": "🔨",
        "KEY TAKEAWAY": "💡",
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
if "doc_text" not in st.session_state:
    st.session_state.doc_text = ""
if "analysis" not in st.session_state:
    st.session_state.analysis = {}
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "page_count" not in st.session_state:
    st.session_state.page_count = 0

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
            with st.spinner("Analysing…"):
                model = get_gemini_model()
                prompt = ANALYSIS_PROMPT.format(
                    text=st.session_state.doc_text[:30000]
                )
                response = model.generate_content(prompt)
                st.session_state.analysis = parse_analysis(response.text)

        st.markdown('<hr class="divider">', unsafe_allow_html=True)
        if st.button("🗑️ Clear Everything"):
            for key in ["doc_text", "analysis", "chat_history", "page_count"]:
                st.session_state[key] = {} if key == "analysis" else ([] if key == "chat_history" else ("" if key != "page_count" else 0))
            st.rerun()

    st.markdown('<hr class="divider">', unsafe_allow_html=True)
    st.markdown('<div style="font-size:0.75rem;color:#555;">Powered by Gemini 1.5 Flash · Free tier</div>', unsafe_allow_html=True)


# ── Main layout ───────────────────────────────────────────────────────────────
col_analysis, col_chat = st.columns([1.1, 0.9], gap="large")

# Left column — Analysis
with col_analysis:
    st.markdown('<div class="main-title" style="font-size:1.6rem;">Case Analysis</div>', unsafe_allow_html=True)
    st.markdown('<hr class="divider">', unsafe_allow_html=True)

    if not st.session_state.doc_text:
        st.markdown("""
        <div class="card">
            <div class="card-content" style="color:#666;">
                Upload a PDF from the sidebar, then click <strong style="color:#c9a84c;">Analyse Document</strong> to extract the case summary.
            </div>
        </div>
        """, unsafe_allow_html=True)
    elif not st.session_state.analysis:
        st.markdown("""
        <div class="card">
            <div class="card-content" style="color:#888;">
                Document loaded. Click <strong style="color:#c9a84c;">Analyse Document</strong> in the sidebar.
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        render_analysis(st.session_state.analysis)


# Right column — Chat
with col_chat:
    st.markdown('<div class="main-title" style="font-size:1.6rem;">Ask Nischal</div>', unsafe_allow_html=True)
    st.markdown('<hr class="divider">', unsafe_allow_html=True)

    if not st.session_state.doc_text:
        st.markdown("""
        <div class="card">
            <div class="card-content" style="color:#666;">
                Upload a document first to start asking questions.
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        # Chat history display
        chat_container = st.container()
        with chat_container:
            if not st.session_state.chat_history:
                st.markdown("""
                <div class="card" style="border-color:#2a2d3a;">
                    <div class="card-content" style="color:#666;font-size:0.85rem;">
                        Ask anything about the document — parties, jurisdiction, ratio, outcome…
                    </div>
                </div>
                """, unsafe_allow_html=True)
            for turn in st.session_state.chat_history:
                st.markdown(f'<div class="chat-bubble-user">🧑 {turn["q"]}</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="chat-bubble-bot">🤖 {turn["a"]}</div>', unsafe_allow_html=True)

        st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)

        # Input
        with st.form("chat_form", clear_on_submit=True):
            question = st.text_input("Your question", placeholder="e.g. What was the main legal issue?", label_visibility="collapsed")
            submitted = st.form_submit_button("Send →")

        if submitted and question.strip():
            with st.spinner("Thinking…"):
                model = get_gemini_model()
                context = st.session_state.doc_text[:20000]
                prompt = CHAT_PROMPT.format(context=context, question=question.strip())
                response = model.generate_content(prompt)
                answer = response.text.strip()
                st.session_state.chat_history.append({"q": question.strip(), "a": answer})
            st.rerun()

        if st.session_state.chat_history:
            if st.button("Clear chat"):
                st.session_state.chat_history = []
                st.rerun()
