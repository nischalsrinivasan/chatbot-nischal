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
                            "You are an expert Indian legal analyst. Analyze the provided court judgment text segments and extract a highly relevant legal brief. "
                            "CRITICAL INSTRUCTION: Ignore all procedural fluff, boilerplate text, lists of advocate names, and administrative history. "
                            "Filter out the noise and focus strictly on substantive legal elements:\n\n"
                            "1. MATERIAL FACTS: Extract only the critical, legally impactful facts that directly gave rise to the cause of action and influenced the final decision. Leave out minor background dates or structural filler.\n"
                            "2. KEY LEGAL ISSUES: Identify only the core questions of law that the court was required to answer to resolve the dispute.\n"
                            "3. RATIO DECIDENDI: Isolate the exact legal principle, doctrine, or rule of law derived from the material facts that forms the binding precedent of the judgment.\n\n"
                            "At the very end, add a distinct section titled '🚀 INSTANT SNAPSHOT' containing a crisp, one-sentence absolute summary for each: Fact, Issue, and Ratio, ensuring all material elements are covered cleanly without unnecessary words.\n\n"
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
                        "You are an expert AI Legal Consultant. Use the provided case text segments below as your primary baseline authority. "
                        "If the user asks questions extending beyond the text, or queries general legal concepts, doctrines, "
                        "or case strategy, deploy your entire legal knowledge base and brain to thoroughly answer and assist them.\n"
                        "Provide a complete, detailed response without truncation.\n\n"
                        f"Primary Case Reference Segments:\n{optimized_context}\n\n"
                        f"User Query: {user_question}"
                    )
                    
                    try:
                        chat_response = client.chat.completions.create(
                            model="google/gemini-2.5-flash",
                            messages=[{"role": "user", "content": chat_prompt}],
                            max_tokens=2500
                        )
                        st.info(chat_response.choices[0].message.content)
                    except Exception as inner_e:
                        st.error(f"❌ API Error: {str(inner_e)}")
else:
    st.info("👈 Please upload a legal PDF in the sidebar to get started!")
