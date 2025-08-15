import os
import uuid
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
st.set_page_config(page_title="Auto Docufy", layout="wide")
st.title("📘 Auto Docufy: Auto-Documentation for Python Code")

st.markdown(
    """
**What you can do:**
- ✅ Create **multiple chats** (each chat is its own workspace)
- ✅ Upload a Python file **per chat**
- ✅ Extract metadata, auto-generate docstrings & README
- ✅ Download Markdown & Word docs
- ✅ **Chat continuously** with the code in that chat
    """
)

# ===============================
# Session State: Multi-chat store
# ===============================
if "chats" not in st.session_state:
    st.session_state["chats"] = {}  # chat_id -> state dict

if "selected_chat_id" not in st.session_state:
    # create a first empty chat
    cid = f"chat_{uuid.uuid4().hex[:8]}"
    st.session_state["chats"][cid] = {
        "name": "Chat 1",
        "history": [],                # list[(user, ai)]
        "file_temp_path": None,       # temp path of uploaded .py
        "file_name": None,            # original uploaded filename
        "base_name": None,            # stem of file
        "persist_dir": f"output/vector_db/{cid}",
        "metadata_path": None,        # output/<cid>_metadata.json
        "enriched_path": None,        # output/<cid>_metadata_enriched.json
        "markdown_path": None,        # output/<base>_docs.md
        "word_path": None,            # output/<base>_docs.docx
        "indexed": False,             # whether vector index exists
        "crc": None,                  # cached ConversationalRetrievalChain
    }
    st.session_state["selected_chat_id"] = cid


def _new_chat():
    cid = f"chat_{uuid.uuid4().hex[:8]}"
    name = f"Chat {len(st.session_state['chats']) + 1}"
    st.session_state["chats"][cid] = {
        "name": name,
        "history": [],
        "file_temp_path": None,
        "file_name": None,
        "base_name": None,
        "persist_dir": f"output/vector_db/{cid}",
        "metadata_path": None,
        "enriched_path": None,
        "markdown_path": None,
        "word_path": None,
        "indexed": False,
        "crc": None,
    }
    st.session_state["selected_chat_id"] = cid


def _delete_chat(cid: str):
    chats = st.session_state["chats"]
    if cid in chats:
        # Best-effort cleanup of vector dir (optional)
        # (We don't delete files on disk by default to avoid surprises.)
        del chats[cid]

    if not chats:
        _new_chat()
    else:
        # pick an arbitrary remaining chat
        st.session_state["selected_chat_id"] = next(iter(chats.keys()))


def _rename_chat(cid: str, new_name: str):
    if cid in st.session_state["chats"] and new_name.strip():
        st.session_state["chats"][cid]["name"] = new_name.strip()


def _reset_chat_file(cid: str):
    """Remove file-specific artifacts from a chat so the user can re-upload."""
    c = st.session_state["chats"][cid]
    c["file_temp_path"] = None
    c["file_name"] = None
    c["base_name"] = None
    c["metadata_path"] = None
    c["enriched_path"] = None
    c["markdown_path"] = None
    c["word_path"] = None
    c["indexed"] = False
    c["crc"] = None
    # Note: We intentionally do not delete any on-disk outputs automatically.


# ===============================
# Sidebar: Chat Manager
# ===============================
with st.sidebar:
    st.subheader("💼 Chat Manager")

    chats = st.session_state["chats"]
    chat_items = [(cid, chats[cid]["name"]) for cid in chats]
    # Keep a stable order:
    chat_items_sorted = sorted(chat_items, key=lambda x: x[1].lower())

    # Build display -> id mapping
    labels = [name for _, name in chat_items_sorted]
    ids = [cid for cid, _ in chat_items_sorted]

    # Determine current index
    current_id = st.session_state["selected_chat_id"]
    try:
        current_index = ids.index(current_id)
    except ValueError:
        current_index = 0
        st.session_state["selected_chat_id"] = ids[0]

    selected_index = st.selectbox("Chats", options=list(range(len(ids))), format_func=lambda i: labels[i], index=current_index)
    st.session_state["selected_chat_id"] = ids[selected_index]
    cid = st.session_state["selected_chat_id"]
    c = st.session_state["chats"][cid]

    # New / Rename / Delete
    cols = st.columns(2)
    if cols[0].button("➕ New Chat", use_container_width=True):
        _new_chat()
        st.rerun()

    if cols[1].button("🗑️ Delete Chat", use_container_width=True):
        _delete_chat(cid)
        st.rerun()

    new_name = st.text_input("Rename Chat", value=c["name"])
    if st.button("Save Name", type="primary"):
        _rename_chat(cid, new_name)
        st.rerun()

    st.markdown("---")
    if st.button("🧹 Clear Chat History"):
        c["history"] = []
        st.success("Chat history cleared.")


# ===============================
# Main area: Selected chat workspace
# ===============================
cid = st.session_state["selected_chat_id"]
c = st.session_state["chats"][cid]

st.markdown(f"### 🗂️ Workspace: **{c['name']}**")

# -------- Upload or replace file for THIS chat --------
if not c["file_name"]:
    st.info("No file uploaded in this chat yet. Upload a `.py` file to begin.")
    uploaded = st.file_uploader(f"📂 Upload a Python file for {c['name']}", type=["py"], key=f"uploader_{cid}")

    if uploaded:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".py") as tmp_file:
            tmp_file.write(uploaded.read())
            c["file_temp_path"] = tmp_file.name

        c["file_name"] = uploaded.name
        c["base_name"] = Path(uploaded.name).stem
        st.success(f"✅ File uploaded for {c['name']}: `{c['file_name']}`")

        # Prepare per-chat output paths (names include chat_id to avoid collisions)
        c["metadata_path"] = str(Path("output") / f"{cid}_metadata.json")
        c["enriched_path"] = str(Path("output") / f"{cid}_metadata_enriched.json")
        c["markdown_path"] = str(Path("output") / f"{c['base_name']}_docs.md")
        c["word_path"] = str(Path("output") / f"{c['base_name']}_docs.docx")

        st.rerun()
else:
    # Show current file info + Replace button
    st.success(f"📄 Current file in this chat: `{c['file_name']}`")
    if st.button("🔁 Replace File in This Chat"):
        _reset_chat_file(cid)
        st.rerun()

# -------- If we have a file, run the pipeline --------
if c["file_name"] and c["file_temp_path"]:
    # Step 1: Scan + Parse
    st.markdown("#### 🔍 Step 1: Scan and Parse File")
    try:
        with st.spinner("Analyzing file and building initial metadata..."):
            metadata = run_module1_on_file(c["file_temp_path"], save_to=c["metadata_path"])
        if metadata:
            st.success("✅ Metadata created successfully!")
            st.json(metadata, expanded=False)
        else:
            st.error("❌ Failed to analyze the uploaded file. Ensure it's a valid Python script.")
    except Exception as e:
        st.error("Metadata extraction failed.")
        st.exception(e)

    # Step 2: Enrich + README
    st.markdown("#### ✨ Step 2: Enrich with Auto-Generated Docstrings & README")
    try:
        with st.spinner("Generating docstrings and README using LLM..."):
            # Only run if we had metadata
            if Path(c["metadata_path"]).exists():
                run_module2_on_metadata(load_metadata(c["metadata_path"]), c["enriched_path"])
        st.success("✅ Enrichment complete!")
    except Exception as e:
        st.error("Enrichment failed.")
        st.exception(e)

    # Export docs
    st.markdown("#### 📄 Export Documentation")
    try:
        if Path(c["enriched_path"]).exists():
            enriched_metadata = load_metadata(c["enriched_path"])
            export_to_markdown(enriched_metadata, Path(c["markdown_path"]))
            export_to_word(enriched_metadata, Path(c["word_path"]))

        # Downloads
        if Path(c["enriched_path"]).exists():
            with open(c["enriched_path"], "r", encoding="utf-8") as ef:
                st.download_button(
                    label="📄 Download Enriched Metadata",
                    data=ef.read(),
                    file_name=Path(c["enriched_path"]).name,
                    mime="application/json",
                )
        else:
            st.warning("⚠️ Enriched metadata not found.")

        readme_path = Path("output/README_generated.md")
        if readme_path.exists():
            with open(readme_path, "r", encoding="utf-8") as rf:
                readme_data = rf.read()
            st.download_button(
                label="📘 Download Generated README",
                data=readme_data,
                file_name="README_generated.md",
                mime="text/markdown",
            )
            st.markdown("**README Preview**")
            st.code(readme_data, language="markdown")
        else:
            st.warning("⚠️ README file was not generated (check enrichment logic).")

        if Path(c["markdown_path"]).exists():
            with open(c["markdown_path"], "r", encoding="utf-8") as f:
                st.download_button(
                    label="📝 Download Markdown Documentation",
                    data=f.read(),
                    file_name=Path(c["markdown_path"]).name,
                    mime="text/markdown",
                )
        else:
            st.warning("⚠️ Markdown documentation file not found.")

        if Path(c["word_path"]).exists():
            with open(c["word_path"], "rb") as f:
                st.download_button(
                    label="📄 Download Word Documentation",
                    data=f.read(),
                    file_name=Path(c["word_path"]).name,
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
        else:
            st.warning("⚠️ Word documentation file not found.")
    except Exception as e:
        st.error("Export failed.")
        st.exception(e)

    # -------- Chatbot Section --------
    st.markdown("#### 💬 Chat with the Uploaded Code")

    # Ensure index exists for this chat
    try:
        with st.spinner("Indexing code + metadata for chatbot..."):
            meta_to_use = c["enriched_path"] if c["enriched_path"] and Path(c["enriched_path"]).exists() else None
            index_code_file(
                file_path=c["file_temp_path"],
                metadata_path=meta_to_use,
                persist_dir=c["persist_dir"],
            )
            c["indexed"] = True
    except Exception as e:
        st.error("Indexing failed. Chat retrieval may not include metadata.")
        st.exception(e)

    # Build / reuse the conversational chain
    try:
        if c["crc"] is None:
            c["crc"] = build_chatbot(
                persist_dir=c["persist_dir"],
                model=os.getenv("GROQ_MODEL", "qwen/qwen3-32b"),
            )

        # Render chat history
        for user_msg, ai_msg in c["history"]:
            with st.chat_message("user"):
                st.markdown(user_msg)
            with st.chat_message("assistant"):
                st.markdown(ai_msg)
# Added a sample comment
        # Input box
        user_query = st.chat_input(f"Ask {c['name']} about `{c['file_name']}`…")
        if user_query:
            with st.chat_message("user"):
                st.markdown(user_query)

            lc_history = [(u, a) for (u, a) in c["history"]]

            # Try once; if model gets decommissioned again, swap to a safe fallback
            try:
                with st.spinner("🤖 Thinking..."):
                    result = c["crc"].invoke({"question": user_query, "chat_history": lc_history})
            except Exception as e:
                if "decommissioned" in str(e).lower() or "model_decommissioned" in str(e).lower():
                    fallback = "llama-3.3-70b-versatile"
                    st.warning(f"Primary model unavailable. Switching to **{fallback}** and retrying…")
                    c["crc"] = build_chatbot(persist_dir=c["persist_dir"], model=fallback)
                    result = c["crc"].invoke({"question": user_query, "chat_history": lc_history})
                else:
                    raise

            answer = result.get("answer", "I could not find an answer.")
            sources = result.get("source_documents", []) or []
            if sources:
                source_list = "\n".join(
                    f"- {Path(src.metadata.get('source', 'unknown')).name}"
                    for src in sources
                )
                answer += f"\n\n**Sources:**\n{source_list}"

            with st.chat_message("assistant"):
                st.markdown(answer)

            c["history"].append((user_query, answer))

    except FileNotFoundError as e:
        st.error(str(e))
    except Exception as e:
        st.error("⚠️ Chatbot could not be constructed.")
        st.exception(e)
