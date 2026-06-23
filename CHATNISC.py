import streamlit as st
import pdfplumber
import pypdfium2 as pdfium
from openai import OpenAI

st.set_page_config(page_title="Nischal's Chat Bot", page_icon="⚖️", layout="wide")

st.title("⚖️ Nischal's Chat Bot")
st.write("Stable, zero-cost analysis for any judgment PDF.")

# Sidebar for file uploads
with st.sidebar:
    st.header("Upload Center")
    uploaded_file = st.file_uploader("Upload Case Judgment (PDF)", type="pdf")

if uploaded_file:
    raw_text = ""
    total_pages = 0
    
    # 1. High-fidelity text layer read
    with pdfplumber.open(uploaded_file) as pdf:
        total_pages = len(pdf.pages)
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                raw_text += text + "\n"
                
    # 2. OCR Fallback for image scans / scrambled characters
    if len(raw_text.strip()) < 100:
        st.sidebar.warning("⚠️ Scrambled/Scanned layout detected. Parsing pixels...")
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

        # Secure packet sizing to guarantee free execution under heavy server load
        if total_chars > 25000:
            optimized_context = raw_text[:18000] + "\n\n[...]\n\n" + raw_text[-7000:]
        else:
            optimized_context = raw_text

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("📋 FIRAC")
            if st.button("✨ Extract Facts, Issues & Ratio"):
                with st.spinner("Compiling brief..."):
                    full_prompt = (
                        "You are an expert Indian legal analyst. Analyze the provided court judgment text segments and provide a structured breakdown strictly adhering to these constraints:\n\n"
                        "1. MATERIAL FACTS: Keep this highly concise. Extract only the critical, essential facts necessary to understand the cause of action. Skip background filler.\n"
                        "2. KEY LEGAL ISSUES: State these cleanly and precisely. Highlight only the core legal questions the court had to resolve.\n"
                        "3. RATIO DECIDENDI: Provide a detailed, comprehensive analysis here. Thoroughly explain the legal principles, judicial logic, and legal tests used by the court.\n\n"
                        "4. 🚀 INSTANT SNAPSHOT: At the very end, provide a clean, crisp summary covering the absolute core of the Fact, Issue, and Ratio in a few punchy sentences.\n\n"
                        f"Case text:\n\n{optimized_context}"
                    )
                    try:
                        response = client.chat.completions.create(
                            model="openrouter/free",
                            messages=[{"role": "user", "content": full_prompt}],
                            max_tokens=800
                        )
                        st.write(response.choices[0].message.content)
                    except Exception as e:
                        st.error(f"❌ API Error: {str(e)}")

        with col2:
            st.subheader("💬 ASK ANYTHING")
            user_question = st.text_input("Ask a question...")
            
            if user_question:
                with st.spinner("Evaluating..."):
                    chat_prompt = (
                        "You are an expert AI Legal Consultant. Answer the user's question accurately, directly, and concisely. "
                        "Give a straight, to-the-point answer followed by a very short, clear explanation.\n\n"
                        f"Primary Case Reference:\n{optimized_context}\n\n"
                        f"User Query: {user_question}"
                    )
                    try:
                        chat_response = client.chat.completions.create(
                            model="openrouter/free",
                            messages=[{"role": "user", "content": chat_prompt}],
                            max_tokens=300
                        )
                        st.info(chat_response.choices[0].message.content)
                    except Exception as inner_e:
                        st.error(f"❌ API Error: {str(inner_e)}")
else:
    st.info("👈 Please upload a legal PDF to begin.")
