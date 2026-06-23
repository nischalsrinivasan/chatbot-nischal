import streamlit as st
import pdfplumber
from openai import OpenAI

st.set_page_config(page_title="Nischal's Chat Bot", page_icon="⚖️", layout="wide")

st.title("⚖️ Nischal's Chat Bot")
st.write("Analyze massive 100+ page judgments, extract crisp summaries, and consult with an uncaged legal AI assistant.")

# Sidebar for file uploads
with st.sidebar:
    st.header("Upload Center")
    uploaded_file = st.file_uploader("Upload Case Judgment (PDF)", type="pdf")

if uploaded_file:
    raw_text = ""
    with pdfplumber.open(uploaded_file) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                raw_text += text + "\n"
                
    total_chars = len(raw_text)
    st.sidebar.success(f"Successfully loaded {len(pdf.pages)} pages ({total_chars} characters)!")

    if "OPENROUTER_API_KEY" not in st.secrets:
        st.error("Missing configuration: Please add your OPENROUTER_API_KEY to your Streamlit App Secrets.")
    else:
        client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=st.secrets["OPENROUTER_API_KEY"],
        )

        # Smart structural context extraction for 100+ page cases
        if total_chars > 160000:
            optimized_context = raw_text[:120000] + "\n\n[... DOCUMENT TRUNCATED FOR CONTEXT OPTIMIZATION ...]\n\n" + raw_text[-40000:]
        else:
            optimized_context = raw_text

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("📋 FIRAC")
            if st.button("✨ Extract Facts, Issues & Ratio"):
                if len(raw_text.strip()) == 0:
                    st.warning("Cannot analyze an empty text extraction.")
                else:
                    with st.spinner("Processing deep case structure..."):
                        full_prompt = (
                            "You are an expert Indian legal analyst. Analyze the provided court judgment text segments and provide a structured breakdown strictly adhering to these length constraints:\n\n"
                            "1. MATERIAL FACTS: Keep this highly concise. Extract only the critical, essential facts necessary to understand the cause of action. Skip any background or administrative filler.\n"
                            "2. KEY LEGAL ISSUES: State these cleanly and precisely. Highlight only the core legal questions the court had to resolve, without long-winded setup text.\n"
                            "3. RATIO DECIDENDI: Provide a highly detailed, comprehensive analysis here. Thoroughly explain the legal principles, judicial logic, and any legal tests used by the court to reach its decision. Do not cut this part short.\n\n"
                            "4. 🚀 INSTANT SNAPSHOT: At the very end, provide a clean, easy-to-read, and crisp summary covering the absolute core of the Fact, Issue, and Ratio in a few punchy sentences. Make it simple and clear to digest immediately.\n\n"
                            f"Case text segments:\n\n{optimized_context}"
                        )
                        
                        try:
                            response = client.chat.completions.create(
                                model="google/gemini-2.5-flash",
                                messages=[{"role": "user", "content": full_prompt}],
                                max_tokens=3000
                            )
                            st.write(response.choices[0].message.content)
                        except Exception as e:
                            st.error(f"❌ API Error: {str(e)}")

        with col2:
            st.subheader("💬 ASK ANYTHING")
            user_question = st.text_input("Ask a question, analyze an argument, or request cross-verifications...")
            
            if user_question and len(raw_text.strip()) > 0:
                with st.spinner("Evaluating across the judgment..."):
                    chat_prompt = (
                        "You are an expert AI Legal Consultant. Answer the user's question accurately, directly, and concisely. "
                        "Give a straight, to-the-point answer followed by a very short, clear explanation. Avoid long-winded essay structures.\n\n"
                        f"Primary Case Reference Segments:\n{optimized_context}\n\n"
                        f"User Query: {user_question}"
                    )
                    
                    try:
                        chat_response = client.chat.completions.create(
                            model="google/gemini-2.5-flash",
                            messages=[{"role": "user", "content": chat_prompt}],
                            max_tokens=600
                        )
                        st.info(chat_response.choices[0].message.content)
                    except Exception as inner_e:
                        st.error(f"❌ API Error: {str(inner_e)}")
else:
    st.info("👈 Please upload a legal PDF in the sidebar to get started!")
