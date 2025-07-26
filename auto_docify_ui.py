import streamlit as st
import tempfile
from pathlib import Path

# Core processing functions
from main import run_module1_on_file, run_module2_on_metadata

# Documentation exporter functions
from doc_exporter import export_to_markdown, export_to_word, load_metadata

# Indexing + chatbot functions
from index_and_chat import index_code_file, build_chatbot

# Ensure output directory exists
Path("output").mkdir(parents=True, exist_ok=True)

# -------------------------------
# Streamlit Page Setup
# -------------------------------
st.set_page_config(page_title="Auto Docufy", layout="centered")
st.title("📘 Auto Docufy: Auto-Documentation for Python Code")
st.markdown(
    """
    Upload a Python file to:
    - ✅ Extract metadata (functions, classes)
    - ✅ Auto-generate docstrings & README.md using LLM
    - ✅ Download Markdown & Word documentation
    - ✅ Chat interactively with the uploaded code
    """
)

# -------------------------------
# File Upload
# -------------------------------
uploaded_file = st.file_uploader("📂 Upload a Python file", type=["py"])

if uploaded_file:
    # Save uploaded file temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix=".py") as tmp_file:
        tmp_file.write(uploaded_file.read())
        temp_path = tmp_file.name

    st.success(f"✅ File uploaded: `{uploaded_file.name}`")

    # --------------------------------
    # Step 1: Scan + Parse File → Metadata
    # --------------------------------
    st.markdown("## 🔍 Step 1: Scan and Parse File")
    with st.spinner("🔄 Analyzing file and building initial metadata..."):
        metadata_file = Path("output") / f"{Path(uploaded_file.name).stem}_metadata.json"
        metadata = run_module1_on_file(temp_path, save_to=str(metadata_file))

    if metadata:
        st.success("✅ Metadata created successfully!")
        st.json(metadata, expanded=False)

        # --------------------------------
        # Step 2: Enrich with Docstrings + README
        # --------------------------------
        st.markdown("## ✨ Step 2: Enrich with Auto-Generated Docstrings & README")
        with st.spinner("🤖 Generating docstrings and README using LLM..."):
            enriched_file = Path("output") / f"{Path(uploaded_file.name).stem}_metadata_enriched.json"
            run_module2_on_metadata(metadata, str(enriched_file))

        st.success("✅ Enrichment complete!")

        # ✅ NEW: After enrichment, export Markdown + Word documentation
        with st.spinner("📄 Exporting documentation files..."):
            enriched_metadata = load_metadata(str(enriched_file))

            # Paths for docs
            base_name = Path(uploaded_file.name).stem
            markdown_file_path = Path("output") / f"{base_name}_docs.md"
            word_file_path = Path("output") / f"{base_name}_docs.docx"

            # Export documentation
            export_to_markdown(enriched_metadata, markdown_file_path)
            export_to_word(enriched_metadata, word_file_path)

        st.success("✅ Documentation exported (Markdown + Word)")

        # ✅ Download Enriched Metadata
        enriched_file_path = Path("output") / f"{Path(uploaded_file.name).stem}_metadata_enriched.json"
        if enriched_file_path.exists():
            with open(enriched_file_path, "r", encoding="utf-8") as ef:
                enriched_data = ef.read()
            st.download_button(
                label="📄 Download Enriched Metadata",
                data=enriched_data,
                file_name=f"{Path(uploaded_file.name).stem}_metadata_enriched.json",
                mime="application/json"
            )
        else:
            st.warning("⚠️ Enriched metadata file not found.")

        # ✅ Download README + Preview
        readme_path = Path("output/README_generated.md")
        if readme_path.exists():
            with open(readme_path, "r", encoding="utf-8") as rf:
                readme_data = rf.read()
            st.download_button(
                label="📘 Download Generated README",
                data=readme_data,
                file_name="README_generated.md",
                mime="text/markdown"
            )
            st.markdown("## 🧠 README Preview")
            st.code(readme_data, language="markdown")
        else:
            st.warning("⚠️ README file was not generated. Please check enrichment logic.")

        # ✅ Download Final Documentation (Markdown + Word)
        st.markdown("## 📦 Download Final Documentation Files")
        if markdown_file_path.exists():
            with open(markdown_file_path, "r", encoding="utf-8") as f:
                markdown_data = f.read()
            st.download_button(
                label="📝 Download Markdown Documentation",
                data=markdown_data,
                file_name=markdown_file_path.name,
                mime="text/markdown"
            )
        else:
            st.warning("⚠️ Markdown documentation file not found.")

        if word_file_path.exists():
            with open(word_file_path, "rb") as f:
                word_data = f.read()
            st.download_button(
                label="📄 Download Word Documentation",
                data=word_data,
                file_name=word_file_path.name,
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
        else:
            st.warning("⚠️ Word documentation file not found.")

        # --------------------------------
        # Step 3: Chatbot Section
        # --------------------------------
        st.markdown("## 💬 Chat with the Uploaded Code")

        # Index both code + enriched metadata into Chroma
        with st.spinner("🔄 Indexing code + metadata for chatbot..."):
            persist_dir = f"output/vector_db/{Path(uploaded_file.name).stem}"
            index_code_file(
                file_path=temp_path,
                metadata_path=str(enriched_file_path),
                persist_dir=persist_dir
            )

        try:
            # Build chatbot using the indexed data
            qa_bot = build_chatbot(model="mistral", persist_dir=persist_dir)

            st.markdown("### 💬 Ask questions about the uploaded code")
            user_query = st.text_input("Type your question:")

            if user_query:
                with st.spinner("🤖 Thinking..."):
                    bot_response = qa_bot(user_query)
                    st.markdown("**🤖 Bot Response:**")
                    st.write(bot_response)

        except FileNotFoundError as e:
            st.error(str(e))
        except Exception as e:
            st.error(f"⚠️ Chatbot failed to respond: {e}")

    else:
        st.error("❌ Failed to analyze the uploaded file. Ensure it's a valid Python script with functions or classes.")

else:
    st.info("ℹ️ Please upload a `.py` file to begin.")
