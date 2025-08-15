# index_and_chat.py
import os
from pathlib import Path

from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import TextLoader
from langchain.chains import ConversationalRetrievalChain
from langchain_openai import ChatOpenAI  # Groq-compatible OpenAI client

# Persistent vector DB directory
DEFAULT_VECTOR_DB_DIR = "output/vector_db"


def index_code_file(
    file_path: str,
    metadata_path: str = None,
    persist_dir: str = DEFAULT_VECTOR_DB_DIR
) -> None:
    """
    Indexes a Python code file + optional enriched metadata into a Chroma DB for semantic search.
    Splits into chunks, embeds, and persists them for later chatbot queries.
    """
    # Ensure output directory exists
    Path(persist_dir).mkdir(parents=True, exist_ok=True)

    print(f"📄 Indexing file: {file_path}")

    # 1️⃣ Load Python file as a document
    loader = TextLoader(file_path, encoding="utf-8")
    docs = loader.load()

    # ✅ If metadata is provided, load it too
    if metadata_path and Path(metadata_path).exists():
        print(f"📝 Adding enriched metadata: {metadata_path}")
        with open(metadata_path, "r", encoding="utf-8") as meta_file:
            metadata_text = meta_file.read()

        # Append metadata as an extra "doc" chunk
        from langchain.schema import Document
        docs.append(Document(page_content=metadata_text, metadata={"source": metadata_path}))

    # 2️⃣ Split into chunks for better retrieval
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        separators=["\nclass ", "\ndef ", "\n#", "\n\n"]
    )
    split_docs = splitter.split_documents(docs)

    # 3️⃣ Create embeddings
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

    # 4️⃣ Create or update Chroma DB
    vectordb = Chroma.from_documents(
        split_docs,
        embedding=embeddings,
        persist_directory=persist_dir
    )
    vectordb.persist()
    print(f"✅ Indexed {len(split_docs)} chunks into Chroma DB at: {persist_dir}")


def _select_model(explicit: str | None) -> str:
    """
    Return the model to use:
      1) the explicit arg if provided,
      2) else env var GROQ_MODEL,
      3) else a safe default.
    """
    return explicit or os.getenv("GROQ_MODEL", "qwen/qwen3-32b")


def build_chatbot(
    persist_dir: str = DEFAULT_VECTOR_DB_DIR,
    model: str | None = None
):
    """
    Builds a conversational retrieval chatbot using the indexed code + metadata in Chroma DB.
    This version supports *continuous* conversation across turns and uses a non-deprecated model.

    Set a model via:
      - passing `model=` (e.g., "llama-3.3-70b-versatile")
      - or environment variable GROQ_MODEL
      - falls back to "qwen/qwen3-32b"
    """
    # Check if vector DB exists
    if not Path(persist_dir).exists():
        raise FileNotFoundError(f"No Chroma index found at {persist_dir}. Please index a code file first.")

    print(f"🔄 Loading Chroma DB from: {persist_dir}")

    # Load persisted Chroma DB
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    vectordb = Chroma(persist_directory=persist_dir, embedding_function=embeddings)

    # Retriever (fetch top 3 most similar chunks)
    retriever = vectordb.as_retriever(search_type="similarity", search_kwargs={"k": 3})

    # ✅ Groq via OpenAI-compatible client — NO deprecated model names
    selected_model = _select_model(model)
    print(f"🔧 Using Groq model: {selected_model}")

    llm = ChatOpenAI(
        model=selected_model,
        base_url=os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1"),
        api_key=os.getenv("GROQ_API_KEY"),
        streaming=True,
        temperature=0.2,
    )

    # ✅ Conversational + Retrieval-aware chain (continuous memory via chat_history)
    crc = ConversationalRetrievalChain.from_llm(
        llm=llm,
        retriever=retriever,
        chain_type="stuff",
        return_source_documents=True
    )

    return crc
