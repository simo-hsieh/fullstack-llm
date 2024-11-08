from fastapi import APIRouter, HTTPException

from app.api.deps import CurrentUser, SessionDep
from app.llm.retriver import retrieve_infringement_check, fuzzy_search_company, get_patent_by_id
from app.models import InfringementCheckInput, InfringementCheckResponse
from app.llm.vectordb import get_vector_store

router = APIRouter()

@router.post(
    "/infringement-check", response_model=InfringementCheckResponse
)
def infringement_check(*, session: SessionDep, current_user: CurrentUser, infringe_in: InfringementCheckInput) -> InfringementCheckResponse:
    """
    retrive infringement check
    """
    vector_store = get_vector_store()
    company_name = fuzzy_search_company(infringe_in.company_name, vector_store)
    patent = get_patent_by_id(infringe_in.patent_id, vector_store)
    try:
        return retrieve_infringement_check(vector_store, company_name, patent)
    except:
        return {"message": "not valid result"}
