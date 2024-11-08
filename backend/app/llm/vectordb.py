from pymilvus import MilvusClient
from langchain_milvus import Milvus
from langchain_openai import OpenAIEmbeddings
from app.llm.loader import load_json_docs

def init_vector_db():
    embeddings = OpenAIEmbeddings()
    docs_list = load_json_docs()

    vector_store = Milvus(
        embedding_function=embeddings,
        connection_args={
            "uri": "./milvus_demo.db",
        },
        drop_old=True,  # Drop the old Milvus collection if it exists
        auto_id=True,  # Automatically generate IDs for documents
    )
    for docs in docs_list:
        vector_store.add_documents(documents=docs)
    return vector_store

def get_vector_store():
    embeddings = OpenAIEmbeddings()
    vector_store = Milvus(
        embedding_function=embeddings,
        connection_args={
            "uri": "./milvus_demo.db",
        },
        auto_id=True,  # Automatically generate IDs for documents
    )
    return vector_store


    

