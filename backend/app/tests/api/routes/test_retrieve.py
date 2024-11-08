import uuid

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.config import settings
from app.tests.utils.item import create_random_item


def test_create_item(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    data = {"patentId": "US-RE49889-E1", "company_name": "Walmart"}
    response = client.post(
        f"{settings.API_V1_STR}/retrieve/infringement-check",
        headers=superuser_token_headers,
        json=data,
    )
    assert response.status_code == 200
    content = response.json()
    assert len(content["top_infringing_products"]) == 2
