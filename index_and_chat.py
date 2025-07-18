# index_and_chat.py

import os
from pathlib import Path

from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import TextLoader
from langchain.chains import RetrievalQA
from langchain_community.chat_models import ChatOllama  # Uses local Ollama models

# Persistent vector DB directory
DEFAULT_VECTOR_DB_DIR = "output/vector_db"


def index_code_file(file_path: str, persist_dir: str = DEFAULT_VECTOR_DB_DIR) -> None:
    """
    Indexes a Python code file into a Chroma DB for semantic search.
    Splits code into chunks, embeds, and persists them for later chatbot queries.
    """
    # Ensure output directory exists
    Path(persist_dir).mkdir(parents=True, exist_ok=True)

    print(f"📄 Indexing file: {file_path}")

    # 1️⃣ Load Python file as a document
    loader = TextLoader(file_path, encoding="utf-8")
    docs = loader.load()

    # 2️⃣ Split code into chunks (helps with retrieval)
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        separators=["\nclass ", "\ndef ", "\n#", "\n\n"]
    )
    split_docs = splitter.split_documents(docs)

    # 3️⃣ Create embeddings (HuggingFace lightweight model)
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

    # 4️⃣ Create or update Chroma DB
    vectordb = Chroma.from_documents(
        split_docs,
        embedding=embeddings,
        persist_directory=persist_dir
    )
    vectordb.persist()
    print(f"✅ Indexed {len(split_docs)} chunks into Chroma DB at: {persist_dir}")


def build_chatbot(
    persist_dir: str = DEFAULT_VECTOR_DB_DIR,
    model: str = "mistral"
):
    """
    Builds a retrieval-based chatbot using the indexed code in Chroma DB.
    Uses ChatOllama for answering questions.
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

    # ChatOllama (local LLM) - you can switch model to "llama2", "mistral", etc.
    llm = ChatOllama(model=model, streaming=True)

    # Retrieval-based QA Chain
    qa_chain = RetrievalQA.from_chain_type(
        llm=llm,
        retriever=retriever,
        chain_type="stuff",
        return_source_documents=True
    )

    def chatbot_fn(query: str) -> str:
        """
        Ask a question about the indexed code and return a clean answer.
        """
        result = qa_chain.invoke(query)
        answer = result.get("result", "I could not find an answer.")
        sources = result.get("source_documents", [])

        # Optional: append sources for transparency
        if sources:
            source_list = "\n".join(
                f"- {Path(src.metadata.get('source', 'unknown')).name}" for src in sources
            )
            answer += f"\n\n**Sources:**\n{source_list}"

        return answer

    return chatbot_fn
