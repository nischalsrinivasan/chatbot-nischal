import streamlit as st
import fitz  # PyMuPDF
import requests
import re
import string

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

# ── Constants & Robust Fallbacks ──────────────────────────────────────────────
MAX_PAGES = 100
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# Production ready high-capacity models
FALLBACK_FREE_MODELS = [
    "meta-llama/llama-3.3-70b-instruct:free",
    "openai/gpt-oss-120b:free",
    "openrouter/free"
]

# ── OpenRouter API Call ───────────────────────────────────────────────────────
def call_openrouter(api_key: str, system_prompt: str, user_message: str, max_tokens: int = 1500) -> str:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://nischal-chatbot.streamlit.app",
        "X-Title": "Nischal Chat Bot",
    }
    
    last_err = ""
    for model in FALLBACK_FREE_MODELS:
        payload = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
        }
        try:
            resp = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=45)
            if resp.status_code == 200:
                text_out = resp.json()["choices"][0]["message"]["content"].strip()
                if text_out:
                    return text_out
            last_err = f"Model {model} status {resp.status_code}: {resp.text[:100]}"
        except Exception as e:
            last_err = str(e)
            continue
            
    raise RuntimeError(f"All free model options failed. Trace logs: {last_err}")

# ── PDF helpers ───────────────────────────────────────────────────────────────
def clean_extracted_text(text: str) -> str:
    """Cleans up bad stream encodings from the PDF layout reader."""
    printable = set(string.printable)
    cleaned = "".join(filter(lambda x: x in printable, text))
    cleaned = re.sub(r'[^\x20-\x7E\n\t]', '', cleaned)
    return cleaned.strip()

def extract_pdf_text(file) -> tuple[str, int]:
    doc = fitz.open(stream=file.read(), filetype="pdf")
    pages = min(len(doc), MAX_PAGES)
    text_runs = []
    
    for i in range(pages):
        page = doc[i]
        # Using layout blocks processing to extract clean textual chunks
        blocks = page.get_text("blocks")
        page_text = "\n".join([b[4] for b in blocks if isinstance(b[4], str)])
        text_runs.append(page_text)
        
    full_raw_text = "\n".join(text_runs)
    return clean_extracted_text(full_raw_text), pages


# ── Prompts ───────────────────────────────────────────────────────────────────
ANALYSIS_SYSTEM = """You are an expert legal intelligence system. Analyze the provided case filing text and summarize the critical legal information. 

You must output your complete analysis wrapped inside explicit HTML tags for safe processing. Extract the real context from the case file under these exact tags:

<casename>Provide the clear name of the case or filing title here</casename>
<parties>Identify all named plaintiffs, appellants, defendants, or respondents involved</parties>
<facts>Summarize the core factual background, event history, and core dispute details</facts>
<issues>Detail the main points of law or constitutional questions the court must resolve</issues>
<ratio>Explain the primary legal rationale, principles, or precedents applied by the judges</ratio>
<holding>State the exact final ruling, decree, order, or judgment delivered</holding>
<takeaway>State the key legal significance or future practice impact of this case</takeaway>

Provide thorough analytical summaries for each item. Do not leave fields empty or write refusal statements."""

CHAT_SYSTEM = """You are a sharp legal assistant helping a user understand a specific legal document.
Answer questions clearly and concisely — 2 to 5 sentences maximum.
Do not repeat the question. Get straight to the point. Do not make up facts not in the document."""


# ── Parse Tagged Analysis Output ──────────────────────────────────────────────
def parse_analysis(raw: str) -> dict:
    tags = {
        "CASE NAME": "casename",
        "PARTIES": "parties",
        "MATERIAL FACTS": "facts",
        "LEGAL ISSUES": "issues",
        "RATIO DECIDENDI": "ratio",
        "DECISION / HOLDING": "holding",
        "KEY TAKEAWAY": "takeaway"
    }
    result = {}
    
    for label, tag in tags.items():
        pattern = rf"<{tag}>(.*?)</{tag}>"
        match = re.search(pattern, raw, re.DOTALL | re.IGNORECASE)
        if match:
            result[label] = match.group(1).strip()
        else:
            # Fallback strategy: if tags are ignored, try string split fallback logic
            fallback_pattern = rf"(?i){label}\s*:?\s*(.*?)(?=\n\n|\n[A-Z\s]+:|$)"
            fb_match = re.search(fallback_pattern, raw, re.DOTALL)
            if fb_match and len(fb_match.group(1).strip()) > 10:
                result[label] = fb_match.group(1).strip()
            else:
                result[label] = "Information extraction parsing anomaly. Please re-run the analysis button."
                
    return result


def render_analysis(sections: dict):
    icons = {
        "CASE NAME": "🏛️", "PARTIES": "👥", "MATERIAL FACTS": "📋",
        "LEGAL ISSUES": "⚖️", "RATIO DECIDENDI": "📐",
        "DECISION / HOLDING": "🔨", "KEY TAKEAWAY": "💡",
    }
    for label, content in sections.items():
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
        with st.spinner("Processing document text lines..."):
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
                with st.spinner("Processing analytical parsing matrix..."):
                    try:
                        raw = call_openrouter(
                            api_key,
                            system_prompt=ANALYSIS_SYSTEM,
                            user_message=f"Document Source Context for Extraction:\n\n{st.session_state.doc_text[:35000]}",
                            max_tokens=1500,
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
        '<div style="font-size:0.75rem;color:#555;">Powered by OpenRouter High-Capacity Tiers</div>',
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
                        context = st.session_state.doc_text[:18000]
                        user_msg = f"Document Context:\n{context}\n\nQuestion: {question.strip()}"
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
