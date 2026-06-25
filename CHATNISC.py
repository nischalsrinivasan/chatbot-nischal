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
    """Clean OCR text while preserving legal formatting."""
    if not text:
        return ""

    text = re.sub(r"\n{2,}", "\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"Page\s+\d+\s+of\s+\d+", "", text, flags=re.IGNORECASE)
    text = re.sub(r"About LexisNexis.*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"Copyright.*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\[\*\d+\]", "", text)
    return text.strip()


def extract_pdf_text(uploaded_file):
    """Extract text using pdfplumber first, then fallback to pdfium."""
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
    
    if len(raw_text) < 200:
        uploaded_file.seek(0)
        try:
            pdf = pdfium.PdfDocument(uploaded_file.read())
            total_pages = len(pdf)
            raw_text = ""

            for page in pdf:
                textpage = page.get_textpage()
                txt = textpage.get_text_bounded()
                if txt:
                    raw_text += txt + "\n"
        except Exception:
            pass

    raw_text = clean_text(raw_text)
    return raw_text, total_pages


def prepare_context(text, max_chars=55000):
    """
    Keeps an expanded beginning, middle, and end of long judgments.
    Optimized to capture core reasoning windows without choking the free tier.
    """
    if len(text) <= max_chars:
        return text

    # Capture initial pages for case metadata and background facts
    start = text[:20000]

    # Dynamically targets the middle 20,000 characters where main arguments sit
    middle_start = len(text) // 2 - 10000
    middle_end = len(text) // 2 + 10000
    middle = text[middle_start:middle_end]

    # Capture the final 15,000 characters for ratios and structural holdings
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
✅ Supreme Court
✅ High Courts
✅ UK Cases
✅ Privy Council
✅ Sale of Goods
✅ Contract
✅ Property
✅ Tort
✅ Constitutional Law
"""
    )

# ------------------------------
# Load PDF
# ------------------------------
if uploaded_file:
    raw_text, total_pages = extract_pdf_text(uploaded_file)
    total_chars = len(raw_text)

    if total_chars < 100:
        st.error("❌ Unable to read this PDF. Try a higher-quality scan.")
        st.stop()

    context = prepare_context(raw_text)
    st.sidebar.success(
        f"✅ Loaded {total_pages} pages | {total_chars:,} characters extracted"
    )

    # ------------------------------
    # OpenRouter Client
    # ------------------------------
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
Your ONLY source is the uploaded judgment.

STRICT RULES
1. Never invent facts.
2. Never invent statutory provisions.
3. Never invent constitutional issues.
4. Never use outside legal knowledge.
5. If something cannot be determined, write: 'Not stated in the judgment.'
6. Extract ONLY what the Court actually decided.
7. Ignore advocates, procedural history, citations, paragraph numbers, page numbers, publisher information, headers, footers.
8. Material Facts must contain ONLY legally relevant facts.
9. Ratio must contain ONLY the binding legal principle.
10. Do NOT explain general law. Explain ONLY the law applied by this Court.

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
Maximum 120 words.

--------------------------------------------------
# ❓ CORE LEGAL ISSUES
Maximum 4 issues.
Each written as a question.

--------------------------------------------------
# ⚖️ COURT'S REASONING
Explain the reasoning in numbered steps.
Include
• Interpretation of statutes
• Tests laid down
• Legal principles applied
• Application of facts
Maximum 8 bullets.

--------------------------------------------------
# 📚 RATIO DECIDENDI
State ONLY the legal rule necessary for deciding this case.
Do NOT repeat facts.
Do NOT summarise.
Maximum 220 words.
If there are multiple ratios, number them.

--------------------------------------------------
# 💬 OBITER DICTA
Mention only observations that were NOT necessary for deciding the dispute.
If none exist write: "No significant obiter."

--------------------------------------------------
# 🏆 HOLDING
Mention
• Who won
• Appeal allowed/dismissed
• Relief granted
Maximum 3 bullets.

--------------------------------------------------
# 📖 IMPORTANT CASES CITED
List ONLY cases actually relied upon.
For each case:
Case Name -> Why it was cited
Maximum 8.

--------------------------------------------------
# 🎓 ACADEMIC SIGNIFICANCE
Explain:
Why this case matters.
How it changed or clarified law.
Whether it expanded an earlier principle.
Maximum 5 bullets.

--------------------------------------------------
# ⚡ 30 SECOND REVISION
Facts -> Issue -> Holding -> Ratio -> Important Sections -> Exam Keyword -> One-Line Memory Trick

==================================================
REMEMBER
If information is absent write "Not stated in the judgment." DO NOT GUESS.

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
        st.caption(
            "Ask anything about the uploaded judgment.\n"
            "The assistant answers ONLY from the judgment."
        )

        user_question = st.text_input(
            "Ask a legal question",
            placeholder="Example: What is the ratio? Which sections were interpreted?"
        )

        if user_question:
            with st.spinner("Analysing judgment..."):
                chat_prompt = dedent(f"""
You are an expert legal AI.

STRICT RULES
• Answer ONLY from the uploaded judgment.
• Never invent facts.
• Never invent statutes.
• Never invent ratios.
• Never answer using general legal knowledge.
• If the judgment does not contain the answer, say "Not stated in the judgment."
• Quote short relevant extracts where useful.
• Keep answers concise.

--------------------------------------------------
Judgment
{context}

--------------------------------------------------
User Question
{user_question}

--------------------------------------------------
OUTPUT FORMAT
## Answer
Direct answer in 2-5 sentences.

## Explanation
Very short explanation.

## Supporting Material
Mention relevant: facts, section, paragraph (if available), reasoning. Only if found in the judgment.
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

    # ==========================================================
    # RAW TEXT
    # ==========================================================
    with st.expander("📄 View Extracted Judgment Text"):
        st.text_area(
            "Extracted Text",
            raw_text,
            height=500,
        )

    # ==========================================================
    # DOCUMENT STATISTICS
    # ==========================================================
    st.divider()
    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Pages", total_pages)
    c2.metric("Characters", f"{len(raw_text):,}")
    c3.metric("Words", f"{len(raw_text.split()):,}")

    parser_used = "OCR/Fallback" if total_chars < 5000 else "Text Extraction"
    c4.metric("Parser", parser_used)

else:
    st.info(
        """
👈 Upload a legal judgment PDF to begin.

Supported:
• Supreme Court
• High Courts
• UK Cases
• Privy Council
• Property Law
• Contract Law
• Sale of Goods
• Tort
• Constitutional Law

The AI will automatically generate:
✅ Material Facts
✅ Core Legal Issues
✅ Court's Reasoning
✅ Ratio Decidendi
✅ Holding
✅ Obiter Dicta
✅ Cases Cited
✅ Statutory Provisions
✅ Academic Significance
✅ 30-Second Revision Snapshot
"""
    )
