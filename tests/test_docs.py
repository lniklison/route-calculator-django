import pytest
from django.test import Client


@pytest.mark.django_db
def test_api_docs_are_available(client: Client) -> None:
    response = client.get("/api/docs/")

    assert response.status_code == 200
    assert b"swagger-ui" in response.content
