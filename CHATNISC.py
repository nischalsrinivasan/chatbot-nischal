import streamlit as st
import pdfplumber
import pypdfium2 as pdfium
import re
from openai import OpenAI
from textwrap import dedent

st.set_page_config(
    page_title="⚖️ Nischal's Legal AI",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("⚖️ Nischal's Legal AI")
st.caption("AI-powered Judgment Analyzer | Material Facts • Issues • Ratio • Holding • Revision Notes")

# ------------------------------
# Utility Functions
# ------------------------------
def clean_text(text):
    """Clean OCR text while preserving legal formatting and removing cid gibberish."""
    if not text:
        return ""

    # Clear out corrupted (cid:x) font flags completely
    text = re.sub(r"\(cid:\d+\)", "", text)
    text = re.sub(r"\n{2,}", "\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"Page\s+\d+\s+of\s+\d+", "", text, flags=re.IGNORECASE)
    text = re.sub(r"About LexisNexis.*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"Copyright.*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\[\*\d+\]", "", text)
    return text.strip()


def extract_pdf_text(uploaded_file):
    """Extract text using pdfplumber first, then aggressively fallback to pixel layers if gibberish is found."""
    raw_text = ""
    total_pages = 0

    try:
        with pdfplumber.open(uploaded_file) as pdf:
            total_pages = len(pdf.pages)
            for page in pdf.pages:
                txt = page.extract_text()
                if txt:
                    raw_text += txt + "\n"
    except Exception:
        pass

    raw_text = clean_text(raw_text)
    
    # DETECT SCRAMBLED GIBBERISH (Lots of symbols, matching things like <, :, @ without real words)
    # If the text layer contains heavy non-alphanumeric patterns or common font mapping symbols, force fallback
    gibberish_pattern = re.compile(r"[\x00-\x1F\x7F-\x9F]|(?:[a-zA-Z0-9 ]{0,3}[<:@^~]{2,})")
    has_gibberish = len(gibberish_pattern.findall(raw_text)) > 20

    if len(raw_text) < 200 or has_gibberish:
        uploaded_file.seek(0)
        try:
            pdf = pdfium.PdfDocument(uploaded_file.read())
            total_pages = len(pdf)
            raw_text = ""

            for page in pdf:
                # Force standard text extraction fallback first
                textpage = page.get_textpage()
                txt = textpage.get_text_bounded()
                
                # If the bounded text is also garbled, we extract raw layout character indices directly
                if not txt or "cid" in txt or len(gibberish_pattern.findall(txt)) > 5:
                    # Alternative font stream lookup
                    txt = textpage.get_text_range()
                
                if txt:
                    raw_text += txt + "\n"
        except Exception:
            pass

    raw_text = clean_text(raw_text)
    return raw_text, total_pages


def prepare_context(text, max_chars=55000):
    """ Keeps an expanded beginning, middle, and end of long judgments. """
    if len(text) <= max_chars:
        return text

    start = text[:20000]
    middle_start = len(text) // 2 - 10000
    middle_end = len(text) // 2 + 10000
    middle = text[middle_start:middle_end]
    end = text[-15000:]

    return (
        start
        + "\n\n====================\n"
        + "MIDDLE OF JUDGMENT\n"
        + "====================\n\n"
        + middle
        + "\n\n====================\n"
        + "END OF JUDGMENT\n"
        + "====================\n\n"
        + end
    )


# ------------------------------
# Sidebar
# ------------------------------
with st.sidebar:
    st.title("📂 Upload Center")
    uploaded_file = st.file_uploader(
        "Upload Judgment (PDF)",
        type=["pdf"]
    )

    st.divider()
    st.info(
        """
Supported:
✅ Supreme Court | ✅ High Courts | ✅ UK Cases
"""
    )

# ------------------------------
# Load PDF
# ------------------------------
if uploaded_file:
    raw_text, total_pages = extract_pdf_text(uploaded_file)
    total_chars = len(raw_text)

    if total_chars < 100:
        st.error("❌ Unable to decode this PDF layer properly. Ensure it contains readable characters or clear digital scans.")
        st.stop()

    context = prepare_context(raw_text)
    st.sidebar.success(
        f"✅ Loaded {total_pages} pages | {total_chars:,} characters extracted"
    )

    if "OPENROUTER_API_KEY" not in st.secrets:
        st.error("OPENROUTER_API_KEY missing from Streamlit Secrets.")
        st.stop()

    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=st.secrets["OPENROUTER_API_KEY"],
    )

    left, right = st.columns([1.35, 1])

    # ==========================================================
    # NOTES GENERATOR
    # ==========================================================
    with left:
        st.subheader("📚 Structured Judgment Notes")

        if st.button(
            "⚖️ Generate Complete Notes",
            use_container_width=True,
        ):
            with st.spinner("Reading judgment and extracting legal principles..."):
                prompt = dedent(f"""
You are a senior law professor and Supreme Court legal researcher.
Your ONLY source is the uploaded judgment text.

STRICT RULES
1. Never invent facts. If strings look like unreadable garbage symbols, ignore them completely.
2. Rely only on legible text. If substantive information cannot be determined due to encoding issues, write 'Not stated in the judgment.' under that field.
3. Extract ONLY what the Court actually decided from the legible segments.

==================================================
OUTPUT FORMAT

# 📌 CASE IDENTIFICATION
Case Name
Court
Bench
Year
Area of Law

--------------------------------------------------
# ⚖️ CORE DOCTRINE
Statutory Provisions
Core Legal Principle

--------------------------------------------------
# 🔍 MATERIAL FACTS
4–8 concise bullet points.
No procedural history.

--------------------------------------------------
# ❓ CORE LEGAL ISSUES
Maximum 4 issues as questions.

--------------------------------------------------
# ⚖️ COURT'S REASONING
Explain the reasoning in numbered steps (Maximum 8).

--------------------------------------------------
# 📚 RATIO DECIDENDI
State ONLY the core legal rule necessary for deciding this case.

--------------------------------------------------
# 💬 OBITER DICTA
Observations that were NOT necessary. If none, write "No significant obiter."

--------------------------------------------------
# 🏆 HOLDING
Who won and relief granted.

--------------------------------------------------
# 📖 IMPORTANT CASES CITED
Case Name -> Why it was cited

--------------------------------------------------
# 🎓 ACADEMIC SIGNIFICANCE
Why this case matters. Maximum 5 bullets.

--------------------------------------------------
# ⚡ 30 SECOND REVISION
Facts -> Issue -> Holding -> Ratio -> Important Sections -> Exam Keyword -> One-Line Memory Trick

==================================================
Judgment
--------------------------
{context}
""")

                try:
                    response = client.chat.completions.create(
                        model="openrouter/free",
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0.15,
                        max_tokens=2200,
                    )
                    notes = response.choices[0].message.content
                    st.markdown(notes)

                    st.download_button(
                        "⬇ Download Notes",
                        notes,
                        file_name="Judgment_Notes.md",
                        mime="text/markdown",
                        use_container_width=True,
                    )
                except Exception as e:
                    st.error(f"API Error: {e}")

    # ==========================================================
    # CHAT ASSISTANT
    # ==========================================================
    with right:
        st.subheader("💬 Legal Judgment Assistant")
        user_question = st.text_input("Ask a legal question")

        if user_question:
            with st.spinner("Analysing judgment..."):
                chat_prompt = dedent(f"""
Answer the user's question accurately and concisely using ONLY the text provided.
If the text consists of unreadable symbols or lacks context for the answer, state 'Not stated in the judgment.'

Judgment
{context}

User Question
{user_question}
""")
                try:
                    reply = client.chat.completions.create(
                        model="openrouter/free",
                        messages=[{"role": "user", "content": chat_prompt}],
                        temperature=0,
                        max_tokens=700,
                    )
                    st.success(reply.choices[0].message.content)
                except Exception as e:
                    st.error(f"API Error: {e}")

    with st.expander("📄 View Extracted Judgment Text"):
        st.text_area("Extracted Text", raw_text, height=500)

    st.divider()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Pages", total_pages)
    c2.metric("Characters", f"{len(raw_text):,}")
    c3.metric("Words", f"{len(raw_text.split()):,}")
    c4.metric("Parser", "Dynamic Text Map Cleanup")
else:
    st.info("👈 Upload a legal judgment PDF to begin.")
