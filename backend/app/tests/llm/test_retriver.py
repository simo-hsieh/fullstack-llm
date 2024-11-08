from app.llm.vectordb import get_vector_store, init_vector_db
from app.llm.retriver import retrieve_infringement_check, fuzzy_search_company, fuzzy_search_patent_id, get_patent_by_id

init_vector_db()

def test_fuzzy_search_company():
    vector_store = get_vector_store()
    result = fuzzy_search_company("walmart", vector_store)
    print(result)

def test_get_patent_by_id():
    vector_store = get_vector_store()
    result = get_patent_by_id("US-RE49889-E1", vector_store)
    print(result)


def test_retrieve_infringement_check():
    vector_store = get_vector_store()
    retrieve_infringement_check(vector_store, "Walmart Inc.", get_patent_by_id("US-RE49889-E1", vector_store))