from fastapi import APIRouter, HTTPException

from app.api.deps import CurrentUser, SessionDep
from app.llm.retriver import retrieve_infringement_check
from app.models import InfringementCheckInput, InfringementCheckResponse

router = APIRouter()

@router.post(
    "/infringement-check", response_model=InfringementCheckResponse
)
def infringement_check(*, session: SessionDep, current_user: CurrentUser, infringe_in: InfringementCheckInput) -> InfringementCheckResponse:
    """
    retrive infringement check
    """

    return retrieve_infringement_check(infringe_in)
