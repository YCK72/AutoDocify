import os
from langchain.document_loaders import TextLoader
from langchain.vectorstores import Chroma
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter

SOURCE_DIR = "."


def get_documents():
    loaders = []
    for file in os.listdir(SOURCE_DIR):
        if file.endswith(".py"):
            loaders.append(TextLoader(os.path.join(SOURCE_DIR, file)))
    return [doc for loader in loaders for doc in loader.load()]


def build_vectorstore(persist_dir="chroma_logs"):
    documents = get_documents()
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    split_docs = splitter.split_documents(documents)

    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    vectordb = Chroma.from_documents(split_docs, embedding=embeddings, persist_directory=persist_dir)
    vectordb.persist()
    print(f"✅ Vector DB created at {persist_dir}")


if __name__ == "__main__":
    build_vectorstore()
