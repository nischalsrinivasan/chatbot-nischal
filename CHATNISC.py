import streamlit as st
from pypdf import PdfReader
from openai import OpenAI

st.set_page_config(page_title="Nischal's Chat Bot", page_icon="⚖️", layout="wide")

st.title("⚖️ Nischal's Chat Bot")
st.write("Analyze case PDFs to extract FIRAC summary points and chat with the judgment.")

# 1. Sidebar for file uploads
with st.sidebar:
    st.header("Upload Center")
    uploaded_file = st.file_uploader("Upload Case Judgment (PDF)", type="pdf")

if uploaded_file:
    # Read text from PDF instantly
    reader = PdfReader(uploaded_file)
    raw_text = ""
    for page in reader.pages:
        text = page.extract_text()
        if text:
            raw_text += text
        
    st.sidebar.success(f"Successfully loaded {len(reader.pages)} pages!")

    # Check if we have an API Key configured in Streamlit secrets
    if "OPENAI_API_KEY" not in st.secrets:
        st.error("Please add your OPENAI_API_KEY to your Streamlit App Secrets to use the AI features.")
    else:
        # Initialize OpenAI client using secure secrets
        client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

        # Split screen into two columns: Left for quick summary, Right for open chat
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("📋 Core FIRAC Brief")
            if st.button("✨ Extract Facts, Issues & Ratio"):
                with st.spinner("Analyzing judgment structures..."):
                    response = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[
                            {"role": "system", "content": "You are an expert legal analyst. Analyze the provided court judgment text and precisely extract: 1. Material Facts, 2. Key Legal Issues, 3. Ratio Decidendi. Rely strictly on the text provided. Do not invent external information."},
                            {"role": "user", "content": f"Here is the case text:\n\n{raw_text[:40000]}"}
                        ]
                    )
                    st.write(response.choices[0].message.content)

        with col2:
            st.subheader("💬 Ask Anything About This Case")
            user_question = st.text_input("Ask a specific question (e.g., 'What were the arguments of the respondent?')")
            
            if user_question:
                with st.spinner("Searching document text..."):
                    chat_response = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[
                            {"role": "system", "content": f"You are a helpful legal assistant. Answer the user's question using ONLY the following case text. If the answer is not explicitly mentioned, say 'I cannot find that in the provided judgment text.'\n\nCase Text:\n{raw_text[:40000]}"},
                            {"role": "user", "content": user_question}
                        ]
                    )
                    st.info(chat_response.choices[0].message.content)
else:
    st.info("👈 Please upload a legal PDF in the sidebar to get started!")
