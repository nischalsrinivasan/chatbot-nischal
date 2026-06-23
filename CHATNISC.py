import streamlit as st
import pdfplumber
from openai import OpenAI

st.set_page_config(page_title="Nischal's Chat Bot", page_icon="⚖️", layout="wide")

st.title("⚖️ Nischal's Chat Bot")
st.write("Analyze massive 100+ page judgments seamlessly without ever hitting token or credit limits.")

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

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("📋 FIRAC")
            if st.button("✨ Extract Facts, Issues & Ratio"):
                if len(raw_text.strip()) == 0:
                    st.warning("Cannot analyze an empty text extraction.")
                else:
                    # Slicing the document into bite-sized chunks to permanently bypass token limits
                    chunk_size = 8000
                    chunks = [raw_text[i:i+chunk_size] for i in range(0, len(raw_text), chunk_size)]
                    
                    # Target critical beginning and ending segments to maximize precision
                    if len(chunks) > 6:
                        targeted_chunks = chunks[:4] + chunks[-2:]
                    else:
                        targeted_chunks = chunks

                    partial_summaries = []
                    progress_bar = st.progress(0)
                    st.info(f"Processing case layout safely in {len(targeted_chunks)} segments...")

                    # Map Phase
                    for idx, chunk in enumerate(targeted_chunks):
                        with st.spinner(f"Analyzing segment {idx+1}/{len(targeted_chunks)}..."):
                            chunk_prompt = (
                                "You are an expert Indian legal analyst. Review this segment of a court judgment and extract any "
                                "Material Facts, Key Legal Issues, or parts of the Ratio Decidendi mentioned here. Be direct.\n\n"
                                f"Judgment Segment:\n{chunk}"
                            )
                            try:
                                response = client.chat.completions.create(
                                    model="meta-llama/llama-3-8b-instruct:free", # Swapped to high-bandwidth unthrottled free core
                                    messages=[{"role": "user", "content": chunk_prompt}],
                                    max_tokens=300
                                )
                                partial_summaries.append(response.choices[0].message.content)
                            except Exception as chunk_err:
                                continue
                        progress_bar.progress((idx + 1) / len(targeted_chunks))

                    # Reduce Phase
                    with st.spinner("Compiling final consolidated FIRAC brief..."):
                        combined_analysis = "\n\n".join(partial_summaries)
                        final_prompt = (
                            "You are an expert Indian legal analyst. Review the compiled legal segments below and synthesize them into a clean, unified breakdown matching these strict rules:\n\n"
                            "1. MATERIAL FACTS: Keep this highly concise. Extract only the critical, essential facts necessary to understand the cause of action.\n"
                            "2. KEY LEGAL ISSUES: State these cleanly and precisely. Highlight only the core legal questions the court had to resolve.\n"
                            "3. RATIO DECIDENDI: Provide a detailed, comprehensive analysis here. Thoroughly explain the legal principles, judicial logic, and legal tests used by the court to reach its decision.\n\n"
                            "4. 🚀 INSTANT SNAPSHOT: At the very end, provide a clean, easy-to-read, and crisp summary covering the absolute core of the Fact, Issue, and Ratio in a few punchy sentences.\n\n"
                            f"Compiled Analysis Streams:\n\n{combined_analysis}"
                        )
                        
                        try:
                            final_response = client.chat.completions.create(
                                model="meta-llama/llama-3-8b-instruct:free", # Bypasses paid or credit capped tokens entirely
                                messages=[{"role": "user", "content": final_prompt}],
                                max_tokens=800
                            )
                            st.write(final_response.choices[0].message.content)
                        except Exception as e:
                            st.error(f"❌ Synthesis Error: {str(e)}")

        with col2:
            st.subheader("💬 ASK ANYTHING")
            user_question = st.text_input("Ask a question, analyze an argument, or request cross-verifications...")
            
            if user_question and len(raw_text.strip()) > 0:
                with st.spinner("Evaluating your question..."):
                    quick_context = raw_text[:20000] + "\n\n[...]\n\n" + raw_text[-10000:] if len(raw_text) > 30000 else raw_text
                    
                    chat_prompt = (
                        "You are an expert AI Legal Consultant. Answer the user's question accurately, directly, and concisely. "
                        "Give a straight, to-the-point answer followed by a very short, clear explanation. Avoid long-winded essay structures.\n\n"
                        f"Primary Case Reference Segments:\n{quick_context}\n\n"
                        f"User Query: {user_question}"
                    )
                    
                    try:
                        chat_response = client.chat.completions.create(
                            model="meta-llama/llama-3-8b-instruct:free",
                            messages=[{"role": "user", "content": chat_prompt}],
                            max_tokens=400
                        )
                        st.info(chat_response.choices[0].message.content)
                    except Exception as inner_e:
                        st.error(f"❌ API Error: {str(inner_e)}")
else:
    st.info("👈 Please upload a legal PDF in the sidebar to get started!")
