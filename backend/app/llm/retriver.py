from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from langchain_openai import ChatOpenAI
from app.models import InfringementCheckResponse
from app.llm.prompt import QA_CHAIN_PROMPT
from langchain.chat_models import ChatOpenAI
from pydantic import ValidationError
from langchain.output_parsers.json import SimpleJsonOutputParser
import json

def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)

def debug_print(data, label="Data at this stage"):
    print(f"{label}:\n", data)
    return data

def retrieve_infringement_check(vector_store, company_name, patent_claim, prompt = QA_CHAIN_PROMPT) -> InfringementCheckResponse:
    model = ChatOpenAI(
        model="gpt-4o",
        temperature=0,
        max_tokens=None,
        timeout=None,
        max_retries=2,
    )
    retriever = vector_store.as_retriever()
    json_parser = SimpleJsonOutputParser()
    chain = (
        {"context": retriever, "query": RunnablePassthrough(), "company_name": RunnableLambda(lambda _: company_name), "patent_claim": RunnableLambda(lambda _: patent_claim)}
        # | RunnableLambda(lambda data: debug_print(data, label="Before Prompt"))
        | prompt
        | RunnableLambda(lambda data: debug_print(data, label="Before Model"))
        | model
        # | RunnableLambda(lambda data: debug_print(data, label="Before Prompt"))
        | json_parser
    )
    query = "Use the following pieces of context, company name, and patent claim to do patent infringement analysis. Pick two most possible patents."
    try:
        response = chain.invoke(query)
        # print(f"response: {InfringementCheckResponse(**response)}")
        return InfringementCheckResponse(**response)
    except (json.JSONDecodeError, ValidationError) as e:
        print("Invalid response format:", e)
        return "Invalid response format"

def fuzzy_search_company(company_name: str, vector_store):
    results = vector_store.similarity_search_with_score(
        company_name,
        k=1,
        expr='source == "/app/app/mockdata/company_products.json"',
    )
    for res, score in results:
        print(f"* [SIM={score:3f}] {res.page_content} [{res.metadata}]")
    return results[0][0].page_content

def fuzzy_search_patent_id(patent_id: str, vector_store):
    results = vector_store.similarity_search_with_score(
        patent_id,
        k=1,
        expr='source == "/app/app/mockdata/patents.json"',
    )
    for res, score in results:
        print(f"* [SIM={score:3f}] {res.page_content} [{res.metadata}]")
    return results[0][0].page_content

def get_patent_by_id(patent_id: str, vector_store):
    results = vector_store.similarity_search_with_score(
        "*",
        k=1,
        filter={"patent_id": patent_id, 'source': '/app/app/mockdata/patents.json'}
    )
    return results