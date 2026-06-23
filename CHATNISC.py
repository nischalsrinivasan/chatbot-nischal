import streamlit as st
from pypdf import PdfReader
import google.generativeai as genai

st.set_page_config(page_title="Nischal's Chat Bot", page_icon="⚖️", layout="wide")

st.title("⚖️ Nischal's Chat Bot")
st.write("Analyze case PDFs to extract FIRAC summary points and chat with the judgment using Google Gemini.")

# Sidebar for file uploads
with st.sidebar:
    st.header("Upload Center")
    uploaded_file = st.file_uploader("Upload Case Judgment (PDF)", type="pdf")

if uploaded_file:
    reader = PdfReader(uploaded_file)
    raw_text = ""
    for page in reader.pages:
        text = page.extract_text()
        if text:
            raw_text += text
        
    st.sidebar.success(f"Successfully loaded {len(reader.pages)} pages!")

    if "GEMINI_API_KEY" not in st.secrets:
        st.error("Missing configuration: Please add your GEMINI_API_KEY to your Streamlit App Secrets.")
    else:
        # Configuring the core library block
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("📋 Core FIRAC Brief")
            if st.button("✨ Extract Facts, Issues & Ratio"):
                with st.spinner("Gemini is analyzing the judgment..."):
                    short_text = raw_text[:30000]
                    
                    full_prompt = (
                        "You are an expert Indian legal analyst. Analyze the provided court judgment text and precisely extract: "
                        "1. Material Facts, 2. Key Legal Issues, 3. Ratio Decidendi. Rely strictly on the text provided.\n\n"
                        f"Case text:\n\n{short_text}"
                    )
                    
                    try:
                        # Fixed target string to active 2.5 architecture
                        model = genai.GenerativeModel('gemini-2.5-flash')
                        response = model.generate_content(full_prompt)
                        st.write(response.text)
                    except Exception as e:
                        st.error(f"❌ Gemini API Error: {str(e)}")

        with col2:
            st.subheader("💬 Ask Anything About This Case")
            user_question = st.text_input("Ask a specific question...")
            
            if user_question:
                with st.spinner("Searching document..."):
                    short_text = raw_text[:30000]
                    chat_prompt = (
                        f"Answer the user's question using ONLY the following case text. If the answer is not mentioned, say 'I cannot find that in the judgment.'\n\n"
                        f"Case Text:\n{short_text}\n\n"
                        f"Question: {user_question}"
                    )
                    
                    try:
                        model = genai.GenerativeModel('gemini-2.5-flash')
                        chat_response = model.generate_content(chat_prompt)
                        st.info(chat_response.text)
                    except Exception as inner_e:
                        st.error(f"❌ Gemini API Error: {str(inner_e)}")
else:
    st.info("👈 Please upload a legal PDF in the sidebar to get started!")
