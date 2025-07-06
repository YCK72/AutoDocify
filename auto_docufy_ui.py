# auto_docufy_ui.py

import streamlit as st
import tempfile
import json
from pathlib import Path

from main import run_module1_on_file, run_module2_on_metadata
from index_and_chat import index_code_file, build_chatbot

# Ensure output directory exists
Path("output").mkdir(parents=True, exist_ok=True)

# Streamlit setup
st.set_page_config(page_title="Auto Docufy", layout="centered")
st.title("📘 Auto Docufy: Auto-Documentation for Python Code")
st.markdown("Upload a Python file to automatically generate docstrings, metadata, and a README file using LLMs.")

# File upload
uploaded_file = st.file_uploader("📂 Upload a Python file", type=["py"])

if uploaded_file:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".py") as tmp_file:
        tmp_file.write(uploaded_file.read())
        temp_path = tmp_file.name

    st.success(f"File uploaded: `{uploaded_file.name}`")

    st.markdown("## 🔍 Step 1: Scan and Parse File")
    with st.spinner("Analyzing file and building initial metadata..."):
        metadata_file = Path("output") / f"{Path(uploaded_file.name).stem}_metadata.json"
        metadata = run_module1_on_file(temp_path, save_to=str(metadata_file))

    if metadata:
        st.success("Metadata created successfully!")
        st.json(metadata, expanded=False)

        st.markdown("## ✨ Step 2: Enrich with Auto-Generated Docstrings")
        with st.spinner("Generating docstrings and README using LLM..."):
            enriched_file = Path("output") / f"{Path(uploaded_file.name).stem}_metadata_enriched.json"
            run_module2_on_metadata(metadata, str(enriched_file))

        st.success("Enrichment complete!")

        # Download Enriched Metadata
        try:
            with open(enriched_file, "r", encoding="utf-8") as ef:
                enriched_data = ef.read()
            st.download_button(
                label="📄 Download Enriched Metadata",
                data=enriched_data,
                file_name=f"{Path(uploaded_file.name).stem}_metadata_enriched.json",
                mime="application/json"
            )
        except FileNotFoundError:
            st.warning("Enriched metadata file not found.")

        # Download README + Preview
        try:
            with open("output/README_generated.md", "r", encoding="utf-8") as rf:
                readme_data = rf.read()
            st.download_button(
                label="📘 Download Generated README",
                data=readme_data,
                file_name="README_generated.md",
                mime="text/markdown"
            )
            st.markdown("## 🧠 README Preview")
            st.code(readme_data, language="markdown")
        except FileNotFoundError:
            st.warning("README file was not generated. Please check your LLM output or enrichment logic.")

        # ✅ Step 3: Chatbot Section
        st.markdown("## 💬 Chat with the Uploaded Code")
        with st.spinner("Indexing code for chatbot..."):
            index_code_file(temp_path)

        qa_bot = build_chatbot()

        user_input = st.text_input("Ask a question about the code:")
        if user_input:
            with st.spinner("Thinking..."):
                response = qa_bot(user_input)
                st.markdown("**🤖 Bot Response:**")
                st.write(response["result"])

    else:
        st.error("Failed to analyze the uploaded file. Ensure it's a valid Python script with functions or classes.")

else:
    st.info("Please upload a `.py` file to begin.")
