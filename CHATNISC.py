import streamlit as st
import pdfplumber
import pypdfium2 as pdfium
from openai import OpenAI

st.set_page_config(page_title="Nischal's Chat Bot", page_icon="⚖️", layout="wide")

st.title("⚖️ Nischal's Chat Bot (RAG Enabled)")
st.write("Cross-referencing legal judgments against your NLSIU Contracts II & Property Law benchmarks.")

# Simulated Knowledge Base Embeddings (Extracted Core Frameworks from your Course Notes)
COURSE_NOTES_KNOWLEDGE = {
    "contracts_ii": (
        "Prof. Ragini Surana Course Notes Standards:\n"
        "- Focuses heavily on the Law of Unjust Enrichment, restitutionary remedies, and obligations outside traditional contract barriers.\n"
        "- Emphasizes legal capacity thresholds (e.g., critical readings of Section 11 and Mohori Bibee void ab initio doctrines vs. practical digital realities).\n"
        "- Prioritizes statutory interpretation of specific indemnity, guarantee, bailment, pledge, and agency provisions under the ICA."
    ),
    "property_law": (
        "Prof. Karthik Suresh Course Notes Standards:\n"
        "- Theoretical frameworks of property rights, conceptions of justice, and distributive mechanisms under the TP Act, 1882.\n"
        "- Focuses on modes of transfer: specific mechanics of Sale, Mortgage, Lease, Exchange, and Gifts.\n"
        "- Emphasizes constitutional history (balancing private property vs. public interest), RERA 2016 consumer interpretations, and the Indian Easements Act."
    )
}

# Sidebar for file uploads
with st.sidebar:
    st.header("Upload Center")
    uploaded_file = st.file_uploader("Upload Case Judgment (PDF)", type="pdf")
    
    st.header("RAG Context Engine")
    selected_module = st.selectbox(
        "Select Course Benchmark Alignment:",
        ["None (Standard Analysis)", "Contracts II (Prof. Ragini Surana)", "Property Law (Prof. Karthik Suresh)"]
    )

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
        st.sidebar.success(f"Loaded {total_pages} pages ({total_chars} characters)!")

    if "OPENROUTER_API_KEY" not in st.secrets:
        st.error("Missing OPENROUTER_API_KEY in Streamlit Secrets.")
    else:
        client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=st.secrets["OPENROUTER_API_KEY"],
        )

        # Retrieve mapped RAG anchor context based on selection
        rag_context = ""
        if "Contracts II" in selected_module:
            rag_context = COURSE_NOTES_KNOWLEDGE["contracts_ii"]
        elif "Property Law" in selected_module:
            rag_context = COURSE_NOTES_KNOWLEDGE["property_law"]

        if total_chars > 25000:
            optimized_context = raw_text[:18000] + "\n\n[...]\n\n" + raw_text[-7000:]
        else:
            optimized_context = raw_text

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("📋 FIRAC EXTRACTION")
            if st.button("✨ Generate Benchmarked Notes"):
                with st.spinner("Executing RAG synthesis..."):
                    full_prompt = (
                        "You are an expert Indian legal analyst. Analyze the court judgment segments below and synthesize them into a clean, unified breakdown matching this exact, uniform format rule. Do not add random prose outside these headers:\n\n"
                        "## 📋 CORE LEGAL ISSUES\nState cleanly and precisely the core questions of law the court had to resolve.\n\n"
                        "## 🔍 MATERIAL FACTS\nProvide a highly concise, text-bounded paragraph of only the critical, essential facts necessary to understand the cause of action.\n\n"
                        "## ⚖️ RATIO DECIDENDI & JURISPRUDENTIAL LOGIC\nProvide a detailed, highly comprehensive analysis here. Thoroughly explain the legal principles, judicial logic, and any specific legal tests or statutory provisions applied by the court.\n\n"
                        "## 📚 COURSE NOTE BENCHMARK ALIGNMENT\nUsing the course note metrics provided below, map out exactly how this judgment aligns with, expands upon, or critiques the specific doctrines or academic frameworks taught in class.\n\n"
                        "## 🚀 INSTANT SNAPSHOT\nProvide a clean, easy-to-read summary covering the absolute essence of the Fact, Issue, and Ratio in a few punchy sentences.\n\n"
                        f"Course Note Benchmarks:\n{rag_context}\n\n"
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
            st.subheader("💬 BENCHMARKED CONSULTATION")
            user_question = st.text_input("Query arguments or verify specific sections against class benchmarks...")
            
            if user_question:
                with st.spinner("Evaluating against notes..."):
                    chat_prompt = (
                        "You are an expert AI Legal Consultant. Answer the user's question accurately, directly, and concisely, framing your explanation through the lens of the provided academic course benchmarks.\n\n"
                        f"Course Benchmarks:\n{rag_context}\n\n"
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
