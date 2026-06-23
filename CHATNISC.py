import streamlit as st
import pdfplumber
from openai import OpenAI

st.set_page_config(page_title="Nischal's Chat Bot", page_icon="⚖️", layout="wide")

st.title("⚖️ Nischal's Chat Bot")
st.write("Analyze case PDFs to extract FIRAC summary points and chat with the judgment completely for free.")

# Sidebar for file uploads
with st.sidebar:
    st.header("Upload Center")
    uploaded_file = st.file_uploader("Upload Case Judgment (PDF)", type="pdf")

if uploaded_file:
    raw_text = ""
    # Open the PDF using pdfplumber to bypass scrambled fonts and layout bugs
    with pdfplumber.open(uploaded_file) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                raw_text += text + "\n"
                
    if len(raw_text.strip()) == 0:
        st.sidebar.error("⚠️ This PDF appears to be a raw image scan. Text extraction returned nothing.")
    else:
        st.sidebar.success(f"Successfully loaded document text!")

    if "OPENROUTER_API_KEY" not in st.secrets:
        st.error("Missing configuration: Please add your OPENROUTER_API_KEY to your Streamlit App Secrets.")
    else:
        client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=st.secrets["OPENROUTER_API_KEY"],
        )

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("📋 Core FIRAC Brief")
            if st.button("✨ Extract Facts, Issues & Ratio"):
                if len(raw_text.strip()) == 0:
                    st.warning("Cannot analyze an empty text extraction.")
                else:
                    with st.spinner("Analyzing the judgment..."):
                        short_text = raw_text[:12000]
                        
                        full_prompt = (
                            "You are an expert Indian legal analyst. Analyze the provided court judgment text and precisely extract: "
                            "1. Material Facts, 2. Key Legal Issues, 3. Ratio Decidendi. Rely strictly on the text provided.\n\n"
                            f"Case text:\n\n{short_text}"
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
            st.subheader("💬 Ask Anything About This Case")
            user_question = st.text_input("Ask a specific question...")
            
            if user_question and len(raw_text.strip()) > 0:
                with st.spinner("Searching document..."):
                    short_text = raw_text[:12000]
                    chat_prompt = (
                        f"Answer the user's question using ONLY the following case text. If the answer is not mentioned, say 'I cannot find that in the judgment.'\n\n"
                        f"Case Text:\n{short_text}\n\n"
                        f"Question: {user_question}"
                    )
                    
                    try:
                        chat_response = client.chat.completions.create(
                            model="openrouter/free",
                            messages=[{"role": "user", "content": chat_prompt}],
                            max_tokens=800
                        )
                        st.info(chat_response.choices[0].message.content)
                    except Exception as inner_e:
                        st.error(f"❌ API Error: {str(inner_e)}")
else:
    st.info("👈 Please upload a legal PDF in the sidebar to get started!")
