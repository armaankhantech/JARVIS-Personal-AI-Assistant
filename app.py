import json
import streamlit as st
from google import genai
from pypdf import PdfReader

st.set_page_config(page_title="AI Exam Prep Generator", layout="wide")

st.title("📚 AI Syllabus-to-Exam Prep Generator")
st.caption("TY BCA (Science) Final Year Demonstration Prototype")

# API Configuration
api_key = st.sidebar.text_input("Enter Gemini API Key", type="password")
uploaded_file = st.sidebar.file_uploader("Upload Chapter/Syllabus PDF", type=["pdf"])

def extract_text_from_pdf(pdf_file):
    reader = PdfReader(pdf_file)
    extracted_text = ""
    for page in reader.pages:
        text = page.extract_text()
        if text:
            extracted_text += text + "\n"
    return extracted_text

def generate_exam_prep_content(text, api_key):
    client = genai.Client(api_key=api_key)
    
    prompt = f"""
    You are an expert examiner. Analyze the following study text and generate structured JSON containing:
    1. "mcqs": A list of 10 objects, each having "question", "options" (list of 4 strings), and "answer" (exact option text).
    2. "flashcards": A list of 5 objects, each having "question" and "answer".
    3. "cheatsheet": A string formatted in clean Markdown summarizing the top 5 essential exam topics and formulas.

    Return ONLY raw valid JSON without markdown wrapping or code blocks.

    Study Text:
    {text[:8000]}
    """
    
    response = client.models.generate_content(
        model="gemini-3.5-flash-lite",
        contents=prompt
    )
    
    clean_json_str = response.text.replace("```json", "").replace("```", "").strip()
    return json.loads(clean_json_str)

if uploaded_file and api_key:
    if st.sidebar.button("Generate Exam Kit 🚀"):
        with st.spinner("Extracting PDF text & generating questions with Gemini..."):
            try:
                raw_text = extract_text_from_pdf(uploaded_file)
                data = generate_exam_prep_content(raw_text, api_key)
                st.session_state["prep_data"] = data
                st.success("Exam Kit Generated Successfully!")
            except Exception as e:
                st.error(f"Error processing document: {e}")

if "prep_data" in st.session_state:
    data = st.session_state["prep_data"]
    tab1, tab2, tab3 = st.tabs(["📝 10-Question Quiz", "🎴 5 Revision Flashcards", "📌 Important Cheatsheet"])
    
    # TAB 1: MCQs
    with tab1:
        st.subheader("Interactive Multiple Choice Questions")
        score = 0
        for i, q in enumerate(data.get("mcqs", [])):
            st.markdown(f"**Q{i+1}: {q['question']}**")
            user_choice = st.radio("Options:", q["options"], key=f"mcq_{i}")
            if user_choice == q["answer"]:
                st.success("Correct!")
                score += 1
            else:
                st.info(f"Correct Answer: {q['answer']}")
            st.divider()
        st.metric("Final Score", f"{score} / {len(data.get('mcqs', []))}")

    # TAB 2: Flashcards
    with tab2:
        st.subheader("Interactive Revision Flashcards")
        for i, card in enumerate(data.get("flashcards", [])):
            with st.expander(f"🎴 Card {i+1}: {card['question']}"):
                st.write(f"Answer:")

    # TAB 3: Cheatsheet
    with tab3:
        st.subheader("Summary Cheatsheet")
        cheatsheet_text = data.get("cheatsheet", "")
        st.markdown(cheatsheet_text)
        
        st.download_button(
            label="💾 Download Cheatsheet (.txt)",
            data=cheatsheet_text,
            file_name="Exam_Important_Topics.txt",
            mime="text/plain"
        )
else:
    st.info("👈 Enter your Gemini API key and upload a syllabus PDF in the sidebar to begin.")