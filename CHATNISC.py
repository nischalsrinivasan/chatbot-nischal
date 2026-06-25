import streamlit as st
import pdfplumber
import pypdfium2 as pdfium
from openai import OpenAI

st.set_page_config(page_title="Nischal's Chat Bot", page_icon="⚖️", layout="wide")

st.title("⚖️ Nischal's Chat Bot")
st.write("Analyze judgments and generate structured notes matching your exact law note benchmarks.")

# Sidebar for file uploads
with st.sidebar:
    st.header("Upload Center")
    uploaded_file = st.file_uploader("Upload Case Judgment (PDF)", type="pdf")

if uploaded_file:
    raw_text = ""
    total_pages = 0
    
    with pdfplumber.open(uploaded_file) as pdf:
        total_pages = len(pdf.pages)
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                raw_text += text + "\n"
                
    if len(raw_text.strip()) < 100:
        st.sidebar.warning("⚠️ Scrambled layout detected. Running fallback parser...")
        raw_text = ""
        uploaded_file.seek(0)
        doc = pdfium.PdfDocument(uploaded_file.read())
        total_pages = len(doc)
        for page in doc:
            textpage = page.get_textpage()
            text = textpage.get_text_bounded()
            if text:
                raw_text += text + "\n"

    total_chars = len(raw_text)
    if total_chars < 50:
        st.sidebar.error("❌ Document is unreadable.")
    else:
        st.sidebar.success(f"Successfully loaded {total_pages} pages ({total_chars} characters)!")

    if "OPENROUTER_API_KEY" not in st.secrets:
        st.error("Missing OPENROUTER_API_KEY in Streamlit Secrets.")
    else:
        client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=st.secrets["OPENROUTER_API_KEY"],
        )

        if total_chars > 25000:
            optimized_context = raw_text[:18000] + "\n\n[...]\n\n" + raw_text[-7000:]
        else:
            optimized_context = raw_text

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("📋 STRUCTURED EXTRACTION")
            if st.button("✨ Generate Notes"):
                with st.spinner("Structuring notes to your exact blueprint..."):
                    full_prompt = (
                        "You are an expert Indian legal analyst. Analyze the court judgment text segments provided below and convert them into a student's highly structured, clean law notes style. "
                        "Match the exact formatting blueprint found in top-tier law notes (hierarchical, bulleted, bolded sections, zero fluff). "
                        "Organize the output strictly using this precise structure:\n\n"
                        "### 📌 [TOPIC / CORE DOCTRINE COVERED]\n"
                        "- **Statutory Provisions**: [List specific Sections of the Indian Contract Act or Sale of Goods Act or Transfer of Property Act invoked, e.g., Section 124 / Section 54]\n"
                        "- **Core Principle**: [Provide a direct, 1-2 sentence definition of the legal rule or doctrine established in this judgment]\n\n"
                        "### ⚖️ CASE ANALYSIS: [Case Name]\n"
                        "- **Fact Blueprint**: [A single, highly condensed bullet point summarizing only the material facts that triggered the cause of action. Absolutely no administrative history.]\n"
                        "- **Core Question**: [The explicit legal issue or question of law phrased as a direct question]\n"
                        "- **Judicial Test & Logic**:\n"
                        "  - [First step of the court's reasoning / interpretation of the statutory provision]\n"
                        "  - [Specific test or standard laid down by the judges, using bolding for key legal terms]\n"
                        "  - [Final conclusion and how the rule applies to these specific facts]\n\n"
                        "### 📚 CLASS ROOM NUANCE & CRITIQUE\n"
                        "- [Provide a crisp, analytical bullet point detailing the academic critique, legal fiction, or broader impact of this ruling on the underlying statutory application]\n\n"
                        "### 🚀 INSTANT SNAPSHOT\n"
                        "- **Facts**: [1 sentence summary]\n"
                        "- **Issue**: [1 sentence summary]\n"
                        "- **Ratio**: [1 sentence summary]\n\n"
                        f"Case Text Segments:\n\n{optimized_context}"
                    )
                    try:
                        response = client.chat.completions.create(
                            model="openrouter/free",
                            messages=[{"role": "user", "content": full_prompt}],
                            max_tokens=1200
                        )
                        st.markdown(response.choices[0].message.content)
                    except Exception as e:
                        st.error(f"❌ API Error: {str(e)}")

        with col2:
            st.subheader("💬 CHAT ASSISTANT")
            user_question = st.text_input("Ask a question, query arguments, or verify specific sections...")
            
            if user_question:
                with st.spinner("Evaluating..."):
                    chat_prompt = (
                        "You are an expert AI Legal Consultant. Answer the user's question accurately, directly, and concisely. "
                        "Give a straight, to-the-point answer followed by a very short, clear explanation. Do not use long-winded essay blocks.\n\n"
                        f"Case Material:\n{optimized_context}\n\n"
                        f"User Query: {user_question}"
                    )
                    try:
                        chat_response = client.chat.completions.create(
                            model="openrouter/free",
                            messages=[{"role": "user", "content": chat_prompt}],
                            max_tokens=400
                        )
                        st.info(chat_response.choices[0].message.content)
                    except Exception as inner_e:
                        st.error(f"❌ API Error: {str(inner_e)}")
else:
    st.info("👈 Please upload a legal PDF to begin.")
