import streamlit as st
import pdfplumber
import pypdfium2 as pdfium
from openai import OpenAI

st.set_page_config(page_title="Nischal's Chat Bot", page_icon="⚖️", layout="wide")

st.title("⚖️ Nischal's Chat Bot")
st.write("Analyze judgments and generate notes matching your exact academic format standard.")

# Sidebar for file uploads
with st.sidebar:
    st.header("Upload Center")
    uploaded_file = st.file_uploader("Upload Case Judgment (PDF)", type="pdf")
    
    st.header("Course Context")
    selected_module = st.selectbox(
        "Select Subject Stream:",
        ["General Analysis", "Contracts II", "Property Law"]
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

        if total_chars > 25000:
            optimized_context = raw_text[:18000] + "\n\n[...]\n\n" + raw_text[-7000:]
        else:
            optimized_context = raw_text

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("📋 FIRAC EXTRACTION")
            if st.button("✨ Generate Notes"):
                with st.spinner("Structuring notes to standard..."):
                    full_prompt = (
                        "You are an expert Indian legal analyst. Analyze the court judgment text segments below and organize your output to perfectly match a student's highly structured, clean law notes style. Use clear bullet points and bolding for key doctrines or statutory provisions. Follow this format exactly:\n\n"
                        "## 📋 CORE LEGAL ISSUES\nState cleanly, numbered, and precisely the core legal questions the court had to resolve.\n\n"
                        "## 🔍 MATERIAL FACTS\nProvide a highly concise, text-bounded paragraph of only the critical, essential facts necessary to understand the cause of action. Skip any background filler.\n\n"
                        "## ⚖️ RATIO DECIDENDI\nProvide a detailed, highly comprehensive analysis here. Thoroughly explain the legal principles, judicial logic, specific legal tests, and statutory sections applied by the court. Break this down with clear sub-bullets for readability.\n\n"
                        "## 📚 CLASS NOTE SYNC\nProvide a crisp, direct summary of how this judgment relates to the core concepts, modules, or statutory rules of the chosen stream (Contracts II or Property Law).\n\n"
                        "## 🚀 INSTANT SNAPSHOT\nProvide a clean, easy-to-read summary covering the absolute core of the Fact, Issue, and Ratio in a few punchy sentences.\n\n"
                        f"Subject Stream Selected: {selected_module}\n"
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
                        f"Subject Stream Context: {selected_module}\n"
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
